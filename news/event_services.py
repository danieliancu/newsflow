import json
import re
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Q, Sum, When
from django.utils import timezone
from openai import OpenAI

from .ai_usage import record_ai_usage
from .models import AIUsage, Article, Event, EventArticle, EventBudget
from .services import token_similarity


EVENT_MERGE_TITLE_THRESHOLD = 0.60
EVENT_MERGE_WINDOW_HOURS = 24
EVENT_SEMANTIC_PREFILTER_THRESHOLD = 0.20
EVENT_SEMANTIC_MERGE_CONFIDENCE = 0.90
EVENT_SEMANTIC_MAX_CHECKS_PER_RUN = 50


def eligible_event_articles(queryset=None):
    queryset = queryset if queryset is not None else Article.objects.all()
    return queryset.exclude(source__slug__in=settings.NEWSFLOW_EVENT_EXCLUDED_SOURCE_SLUGS)


def _merge_events(survivor, duplicates):
    duplicates = [event for event in duplicates if event.pk != survivor.pk]
    if not duplicates:
        return survivor
    with transaction.atomic():
        for duplicate in duplicates:
            EventArticle.objects.filter(event=duplicate).update(event=survivor)
            AIUsage.objects.filter(event=duplicate).update(event=survivor)
            survivor.generation_count += duplicate.generation_count
            survivor.initial_cost_gbp += duplicate.initial_cost_gbp
            survivor.update_cost_gbp += duplicate.update_cost_gbp
            survivor.total_cost_gbp += duplicate.total_cost_gbp
            if duplicate.first_generated_at and (
                survivor.first_generated_at is None
                or duplicate.first_generated_at < survivor.first_generated_at
            ):
                survivor.first_generated_at = duplicate.first_generated_at
            if duplicate.last_generated_at and (
                survivor.last_generated_at is None
                or duplicate.last_generated_at > survivor.last_generated_at
            ):
                survivor.last_generated_at = duplicate.last_generated_at
            duplicate.delete()
        survivor.generated_source_count = eligible_event_articles(survivor.articles).values("source_id").distinct().count()
        survivor.status = Event.Status.PENDING
        survivor.next_generation_at = timezone.now()
        survivor.save(
            update_fields=[
                "generation_count",
                "initial_cost_gbp",
                "update_cost_gbp",
                "total_cost_gbp",
                "first_generated_at",
                "last_generated_at",
                "generated_source_count",
                "status",
                "next_generation_at",
            ]
        )
    return survivor


def _similar_events(root, members, latest):
    window_start = latest - timedelta(hours=EVENT_MERGE_WINDOW_HOURS)
    window_end = latest + timedelta(hours=EVENT_MERGE_WINDOW_HOURS)
    titles = [root.title, *(article.title for article in members)]
    matches = []
    candidates = Event.objects.filter(last_article_at__range=(window_start, window_end))
    for candidate in candidates:
        if max(token_similarity(title, candidate.title) for title in titles) >= EVENT_MERGE_TITLE_THRESHOLD:
            matches.append(candidate)
    return matches


def synchronize_events():
    """Create/update event clusters from the existing duplicate relationships."""
    EventArticle.objects.filter(
        article__source__slug__in=settings.NEWSFLOW_EVENT_EXCLUDED_SOURCE_SLUGS
    ).delete()
    Event.objects.filter(event_articles__isnull=True).delete()
    created = 0
    updated = 0
    roots = (
        eligible_event_articles(Article.objects.filter(processing_status=Article.ProcessingStatus.PROCESSED))
        .filter(Q(duplicate_articles__isnull=False) | Q(duplicate_of__isnull=False))
        .values_list("duplicate_of_id", flat=True)
    )
    root_ids = {root_id for root_id in roots if root_id}
    root_ids.update(
        eligible_event_articles(Article.objects.filter(duplicate_articles__isnull=False)).values_list("pk", flat=True)
    )
    budget = EventBudget.get_solo()
    for root in eligible_event_articles(Article.objects.filter(pk__in=root_ids)).select_related("source"):
        members = list(
            eligible_event_articles(Article.objects.filter(Q(pk=root.pk) | Q(duplicate_of=root)))
            .filter(processing_status=Article.ProcessingStatus.PROCESSED)
            .select_related("source")
            .order_by("published_at", "collected_at")
        )
        if len({article.source_id for article in members}) < budget.minimum_sources_for_creation:
            continue
        latest = max(
            (article.published_at or article.collected_at for article in members),
            default=timezone.now(),
        )
        matching_events = list(
            Event.objects.filter(event_articles__article__in=members).distinct()
        )
        matching_ids = {event.pk for event in matching_events}
        for candidate in _similar_events(root, members, latest):
            if candidate.pk not in matching_ids:
                matching_events.append(candidate)
                matching_ids.add(candidate.pk)
        existing = min(matching_events, key=lambda event: event.pk) if matching_events else None
        if existing is not None and len(matching_events) > 1:
            existing = _merge_events(
                existing, [event for event in matching_events if event.pk != existing.pk]
            )
        if existing is None:
            existing = Event.objects.create(
                title=root.title,
                status=Event.Status.PENDING,
                last_article_at=latest,
            )
            created += 1
        previous_count = existing.articles.count()
        for article in members:
            EventArticle.objects.update_or_create(
                article=article, defaults={"event": existing}
            )
        new_count = existing.articles.count()
        current_source_count = existing.articles.values("source_id").distinct().count()
        if new_count > previous_count and previous_count:
            updated += 1
        existing.last_article_at = latest
        existing.generated_source_count = current_source_count
        if existing.status in {Event.Status.STABLE, Event.Status.FAILED}:
            existing.status = Event.Status.PENDING
        existing.save(
            update_fields=["last_article_at", "generated_source_count", "status"]
        )
    return created, updated


def stabilize_old_events():
    cutoff = timezone.now() - timedelta(days=settings.NEWSFLOW_EVENT_ACTIVE_DAYS)
    return Event.objects.filter(
        last_article_at__lt=cutoff,
        status__in=[
            Event.Status.GENERATED,
            Event.Status.INDEXABLE,
            Event.Status.PENDING,
            Event.Status.BUDGET_BLOCKED,
        ],
    ).update(status=Event.Status.STABLE, next_generation_at=None)


def _period_usage(now):
    local_now = now.astimezone(ZoneInfo("Europe/London"))
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    event_usage = AIUsage.objects.filter(event__isnull=False)
    return {
        "day_cost": event_usage.filter(created_at__gte=day_start).aggregate(
            value=Sum("total_cost_gbp")
        )["value"]
        or Decimal("0"),
        "month_cost": event_usage.filter(created_at__gte=month_start).aggregate(
            value=Sum("total_cost_gbp")
        )["value"]
        or Decimal("0"),
        "day_events": Event.objects.filter(first_generated_at__gte=day_start).count(),
        "month_events": Event.objects.filter(first_generated_at__gte=month_start).count(),
    }


def reserve_event_budget(event):
    with transaction.atomic():
        budget = EventBudget.objects.select_for_update().get_or_create(pk=1)[0]
        if not budget.ai_enabled:
            return False, Decimal("0"), "Generarea AI este dezactivată."
        usage = _period_usage(timezone.now())
        estimated_reserve = Decimal(settings.NEWSFLOW_EVENT_ESTIMATED_RESERVATION_GBP)
        if budget.max_cost_gbp_per_event:
            remaining_event_budget = max(
                Decimal("0"), budget.max_cost_gbp_per_event - event.total_cost_gbp
            )
            reserve = (
                estimated_reserve
                if remaining_event_budget >= estimated_reserve
                else Decimal("0")
            )
        else:
            reserve = estimated_reserve
        checks = [
            (
                budget.max_new_events_per_day
                and event.first_generated_at is None
                and usage["day_events"] >= budget.max_new_events_per_day,
                "Limita zilnică de evenimente a fost atinsă.",
            ),
            (
                budget.max_new_events_per_month
                and event.first_generated_at is None
                and usage["month_events"] >= budget.max_new_events_per_month,
                "Limita lunară de evenimente a fost atinsă.",
            ),
            (
                budget.max_cost_gbp_per_day
                and usage["day_cost"] + budget.reserved_cost_gbp + reserve
                > budget.max_cost_gbp_per_day,
                "Bugetul zilnic pentru evenimente a fost atins.",
            ),
            (
                budget.max_cost_gbp_per_month
                and usage["month_cost"] + budget.reserved_cost_gbp + reserve
                > budget.max_cost_gbp_per_month,
                "Bugetul lunar pentru evenimente a fost atins.",
            ),
            (
                budget.max_cost_gbp_per_event
                and reserve <= 0,
                "Costul maxim al evenimentului a fost atins.",
            ),
        ]
        for blocked, reason in checks:
            if blocked:
                return False, Decimal("0"), reason
        budget.reserved_cost_gbp += reserve
        budget.save(update_fields=["reserved_cost_gbp", "updated_at"])
        return True, reserve, ""


def release_event_budget(reserved):
    with transaction.atomic():
        budget = EventBudget.objects.select_for_update().get_or_create(pk=1)[0]
        budget.reserved_cost_gbp = max(
            Decimal("0"), budget.reserved_cost_gbp - reserved
        )
        budget.save(update_fields=["reserved_cost_gbp", "updated_at"])


def _event_sources(event):
    sources = list(
        eligible_event_articles(event.articles.select_related("source"))
        .order_by("published_at", "collected_at")
        .values(
            "id",
            "title",
            "first_paragraph",
            "second_paragraph",
            "published_at",
            "canonical_url",
            "source__name",
            "source_id",
        )
    )
    for source in sources:
        if source["published_at"]:
            source["published_at"] = source["published_at"].isoformat()
    return sources


def _semantic_merge_payload(event):
    articles = list(
        eligible_event_articles(event.articles.select_related("source"))
        .order_by("published_at", "collected_at")
        .values(
            "title",
            "first_paragraph",
            "second_paragraph",
            "published_at",
            "source__name",
        )[:8]
    )
    for article in articles:
        if article["published_at"]:
            article["published_at"] = article["published_at"].isoformat()
    return {"title": event.title, "articles": articles}


def _call_semantic_merge_check(client, first, second, refresh_run):
    model = settings.OPENAI_EVENT_EXTRACTION_MODEL
    response = client.responses.create(
        model=model,
        store=False,
        instructions=(
            "Decide dacă cele două grupuri de relatări descriu același eveniment concret. "
            "Consideră același eveniment și reacțiile diferitelor persoane la aceeași decizie, "
            "evaluare, declarație oficială, incident sau evoluție, dacă au același declanșator "
            "central și același context temporal. Nu uni relatări care au doar aceeași temă, "
            "instituție sau persoană, dar descriu decizii ori evoluții distincte. Acordă o "
            "încredere de minimum 0.90 numai când identitatea evenimentului central este clară. "
            "Folosește exclusiv informațiile furnizate și nu completa din memorie."
        ),
        input=json.dumps(
            {
                "first_event": _semantic_merge_payload(first),
                "second_event": _semantic_merge_payload(second),
            },
            ensure_ascii=False,
            default=str,
        ),
        max_output_tokens=120,
        text={
            "format": {
                "type": "json_schema",
                "name": "event_semantic_merge",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "same_event": {"type": "boolean"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["same_event", "confidence"],
                    "additionalProperties": False,
                },
            }
        },
    )
    record_ai_usage(
        response,
        event=first,
        refresh_run=refresh_run,
        model=model,
        input_rate=settings.OPENAI_EVENT_NANO_INPUT_USD_PER_MILLION,
        cached_input_rate=settings.OPENAI_EVENT_NANO_CACHED_INPUT_USD_PER_MILLION,
        output_rate=settings.OPENAI_EVENT_NANO_OUTPUT_USD_PER_MILLION,
        usage_type=AIUsage.UsageType.EVENT_MERGE_CHECK,
    )
    return json.loads(response.output_text)


def merge_semantically_equivalent_candidates(refresh_run=None):
    """Merge only never-generated events after a cheap local shortlist."""
    budget = EventBudget.get_solo()
    if not budget.ai_enabled or not settings.OPENAI_API_KEY:
        return 0
    candidates = list(
        Event.objects.filter(
            first_generated_at=None,
            status=Event.Status.PENDING,
        )
        .prefetch_related("articles__source")
        .order_by("first_seen_at", "pk")
    )
    if len(candidates) < 2:
        return 0

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    active_ids = {event.pk for event in candidates}
    merged = 0
    checks = 0
    for index, first in enumerate(candidates):
        if first.pk not in active_ids:
            continue
        for second in candidates[index + 1 :]:
            if second.pk not in active_ids:
                continue
            first_time = first.last_article_at or first.first_seen_at
            second_time = second.last_article_at or second.first_seen_at
            if abs(first_time - second_time) > timedelta(hours=EVENT_MERGE_WINDOW_HOURS):
                continue
            if token_similarity(first.title, second.title) < EVENT_SEMANTIC_PREFILTER_THRESHOLD:
                continue
            if checks >= EVENT_SEMANTIC_MAX_CHECKS_PER_RUN:
                return merged
            checks += 1
            try:
                result = _call_semantic_merge_check(
                    client, first, second, refresh_run
                )
            except Exception:
                continue
            if not result["same_event"] or result["confidence"] < EVENT_SEMANTIC_MERGE_CONFIDENCE:
                continue
            duplicate_id = second.pk
            first = _merge_events(first, [second])
            active_ids.remove(duplicate_id)
            merged += 1
    return merged


def replace_article_references(text, sources):
    """Replace internal article identifiers with publication names."""
    result = str(text)
    id_to_name = {
        str(source["id"]): source.get("source__name", "publicația")
        for source in sources
    }
    for article_id in sorted(id_to_name, key=len, reverse=True):
        result = re.sub(
            rf"\b{re.escape(article_id)}\b", id_to_name[article_id], result
        )
    return re.sub(
        r"\b(?:articolul|articolele|sursa|sursele)\s+(?=[A-ZĂÂÎȘȚ])",
        "",
        result,
        flags=re.IGNORECASE,
    )


SOURCE_OMISSION_PATTERNS = (
    re.compile(r"\b(?:informa(?:ția|țiile)|detali(?:ul|ile)|aspect(?:ul|ele))\s+care\s+nu\b", re.IGNORECASE),
    re.compile(
        r"\bnu\s+(?:apare|apar|este\s+prezent(?:ă)?|sunt\s+prezent(?:e)?|se\s+regăsește|se\s+regăsesc|"
        r"menționează|precizează|include|relatează|oferă|abordează|confirmă)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:lipsește|lipsesc|absent(?:ă|e)?)\b", re.IGNORECASE),
)


def difference_is_material_conflict(text):
    """Reject source differences that describe omission instead of conflicting claims."""
    normalized = " ".join(str(text or "").split())
    return bool(normalized) and not any(
        pattern.search(normalized) for pattern in SOURCE_OMISSION_PATTERNS
    )


SUMMARY_FILLER_PATTERNS = (
    re.compile(r"^informațiile (?:disponibile|cunoscute|prezentate) (?:sunt|rămân) limitate\b", re.IGNORECASE),
    re.compile(r"^(?:nu sunt disponibile|nu există|fără) alte detalii\b", re.IGNORECASE),
    re.compile(r"^(?:sursele|relatările|materialele) (?:disponibile )?(?:nu )?(?:oferă|conțin|precizează)\b", re.IGNORECASE),
    re.compile(r"^declarația (?:reia|mută accentul|pune accentul)\b", re.IGNORECASE),
)


def remove_summary_filler(text):
    """Drop meta-commentary about missing material instead of facts about the event."""
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(str(text or "").split()))
    kept = [
        sentence
        for sentence in sentences
        if sentence and not any(pattern.search(sentence) for pattern in SUMMARY_FILLER_PATTERNS)
    ]
    return " ".join(kept)


def _call_extraction(client, event, sources, refresh_run):
    model = settings.OPENAI_EVENT_EXTRACTION_MODEL
    response = client.responses.create(
        model=model,
        store=False,
        instructions=(
            "Extrage numai afirmații factuale explicite din fragmentele furnizate. "
            "Nu completa informații din memorie. Păstrează article_id-ul sursei."
        ),
        input=json.dumps(sources, ensure_ascii=False, default=str),
        max_output_tokens=900,
        text={
            "format": {
                "type": "json_schema",
                "name": "event_claims",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "claims": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "article_id": {"type": "integer"},
                                    "claim": {"type": "string"},
                                },
                                "required": ["article_id", "claim"],
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["claims"],
                    "additionalProperties": False,
                },
            }
        },
    )
    record_ai_usage(
        response,
        event=event,
        refresh_run=refresh_run,
        model=model,
        input_rate=settings.OPENAI_EVENT_NANO_INPUT_USD_PER_MILLION,
        cached_input_rate=settings.OPENAI_EVENT_NANO_CACHED_INPUT_USD_PER_MILLION,
        output_rate=settings.OPENAI_EVENT_NANO_OUTPUT_USD_PER_MILLION,
        usage_type=AIUsage.UsageType.EVENT_CLAIM_EXTRACTION,
    )
    return json.loads(response.output_text)["claims"]


def _call_update_check(client, event, new_sources, refresh_run):
    model = settings.OPENAI_EVENT_EXTRACTION_MODEL
    response = client.responses.create(
        model=model,
        store=False,
        instructions=(
            "Compară relatările noi exclusiv cu sinteza existentă. Marchează actualizarea "
            "necesară numai dacă apare cel puțin una dintre următoarele: un fapt nou relevant "
            "pentru subiect, o contradicție factuală sau o evoluție majoră. O reformulare, "
            "repetarea acelorași fapte ori simpla confirmare de către încă o publicație nu "
            "justifică rescrierea. Nu completa informații din memorie."
        ),
        input=json.dumps(
            {
                "existing_event": {
                    "title": event.title,
                    "summary": event.summary,
                    "differences": event.differences,
                    "timeline": event.timeline,
                },
                "new_sources": new_sources,
            },
            ensure_ascii=False,
            default=str,
        ),
        max_output_tokens=350,
        text={
            "format": {
                "type": "json_schema",
                "name": "event_update_check",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "should_update": {"type": "boolean"},
                        "change_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "new_fact",
                                    "contradiction",
                                    "major_development",
                                ],
                            },
                        },
                        "reason": {"type": "string"},
                    },
                    "required": ["should_update", "change_types", "reason"],
                    "additionalProperties": False,
                },
            }
        },
    )
    record_ai_usage(
        response,
        event=event,
        refresh_run=refresh_run,
        model=model,
        input_rate=settings.OPENAI_EVENT_NANO_INPUT_USD_PER_MILLION,
        cached_input_rate=settings.OPENAI_EVENT_NANO_CACHED_INPUT_USD_PER_MILLION,
        output_rate=settings.OPENAI_EVENT_NANO_OUTPUT_USD_PER_MILLION,
        usage_type=AIUsage.UsageType.EVENT_UPDATE_CHECK,
    )
    return json.loads(response.output_text)


def _call_summary(client, event, sources, claims, refresh_run, is_update):
    model = settings.OPENAI_EVENT_SUMMARY_MODEL
    article_ids = [source["id"] for source in sources]
    response = client.responses.create(
        model=model,
        store=False,
        instructions=(
            "Redactează în română o sinteză neutră și originală, cu lungimea adaptată "
            "strict cantității de informație factuală disponibilă. Pentru un eveniment cu "
            "puține fapte sunt suficiente una până la trei propoziții; nu există o lungime "
            "minimă. Pentru evenimentele bogate în informații poți ajunge la aproximativ "
            "170 de cuvinte, iar numai subiectele complexe pot ajunge la 220 de cuvinte. "
            "Dezvoltă contextul, consecințele și "
            "legăturile dintre fapte atunci când acestea sunt susținute de surse. Urmărește "
            "densitatea informațională, nu un număr de cuvinte. Oprește sinteza imediat ce "
            "faptele relevante au fost prezentate; nu inventa, nu repeta și nu adăuga text "
            "de umplutură. Nu comenta lipsa informațiilor și nu încheia cu formule precum "
            "«informațiile disponibile sunt limitate», «nu există alte detalii», «sursele nu "
            "oferă alte informații» sau echivalente. "
            "Titlul trebuie să fie factual, autonom și să aibă maximum 110 caractere. "
            "Folosește exclusiv afirmațiile extrase. Evidențiază separat diferențele dintre surse. "
            "Scrie summary cu focus pe informații și într-un flux jurnalistic natural. "
            "Folosește un stil jurnalistic clar și fluent, cu tranziții firești între idei, "
            "vocabular variat și suficient context pentru ca relevanța faptelor să fie ușor de "
            "înțeles. Alternează natural structura propozițiilor și preferă verbe precise, fără "
            "a transforma sinteza într-o enumerare mecanică. Evită repetițiile, dramatizarea, "
            "adjectivele evaluative și formulările introduse doar pentru a lungi textul. "
            "Titlul și summary trebuie să descrie exclusiv evenimentul și faptele sale, nu felul "
            "în care informația a fost publicată, relatată, verificată sau confirmată prin "
            "compararea materialelor. Formulează direct faptele confirmate de minimum două "
            "articole, fără nume de publicații și fără atribuiri. Pentru acestea evită expresii "
            "precum «X relatează», «Y notează», «potrivit X», "
            "«sursele spun», «informația este confirmată» sau «relatările precizează». Nu menționa "
            "acordul dintre surse și nu explica cine a publicat ori a transmis primul informația. "
            "Titlul nu trebuie să conțină niciodată nume de publicații. Poți include în summary "
            "un fapt contextual relevant care apare într-o singură "
            "publicație numai dacă îl atribui explicit acelei publicații prin source__name și "
            "îl formulezi cu gradul de certitudine din relatare. "
            "Dacă nu poate fi formulat responsabil cu atribuire, omite-l din summary. Nu muta "
            "automat un asemenea detaliu "
            "în differences doar pentru că apare într-o singură relatare. Absența sau omiterea "
            "unei informații dintr-o publicație nu este o diferență și nu trebuie menționată. "
            "Compară numai afirmații despre același fapt care apar explicit în minimum două "
            "publicații. Folosește differences exclusiv pentru contradicții, "
            "valori diferite, interpretări incompatibile sau detalii asupra cărora relatările "
            "diferă în mod real și care pot schimba înțelegerea evenimentului. Rubrica nu este "
            "obligatorie: dacă nu există diferențe serioase, returnează differences ca listă "
            "goală. Nu căuta artificial diferențe și ignoră variațiile de redactare, punctuație, "
            "ordine a cuvintelor, denumire a monedei, separatori de mii sau forme numerice "
            "echivalente; de exemplu, «3 milioane EUR» și «3.000.000 euro» reprezintă aceeași "
            "informație. Include numai diferențe materiale privind faptele, valorile după "
            "normalizare, datele, persoanele implicate, cauzele, consecințele ori gradul de "
            "certitudine. "
            "În textele destinate cititorului folosește întotdeauna numele publicației din "
            "source__name. Nu afișa article_id, ID-uri, numere interne sau formulări precum "
            "«articolul 27» ori «sursa 27». "
            "În differences atribuie explicit informațiile publicațiilor pe nume. "
            "Nu folosi citate inventate și nu declara cert ceea ce apare într-o singură sursă."
        ),
        input=json.dumps(
            {"allowed_article_ids": article_ids, "sources": sources, "claims": claims},
            ensure_ascii=False,
            default=str,
        ),
        max_output_tokens=1300,
        text={
            "format": {
                "type": "json_schema",
                "name": "event_summary",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "maxLength": 110},
                        "summary": {"type": "string"},
                        "differences": {"type": "array", "items": {"type": "string"}},
                        "timeline": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string"},
                                    "text": {"type": "string"},
                                    "article_ids": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                    },
                                },
                                "required": ["date", "text", "article_ids"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": [
                        "title",
                        "summary",
                        "differences",
                        "timeline",
                    ],
                    "additionalProperties": False,
                },
            }
        },
    )
    record_ai_usage(
        response,
        event=event,
        refresh_run=refresh_run,
        model=model,
        input_rate=settings.OPENAI_EVENT_MINI_INPUT_USD_PER_MILLION,
        cached_input_rate=settings.OPENAI_EVENT_MINI_CACHED_INPUT_USD_PER_MILLION,
        output_rate=settings.OPENAI_EVENT_MINI_OUTPUT_USD_PER_MILLION,
        usage_type=(
            AIUsage.UsageType.EVENT_UPDATE
            if is_update
            else AIUsage.UsageType.EVENT_SUMMARY
        ),
    )
    return json.loads(response.output_text)


def generate_event(event, refresh_run=None, force=False):
    sources = _event_sources(event)
    source_ids = {source["source_id"] for source in sources}
    reviewed_source_ids = {
        source.get("source_id") for source in event.source_snapshot if source.get("source_id")
    }
    budget = EventBudget.get_solo()
    if len(source_ids) < budget.minimum_sources_for_creation:
        return False
    if not force and event.last_generated_at and reviewed_source_ids >= source_ids:
        return False
    if not force and event.last_generated_at and not reviewed_source_ids and event.generated_source_count >= len(source_ids):
        return False
    if not force and event.next_generation_at and event.next_generation_at > timezone.now():
        return False
    reserved, reserved_amount, reason = reserve_event_budget(event)
    if not reserved:
        event.status = Event.Status.BUDGET_BLOCKED
        event.last_error = reason
        event.save(update_fields=["status", "last_error"])
        return False
    if not settings.OPENAI_API_KEY:
        release_event_budget(reserved_amount)
        event.status = Event.Status.PENDING
        event.last_error = "OPENAI_API_KEY lipsește."
        event.save(update_fields=["status", "last_error"])
        return False
    before_cost = event.ai_usage.aggregate(value=Sum("total_cost_gbp"))["value"] or Decimal("0")
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        is_update = event.first_generated_at is not None
        if is_update and not force:
            new_sources = [
                source for source in sources if source["source_id"] not in reviewed_source_ids
            ]
            assessment = _call_update_check(client, event, new_sources, refresh_run)
            if not assessment["should_update"]:
                now = timezone.now()
                event.source_snapshot = sources
                event.generated_source_count = len(source_ids)
                event.next_generation_at = now + timedelta(
                    minutes=settings.NEWSFLOW_EVENT_REGENERATION_MINUTES
                )
                event.status = (
                    Event.Status.INDEXABLE
                    if len(source_ids) >= budget.minimum_sources_for_indexing
                    else Event.Status.GENERATED
                )
                event.last_error = ""
                event.save(
                    update_fields=[
                        "source_snapshot",
                        "generated_source_count",
                        "next_generation_at",
                        "status",
                        "last_error",
                    ]
                )
                after_cost = (
                    event.ai_usage.aggregate(value=Sum("total_cost_gbp"))["value"]
                    or Decimal("0")
                )
                event.update_cost_gbp += after_cost - before_cost
                event.total_cost_gbp = after_cost
                event.save(update_fields=["update_cost_gbp", "total_cost_gbp"])
                return False
        claims = _call_extraction(client, event, sources, refresh_run)
        result = _call_summary(client, event, sources, claims, refresh_run, is_update)
        now = timezone.now()
        event.title = result["title"][:110].rstrip()
        event.summary = remove_summary_filler(result["summary"])
        event.differences = [
            cleaned
            for difference in result["differences"]
            if difference_is_material_conflict(
                cleaned := replace_article_references(difference, sources)
            )
        ]
        event.timeline = result["timeline"]
        event.source_snapshot = sources
        event.generated_source_count = len(source_ids)
        event.generation_count += 1
        event.first_generated_at = event.first_generated_at or now
        event.last_generated_at = now
        event.next_generation_at = now + timedelta(
            minutes=settings.NEWSFLOW_EVENT_REGENERATION_MINUTES
        )
        event.status = (
            Event.Status.INDEXABLE
            if len(source_ids) >= budget.minimum_sources_for_indexing
            else Event.Status.GENERATED
        )
        event.last_error = ""
        event.save()
        after_cost = (
            event.ai_usage.aggregate(value=Sum("total_cost_gbp"))["value"] or Decimal("0")
        )
        generation_cost = after_cost - before_cost
        if is_update:
            event.update_cost_gbp += generation_cost
        else:
            event.initial_cost_gbp += generation_cost
        event.total_cost_gbp = after_cost
        event.save(
            update_fields=["initial_cost_gbp", "update_cost_gbp", "total_cost_gbp"]
        )
        return True
    except Exception as exc:
        event.status = Event.Status.FAILED
        event.last_error = str(exc)[:2000]
        event.save(update_fields=["status", "last_error"])
        return False
    finally:
        release_event_budget(reserved_amount)


def process_event_queue(refresh_run=None):
    merge_semantically_equivalent_candidates(refresh_run=refresh_run)
    stabilize_old_events()
    now = timezone.now()
    candidates = (
        Event.objects.filter(
            status__in=[
                Event.Status.PENDING,
                Event.Status.GENERATED,
                Event.Status.INDEXABLE,
                Event.Status.BUDGET_BLOCKED,
                Event.Status.FAILED,
            ]
        )
        .filter(Q(next_generation_at__lte=now) | Q(next_generation_at__isnull=True))
        .annotate(
            source_count=Count(
                "articles__source",
                filter=~Q(articles__source__slug__in=settings.NEWSFLOW_EVENT_EXCLUDED_SOURCE_SLUGS),
                distinct=True,
            )
        )
        .annotate(
            update_priority=Case(
                When(first_generated_at__isnull=False, then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by(
            "update_priority",
            "-source_count",
            "first_seen_at",
        )
    )
    created = 0
    updated = 0
    blocked = 0
    for event in candidates:
        was_generated = event.first_generated_at is not None
        if generate_event(event, refresh_run=refresh_run):
            if was_generated:
                updated += 1
            else:
                created += 1
        else:
            event.refresh_from_db(fields=["status"])
            if event.status == Event.Status.BUDGET_BLOCKED:
                blocked += 1
                # All later new candidates have lower priority; existing events may still
                # be blocked by the same cost ceiling, so end this run deterministically.
                break
    return created, updated, blocked
