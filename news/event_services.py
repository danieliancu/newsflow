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
        survivor.generated_source_count = survivor.articles.values("source_id").distinct().count()
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
    created = 0
    updated = 0
    roots = (
        Article.objects.filter(processing_status=Article.ProcessingStatus.PROCESSED)
        .filter(Q(duplicate_articles__isnull=False) | Q(duplicate_of__isnull=False))
        .values_list("duplicate_of_id", flat=True)
    )
    root_ids = {root_id for root_id in roots if root_id}
    root_ids.update(
        Article.objects.filter(duplicate_articles__isnull=False).values_list("pk", flat=True)
    )
    budget = EventBudget.get_solo()
    for root in Article.objects.filter(pk__in=root_ids).select_related("source"):
        members = list(
            Article.objects.filter(Q(pk=root.pk) | Q(duplicate_of=root))
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
        if new_count > previous_count and previous_count:
            updated += 1
        existing.last_article_at = latest
        if existing.status in {Event.Status.STABLE, Event.Status.FAILED}:
            existing.status = Event.Status.PENDING
        existing.save(update_fields=["last_article_at", "status"])
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
        event.articles.select_related("source")
        .order_by("published_at", "collected_at")
        .values(
            "id",
            "title",
            "first_paragraph",
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
        event.articles.select_related("source")
        .order_by("published_at", "collected_at")
        .values("title", "first_paragraph", "published_at", "source__name")[:8]
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


def confirmed_fact_is_subject_focused(fact, sources):
    text = fact.get("text", "")
    lowered = text.casefold()
    if any(source.get("source__name", "").casefold() in lowered for source in sources):
        return False
    return not re.search(
        r"\b(?:sursă|surse|sursa|sursele|articol|articolul|articole|articolele|publicația|publicațiile|relatare|relatări|relatările)\b",
        lowered,
    )


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
                    "confirmed_facts": event.confirmed_facts,
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
            "informațiilor disponibile: 90-120 de cuvinte pentru evenimente cu puține "
            "informații, 120-170 de cuvinte pentru majoritatea evenimentelor și 180-220 "
            "de cuvinte pentru subiecte complexe. Dezvoltă contextul, consecințele și "
            "legăturile dintre fapte atunci când acestea sunt susținute de surse. Urmărește "
            "cel puțin 90 de cuvinte, dar nu inventa, nu repeta și nu adăuga text de "
            "umplutură dacă sursele nu oferă suficiente informații relevante. "
            "Titlul trebuie să fie factual, autonom și să aibă maximum 110 caractere. "
            "Folosește exclusiv afirmațiile extrase. Fiecare fapt confirmat trebuie să aibă "
            "minimum două article_ids distincte. Evidențiază separat diferențele dintre surse. "
            "Scrie summary cu focus pe informații și într-un flux jurnalistic natural. "
            "Folosește un stil jurnalistic clar și fluent, cu tranziții firești între idei, "
            "vocabular variat și suficient context pentru ca relevanța faptelor să fie ușor de "
            "înțeles. Alternează natural structura propozițiilor și preferă verbe precise, fără "
            "a transforma sinteza într-o enumerare mecanică. Evită repetițiile, dramatizarea, "
            "adjectivele evaluative și formulările introduse doar pentru a lungi textul. "
            "Pentru "
            "faptele susținute de minimum două publicații, formulează informația direct, fără "
            "enumerarea publicațiilor și fără expresii precum «X relatează», «Y notează» sau "
            "«sursele spun». Dacă o informație relevantă este susținută de o singură publicație, "
            "o poți include în summary numai cu atribuirea explicită «Potrivit [numele "
            "publicației]...». Nu muta automat o asemenea informație în differences doar pentru "
            "că apare într-o singură relatare. Folosește differences exclusiv pentru contradicții, "
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
            "În confirmed_facts scrie exclusiv faptele comune despre subiect, direct și autonom. "
            "Nu menționa acolo publicații, surse, articole, procesul de comparare sau formulări "
            "precum «X și Y relatează». Nu include în confirmed_facts o informație susținută "
            "în realitate de o singură relatare. "
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
                        "confirmed_facts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string"},
                                    "article_ids": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                    },
                                },
                                "required": ["text", "article_ids"],
                                "additionalProperties": False,
                            },
                        },
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
                        "confirmed_facts",
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


def generate_event(event, refresh_run=None):
    sources = _event_sources(event)
    source_ids = {source["source_id"] for source in sources}
    reviewed_source_ids = {
        source.get("source_id") for source in event.source_snapshot if source.get("source_id")
    }
    budget = EventBudget.get_solo()
    if len(source_ids) < budget.minimum_sources_for_creation:
        return False
    if event.last_generated_at and reviewed_source_ids >= source_ids:
        return False
    if event.last_generated_at and not reviewed_source_ids and event.generated_source_count >= len(source_ids):
        return False
    if event.next_generation_at and event.next_generation_at > timezone.now():
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
        if is_update:
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
        allowed_ids = {source["id"] for source in sources}
        confirmed = [
            fact
            for fact in result["confirmed_facts"]
            if len(set(fact["article_ids"]) & allowed_ids) >= 2
            and confirmed_fact_is_subject_focused(fact, sources)
        ]
        now = timezone.now()
        event.title = result["title"][:110].rstrip()
        event.summary = result["summary"]
        event.confirmed_facts = confirmed
        event.differences = [
            replace_article_references(difference, sources)
            for difference in result["differences"]
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
        .annotate(source_count=Count("articles__source", distinct=True))
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
