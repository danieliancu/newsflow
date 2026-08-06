import json
import re
import unicodedata
from urllib.parse import urlencode
from copy import deepcopy
from datetime import date, timedelta
from urllib.parse import urljoin

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.db.utils import OperationalError
from django.db.models import Case, Count, IntegerField, Max, Q, Sum, Value, When
from django.db.models.functions import Coalesce, TruncDate
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.templatetags.static import static
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.html import escape
from django.utils.http import url_has_allowed_host_and_scheme

from news.models import Article, Event, EventBudget
from news.event_services import difference_is_material_conflict, eligible_event_articles
from accounts.forms import PreferenceForm
from accounts.models import User
from accounts.views import available_categories, preference_context
from news.models import Source
from taxonomy.models import Category, Topic

from .models import Interaction, OpenedEvent, SavedEvent
from .services import ranked_feed
from .technical_content import TECHNICAL_PAGES as TECHNICAL_PAGE_CONTENT


ROMANIAN_MONTHS = (
    "", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
    "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie",
)
GUEST_FILTER_SESSION_AGE = 60 * 60 * 24 * 30


def _event_timeline_for_display(timeline):
    displayed = []
    for item in timeline or []:
        displayed_item = dict(item)
        raw_date = item.get("date", "")
        month_year_match = re.fullmatch(r"(0?[1-9]|1[0-2])-(\d{4})", str(raw_date))
        year_month_match = re.fullmatch(r"(\d{4})-(0?[1-9]|1[0-2])", str(raw_date))
        if month_year_match:
            month, year = map(int, month_year_match.groups())
            displayed_item["display_date"] = f"{ROMANIAN_MONTHS[month]} {year}"
        elif year_month_match:
            year, month = map(int, year_month_match.groups())
            displayed_item["display_date"] = f"{ROMANIAN_MONTHS[month]} {year}"
        else:
            try:
                parsed = date.fromisoformat(str(raw_date)[:10])
                displayed_item["display_date"] = (
                    f"{parsed.day} {ROMANIAN_MONTHS[parsed.month]} {parsed.year}"
                )
            except (TypeError, ValueError):
                displayed_item["display_date"] = raw_date
        displayed.append(displayed_item)
    return displayed


def _event_seo_description(summary):
    """Use complete opening sentences instead of cutting the summary mid-sentence."""
    text = " ".join((summary or "").split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected = []
    for sentence in sentences:
        if selected and len(" ".join(selected + [sentence])) > 180:
            break
        selected.append(sentence)
        if len(" ".join(selected)) >= 130:
            break
    return " ".join(selected) or text


def _search_normalize(value):
    """Fold Romanian diacritics and Unicode variants for accent-insensitive search."""
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()


def _normalized_search_ids(rows, query, fields):
    needle = _search_normalize(query)
    return [
        row["id"]
        for row in rows
        if any(needle in _search_normalize(row.get(field)) for field in fields)
    ]


def _compact_schema(value):
    if isinstance(value, dict):
        return {
            key: compacted
            for key, item in value.items()
            if (compacted := _compact_schema(item)) not in (None, [], {})
        }
    if isinstance(value, list):
        return [
            compacted
            for item in value
            if (compacted := _compact_schema(item)) not in (None, [], {})
        ]
    return value


TECHNICAL_PAGES = {
    "about": {
        "title": "Despre Newsflow",
        "description": "Informații despre Newsflow și modul în care organizează știrile.",
        "intro": "Newsflow este un agregator care organizează știrile din publicații românești într-un flux simplu și ușor de personalizat.",
        "sections": [
            ("Ce facem", "Colectăm informații publicate de sursele partenere sau disponibile prin fluxurile lor publice și le organizăm pe categorii, subiecte și publicații."),
            ("Cum funcționează", "Titlurile, fragmentele și imaginile trimit întotdeauna către articolul original. Newsflow nu înlocuiește publicația care a realizat materialul."),
        ],
    },
    "terms": {
        "title": "Termeni și condiții",
        "description": "Termenii generali pentru utilizarea serviciului Newsflow.",
        "intro": "Prin folosirea Newsflow accepți regulile generale de utilizare descrise pe această pagină.",
        "sections": [
            ("Utilizarea serviciului", "Serviciul este oferit pentru informare și poate fi modificat, întrerupt sau actualizat pe măsură ce platforma evoluează."),
            ("Conținut extern", "Articolele aparțin publicațiilor originale. Disponibilitatea și corectitudinea lor sunt responsabilitatea sursei care le publică."),
        ],
    },
    "privacy": {
        "title": "Confidențialitate",
        "description": "Informații generale despre prelucrarea datelor în Newsflow.",
        "intro": "Newsflow folosește numai datele necesare funcționării contului și personalizării experienței.",
        "sections": [
            ("Datele contului", "Adresa de email este folosită pentru autentificare, verificarea contului și comunicări strict legate de serviciu."),
            ("Preferințe și activitate", "Preferințele, știrile salvate și istoricul sunt asociate contului pentru a putea fi sincronizate între dispozitive."),
        ],
    },
    "cookies": {
        "title": "Cookie-uri",
        "description": "Cum sunt folosite cookie-urile și stocarea locală în Newsflow.",
        "intro": "Platforma folosește cookie-uri și stocare locală pentru funcțiile esențiale și pentru memorarea unor alegeri.",
        "sections": [
            ("Cookie-uri esențiale", "Sunt necesare pentru autentificare, securitate și păstrarea sesiunii active."),
            ("Preferințe locale", "Browserul poate memora alegeri precum închiderea unei invitații, pentru a evita afișarea ei repetată."),
        ],
    },
    "contact": {
        "title": "Contact",
        "description": "Informații pentru a lua legătura cu echipa Newsflow.",
        "intro": "Poți contacta echipa pentru întrebări, sugestii, corecturi sau solicitări legate de conținut.",
        "sections": [
            ("Solicitări generale", "Datele complete de contact și formularul dedicat vor fi publicate aici înainte de lansarea oficială."),
            ("Publicații", "Reprezentanții publicațiilor pot solicita actualizarea informațiilor despre sursă sau verificarea modului de atribuire."),
        ],
    },
}


TECHNICAL_PAGES = TECHNICAL_PAGE_CONTENT


def _public_url(path):
    return urljoin(f"{settings.APP_PUBLIC_URL.rstrip('/')}/", path.lstrip("/"))


def _organization_schema():
    homepage = _public_url(reverse("feed"))
    organization = {
        "@type": "Organization",
        "@id": f"{homepage}#organization",
        "name": "Newsflow",
        "legalName": "GREEN HORIZON CONCEPTS S.R.L.",
        "url": homepage,
        "logo": {
            "@type": "ImageObject",
            "url": _public_url(static("favicon.svg")),
            "width": 64,
            "height": 64,
        },
    }
    if settings.PUBLIC_CONTACT_EMAIL:
        organization["email"] = settings.PUBLIC_CONTACT_EMAIL
        organization["contactPoint"] = {
            "@type": "ContactPoint",
            "contactType": "editorial",
            "email": settings.PUBLIC_CONTACT_EMAIL,
            "availableLanguage": "Romanian",
        }
    return organization


def technical_page(request, page_slug):
    page = deepcopy(TECHNICAL_PAGES.get(page_slug))
    if page is None:
        raise Http404
    if page_slug == "contact" and settings.PUBLIC_CONTACT_EMAIL:
        page["sections"].insert(
            1,
            ("Email", settings.PUBLIC_CONTACT_EMAIL),
        )
    return render(
        request,
        "recommendations/technical_page.html",
        {
            "technical_page": page,
            "canonical_url": _public_url(request.path),
            "og_title": f"{page['title']} · Newsflow",
            "og_description": page["description"],
            "public_contact_email": settings.PUBLIC_CONTACT_EMAIL,
        },
    )


def _wants_json(request):
    return "application/json" in request.headers.get("Accept", "")


def _eligible_articles():
    return (
        Article.objects.filter(
            processing_status=Article.ProcessingStatus.PROCESSED,
            duplicate_of__isnull=True,
        )
        .select_related("source", "primary_category")
        .prefetch_related("topic_matches__topic")
    )


def _public_events():
    return Event.objects.filter(
        status__in=[Event.Status.INDEXABLE, Event.Status.STABLE],
        summary__gt="",
    ).annotate(
        public_total_articles=Count("articles", distinct=True),
        public_eligible_articles=Count(
            "articles",
            filter=~Q(articles__source__slug__in=settings.NEWSFLOW_EVENT_EXCLUDED_SOURCE_SLUGS),
            distinct=True,
        ),
    ).filter(
        Q(public_total_articles=0) | Q(public_eligible_articles__gt=0)
    ).order_by("-last_article_at", "-last_generated_at")


def _topics_of_day_events():
    return _public_events()


def _with_representative_images(events):
    events = list(events)
    event_by_id = {event.pk: event for event in events}
    if not event_by_id:
        return events
    image_articles = (
        eligible_event_articles(Article.objects.filter(events__pk__in=event_by_id))
        .exclude(image_url="")
        .select_related("event_membership")
        .order_by("-published_at", "-collected_at")
    )
    for article in image_articles:
        event_id = article.event_membership.event_id
        event = event_by_id.get(event_id)
        if event and not hasattr(event, "representative_image_url"):
            event.representative_image_url = article.image_url
    for event in events:
        if not hasattr(event, "representative_image_url"):
            event.representative_image_url = ""
    return events


def _group_public_event_articles(articles, seen_event_ids=None):
    articles = list(articles)
    article_by_id = {article.pk: article for article in articles}
    if not article_by_id:
        return articles
    seen_event_ids = seen_event_ids if seen_event_ids is not None else set()
    event_article_ids = {
        article.pk
        for article in articles
        if article.source.slug not in settings.NEWSFLOW_EVENT_EXCLUDED_SOURCE_SLUGS
    }
    events = (
        _topics_of_day_events()
        .filter(articles__pk__in=event_article_ids)
        .prefetch_related("articles")
        .distinct()
    )
    for event in events:
        for article in event.articles.exclude(
            source__slug__in=settings.NEWSFLOW_EVENT_EXCLUDED_SOURCE_SLUGS
        ):
            if article.pk in article_by_id:
                article_by_id[article.pk].public_event = event
    grouped = []
    for article in articles:
        event = getattr(article, "public_event", None)
        if event and event.pk in seen_event_ids:
            continue
        if event:
            seen_event_ids.add(event.pk)
        grouped.append(article)
    return grouped


def _saved_ids(request):
    if not request.user.is_authenticated:
        return set()
    return set(
        request.user.interactions.filter(kind=Interaction.Kind.SAVED).values_list(
            "article_id", flat=True
        )
    )


def _saved_event_ids(request):
    if not request.user.is_authenticated:
        return set()
    return set(request.user.saved_events.values_list("event_id", flat=True))


def _archive_preference_ids(request):
    if request.user.is_authenticated:
        preferred_ids = set(
            request.user.source_preferences.filter(is_blocked=False).values_list(
                "source_id", flat=True
            )
        )
        blocked_ids = set(
            request.user.source_preferences.filter(is_blocked=True).values_list(
                "source_id", flat=True
            )
        )
        hidden_ids = set(
            request.user.interactions.filter(kind=Interaction.Kind.HIDDEN).values_list(
                "article_id", flat=True
            )
        )
        return preferred_ids, blocked_ids, hidden_ids

    requested_ids = [
        value for value in request.GET.getlist("preferred_sources") if value.isdigit()
    ]
    if requested_ids:
        preferred_ids = set(
            Source.objects.filter(is_active=True, pk__in=requested_ids).values_list(
                "pk", flat=True
            )
        )
        request.session["guest_preferred_source_ids"] = sorted(preferred_ids)
        request.session.set_expiry(GUEST_FILTER_SESSION_AGE)
    else:
        preferred_ids = set(request.session.get("guest_preferred_source_ids", []))
    return preferred_ids, set(), set()


def _archive_navigation(blocked_source_ids=None):
    blocked_source_ids = blocked_source_ids or set()
    articles = Article.objects.filter(
        processing_status=Article.ProcessingStatus.PROCESSED,
        duplicate_of__isnull=True,
    ).exclude(source_id__in=blocked_source_ids)
    return {
        "archive_categories": Category.objects.filter(
            is_active=True, articles__in=articles
        ).distinct(),
        "archive_sources": Source.objects.filter(
            is_active=True, articles__in=articles
        ).exclude(pk__in=blocked_source_ids).distinct(),
        "archive_topics": Topic.objects.filter(
            is_active=True, article_matches__article__in=articles
        ).distinct(),
    }


def _archive_response(
    request, entity, archive_type, queryset, title, description, extra_context=None
):
    preferred_source_ids, blocked_source_ids, hidden_article_ids = (
        _archive_preference_ids(request)
    )
    queryset = queryset.exclude(source_id__in=blocked_source_ids).exclude(
        pk__in=hidden_article_ids
    )
    if preferred_source_ids:
        queryset = queryset.annotate(
            archive_day=TruncDate(Coalesce("published_at", "collected_at")),
            preferred_source_order=Case(
                When(source_id__in=preferred_source_ids, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        ordered_queryset = queryset.order_by(
            "-archive_day",
            "preferred_source_order",
            "-published_at",
            "-collected_at",
        )
    else:
        ordered_queryset = queryset.order_by("-published_at", "-collected_at")
    today = timezone.localdate()
    current_articles_query = ordered_queryset.filter(published_at__date=today)
    current_article_ids = list(current_articles_query.values_list("pk", flat=True))
    previous_articles_query = ordered_queryset.exclude(pk__in=current_article_ids)
    page_obj = Paginator(previous_articles_query, 24).get_page(request.GET.get("page"))
    current_articles = list(current_articles_query) if page_obj.number == 1 else []
    previous_articles = list(page_obj.object_list)
    for article in current_articles + previous_articles:
        if article.source_id in preferred_source_ids:
            article.feed_reason = {"type": "preferred_source"}
    previous_article_groups = []
    for article in previous_articles:
        timestamp = article.published_at or article.collected_at
        article_day = timezone.localdate(timestamp)
        if (
            not previous_article_groups
            or previous_article_groups[-1]["date"] != article_day
        ):
            previous_article_groups.append({"date": article_day, "articles": []})
        previous_article_groups[-1]["articles"].append(article)

    path = reverse(f"{archive_type}_archive", kwargs={"slug": entity.slug})
    page_number = page_obj.number
    canonical_path = path if page_number == 1 else f"{path}?page={page_number}"
    canonical_url = _public_url(canonical_path)
    total_article_count = ordered_queryset.count()
    indexable = total_article_count >= 5
    breadcrumb_label = {
        "category": "Categorii",
        "source": "Publicații",
        "topic": "Subiecte",
    }[archive_type]
    item_list = [
        {
            "@type": "ListItem",
            "position": page_obj.start_index() + index,
            "url": article.canonical_url,
            "name": article.title,
        }
        for index, article in enumerate(current_articles + previous_articles)
    ]
    structured_data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": canonical_url,
                "url": canonical_url,
                "name": title,
                "description": description,
                "mainEntity": {"@type": "ItemList", "itemListElement": item_list},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Newsflow",
                        "item": _public_url(reverse("feed")),
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": breadcrumb_label,
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": entity.name,
                        "item": canonical_url,
                    },
                ],
            },
        ],
    }
    context = {
        "archive_entity": entity,
        "archive_type": archive_type,
        "archive_title": title,
        "archive_description": description,
        "page_obj": page_obj,
        "articles": current_articles + previous_articles,
        "current_articles": current_articles,
        "current_articles_count": len(current_articles),
        "today_date": today,
        "previous_article_groups": previous_article_groups,
        "total_article_count": total_article_count,
        "saved_ids": _saved_ids(request),
        "saved_event_ids": _saved_event_ids(request),
        "canonical_url": canonical_url,
        "robots_value": "index,follow" if indexable else "noindex,follow",
        "og_title": title,
        "og_description": description,
        "structured_data": json.dumps(structured_data, ensure_ascii=False).replace(
            "<", "\\u003c"
        ),
    }
    context.update(_archive_navigation(blocked_source_ids))
    if archive_type == "topic" and page_obj.number == 1:
        context["topic_events"] = _with_representative_images(
            Event.objects.filter(
                status__in=[Event.Status.INDEXABLE, Event.Status.STABLE],
                articles__topic_matches__topic=entity,
            )
            .filter(
                Q(first_generated_at__date=today)
                | Q(first_generated_at=None, last_generated_at__date=today)
            )
            .distinct()
            .order_by("-last_article_at")[:12]
        )
    context.update(extra_context or {})
    return render(request, "recommendations/archive.html", context)


def category_archive(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    return _archive_response(
        request,
        category,
        "category",
        _eligible_articles().filter(primary_category=category),
        category.seo_title or f"Știri {category.name} · Newsflow",
        category.seo_description
        or category.description
        or f"Cele mai recente știri din categoria {category.name}, selectate din publicații românești.",
    )


def legacy_category_archive(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    target = reverse("category_archive", kwargs={"slug": category.slug})
    page = request.GET.get("page")
    if page and page.isdigit() and int(page) > 1:
        target = f"{target}?page={page}"
    return redirect(target, permanent=True)


def _legacy_redirect(request, route_name, **kwargs):
    target = reverse(route_name, kwargs=kwargs or None)
    if request.GET:
        target = f"{target}?{request.GET.urlencode()}"
    return redirect(target, permanent=True)


def legacy_source_archive(request, slug):
    source = get_object_or_404(Source, slug=slug, is_active=True)
    return _legacy_redirect(request, "source_archive", slug=source.slug)


def legacy_topic_archive(request, slug):
    topic = get_object_or_404(Topic, slug=slug, is_active=True)
    return _legacy_redirect(request, "topic_archive", slug=topic.slug)


def legacy_search_results(request):
    return _legacy_redirect(request, "search_results")


def legacy_saved_news(request):
    return _legacy_redirect(request, "saved_news")


def source_archive(request, slug):
    source = get_object_or_404(Source, slug=slug, is_active=True)
    return _archive_response(
        request,
        source,
        "source",
        _eligible_articles().filter(source=source),
        source.seo_title or f"Știri {source.name} · Newsflow",
        source.seo_description
        or source.description
        or f"Cele mai recente știri publicate de {source.name}, într-un singur flux.",
    )


def topic_archive(request, slug):
    topic = get_object_or_404(Topic, slug=slug, is_active=True)
    return _archive_response(
        request,
        topic,
        "topic",
        _eligible_articles().filter(topic_matches__topic=topic).distinct(),
        topic.seo_title or f"Știri despre {topic.name} · Newsflow",
        topic.seo_description
        or topic.description
        or f"Ultimele știri și evoluții despre {topic.name}, din publicații românești.",
    )


def events_archive(request):
    public_events = _topics_of_day_events()
    today = timezone.localdate()
    current_events_query = public_events.filter(
        Q(first_generated_at__date=today)
        | Q(first_generated_at=None, last_generated_at__date=today)
    )
    current_event_ids = list(current_events_query.values_list("pk", flat=True))
    current_events = _with_representative_images(current_events_query)
    previous_events_query = public_events.exclude(pk__in=current_event_ids).order_by(
        "-first_generated_at", "-last_generated_at"
    )
    page_obj = Paginator(previous_events_query, 18).get_page(request.GET.get("page"))
    previous_events = _with_representative_images(page_obj.object_list)
    previous_event_groups = []
    for event in previous_events:
        timestamp = (
            event.first_generated_at
            or event.last_generated_at
            or event.last_article_at
            or event.first_seen_at
        )
        event_day = timezone.localdate(timestamp)
        if not previous_event_groups or previous_event_groups[-1]["date"] != event_day:
            previous_event_groups.append({"date": event_day, "events": []})
        previous_event_groups[-1]["events"].append(event)
    canonical_path = reverse("events_archive")
    if page_obj.number > 1:
        canonical_path = f"{canonical_path}?page={page_obj.number}"
    context = {
        "page_obj": page_obj,
        "current_events": current_events,
        "current_events_count": len(current_events),
        "today_date": today,
        "saved_event_ids": _saved_event_ids(request),
        "previous_event_groups": previous_event_groups,
        "canonical_url": _public_url(canonical_path),
        "robots_value": "index,follow",
        "og_title": "Subiectele zilei · Newsflow",
        "og_description": (
            "Știrile importante, reunite și comparate din mai multe surse, "
            "actualizate pe măsură ce apar informații noi."
        ),
    }
    context.update(_archive_navigation())
    return render(request, "recommendations/events_archive.html", context)


def legacy_event_detail(request, slug, event_id):
    clean_slug = f"{slug}-{event_id}"
    if _public_events().filter(slug=clean_slug).exists():
        return event_detail(request, clean_slug)
    event = get_object_or_404(
        Event,
        pk=event_id,
        status__in=[
            Event.Status.GENERATED,
            Event.Status.INDEXABLE,
            Event.Status.STABLE,
        ],
    )
    return redirect("event_detail", slug=event.slug, permanent=True)


def event_detail(request, slug):
    event = get_object_or_404(
        Event.objects.prefetch_related("articles__source"),
        slug=slug,
        status__in=[
            Event.Status.GENERATED,
            Event.Status.INDEXABLE,
            Event.Status.STABLE,
        ],
    )
    event.display_differences = [
        difference
        for difference in event.differences
        if difference_is_material_conflict(difference)
    ]
    if request.user.is_authenticated:
        opened_event, _ = OpenedEvent.objects.get_or_create(
            user=request.user,
            event=event,
        )
        OpenedEvent.objects.filter(pk=opened_event.pk).update(updated_at=timezone.now())
    articles = list(
        eligible_event_articles(event.articles.select_related("source", "primary_category")).order_by(
            "published_at", "collected_at"
        )
    )
    related_events = _with_representative_images(
        _public_events().exclude(pk=event.pk)[:8]
    )
    event_position = event.last_article_at or event.first_seen_at
    previous_event = (
        _public_events()
        .filter(
            Q(last_article_at__gt=event_position)
            | Q(last_article_at=event_position, pk__gt=event.pk)
        )
        .order_by("last_article_at", "pk")
        .first()
    )
    next_event = (
        _public_events()
        .filter(
            Q(last_article_at__lt=event_position)
            | Q(last_article_at=event_position, pk__lt=event.pk)
        )
        .order_by("-last_article_at", "-pk")
        .first()
    )
    event.representative_image_url = next(
        (article.image_url for article in reversed(list(articles)) if article.image_url),
        "",
    )
    canonical_url = _public_url(event.public_path)
    seo_description = _event_seo_description(event.summary)
    article_schema_id = f"{canonical_url}#article"
    breadcrumb_schema_id = f"{canonical_url}#breadcrumb"
    structured_data = _compact_schema({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "NewsArticle",
                "@id": article_schema_id,
                "mainEntityOfPage": {"@id": canonical_url},
                "headline": event.title,
                "description": seo_description,
                "image": [event.representative_image_url]
                if event.representative_image_url
                else [],
                "datePublished": event.first_generated_at.isoformat()
                if event.first_generated_at
                else None,
                "dateModified": event.last_generated_at.isoformat()
                if event.last_generated_at
                else None,
                "author": {
                    "@type": "Organization",
                    "name": "Redacția Newsflow",
                    "url": _public_url(reverse("about")),
                },
                "publisher": {
                    "@id": f"{_public_url(reverse('feed'))}#organization",
                },
                "isAccessibleForFree": True,
                "citation": [article.canonical_url for article in articles],
            },
            {
                "@type": "WebPage",
                "@id": canonical_url,
                "url": canonical_url,
                "name": event.title,
                "breadcrumb": {"@id": breadcrumb_schema_id},
                "mainEntity": {"@id": article_schema_id},
            },
            _organization_schema(),
            {
                "@type": "BreadcrumbList",
                "@id": breadcrumb_schema_id,
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Newsflow",
                        "item": _public_url(reverse("feed")),
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": "Subiecte",
                        "item": _public_url(reverse("events_archive")),
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": event.title,
                    },
                ],
            },
        ],
    })
    budget = EventBudget.get_solo()
    event_timeline = _event_timeline_for_display(event.timeline)
    timeline_dates = {
        str(item.get("date", ""))[:10]
        for item in event.timeline or []
        if item.get("date")
    }
    return render(
        request,
        "recommendations/event_detail.html",
        {
            "event": event,
            "articles": articles,
            "event_timeline": event_timeline,
            "show_event_timeline": len(timeline_dates) > 1,
            "related_events": related_events,
            "previous_event": previous_event,
            "next_event": next_event,
            "canonical_url": canonical_url,
            "robots_value": (
                "index,follow,max-image-preview:large"
                if event.status in [Event.Status.INDEXABLE, Event.Status.STABLE]
                and event.generated_source_count >= budget.minimum_sources_for_indexing
                else "noindex,follow"
            ),
            "og_title": event.title,
            "og_description": seo_description,
            "og_image": event.representative_image_url,
            "structured_data": json.dumps(
                structured_data, ensure_ascii=False
            ).replace("<", "\\u003c"),
            "event_is_saved": (
                request.user.is_authenticated
                and request.user.saved_events.filter(event=event).exists()
            ),
        },
    )


def feed(request):
    raw_categories = request.GET.getlist("categories")
    filter_keys = set(request.GET) - {"page"}
    if request.user.is_authenticated and len(raw_categories) == 1 and filter_keys == {"categories"}:
        value = raw_categories[0]
        category = (
            Category.objects.filter(pk=int(value)).first()
            if value.isdigit()
            else Category.objects.filter(slug=value).first()
        )
        if category:
            target = reverse("category_archive", kwargs={"slug": category.slug})
            page = request.GET.get("page")
            if page and page.isdigit() and int(page) > 1:
                target = f"{target}?page={page}"
            return redirect(target, permanent=True)

    selected_category_ids = set()
    selected_category_slugs = set()
    selected_source_ids = set()
    selected_topic_ids = set()
    selected_topic = None
    if not request.user.is_authenticated:
        filters_submitted = (
            request.GET.get("guest_filters_submitted") == "1"
            or any(
                key in request.GET
                for key in ("categories", "preferred_sources", "topic")
            )
        )
        if filters_submitted:
            requested_category_slugs = [
                value for value in request.GET.getlist("categories") if value
            ]
            requested_source_ids = [
                value
                for value in request.GET.getlist("preferred_sources")
                if value.isdigit()
            ]
        else:
            requested_category_slugs = list(
                request.session.get("guest_followed_category_slugs", [])
            )
            requested_source_ids = [
                str(value)
                for value in request.session.get("guest_preferred_source_ids", [])
            ]
        selected_categories = Category.objects.filter(
            is_active=True, slug__in=requested_category_slugs
        )
        selected_category_ids = set(selected_categories.values_list("pk", flat=True))
        selected_category_slugs = set(selected_categories.values_list("slug", flat=True))
        selected_source_ids = set(
            Source.objects.filter(
                is_active=True, pk__in=requested_source_ids
            ).values_list("pk", flat=True)
        )
        if filters_submitted:
            request.session["guest_followed_category_slugs"] = sorted(
                selected_category_slugs
            )
            request.session["guest_preferred_source_ids"] = sorted(selected_source_ids)
            request.session.set_expiry(GUEST_FILTER_SESSION_AGE)
        for topic_slug in request.GET.getlist("topic"):
            selected_topic = Topic.objects.filter(
                is_active=True, slug=topic_slug
            ).first()
            if selected_topic:
                selected_topic_ids = {selected_topic.pk}
                break
    if request.user.is_authenticated:
        requested_feed_mode = request.GET.get("view")
        if requested_feed_mode in {"for-you", "latest"}:
            feed_mode = requested_feed_mode
            if request.user.feed_mode != feed_mode:
                request.user.feed_mode = feed_mode
                request.user.save(update_fields=["feed_mode", "updated_at"])
        else:
            feed_mode = request.user.feed_mode
    else:
        feed_mode = "latest"
    articles = ranked_feed(
        request.user,
        category_ids=selected_category_ids,
        source_ids=selected_source_ids,
        topic_ids=selected_topic_ids,
        personalized=feed_mode == "for-you",
    )
    other_articles = []
    if request.user.is_authenticated and feed_mode == "for-you":
        other_articles = [article for article in articles if not article.matches_preferences]
        articles = [article for article in articles if article.matches_preferences]
    seen_event_ids = set()
    articles = _group_public_event_articles(articles, seen_event_ids)
    other_articles = _group_public_event_articles(other_articles, seen_event_ids)
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            request.user.interactions.filter(kind=Interaction.Kind.SAVED).values_list("article_id", flat=True)
        )
    context = {
        "articles": articles,
        "other_articles": other_articles,
        "saved_ids": saved_ids,
        "featured_events": _with_representative_images(_topics_of_day_events()[:9]),
        "canonical_url": _public_url(request.path),
        "robots_value": (
            "noindex,follow"
            if request.GET or selected_category_ids or selected_source_ids
            else "index,follow"
        ),
        "og_title": "Newsflow · Știrile tale, fără zgomot",
        "og_description": "Cele mai recente știri din România, organizate pe categorii și publicații.",
    }
    context["feed_mode"] = feed_mode
    if request.user.is_authenticated:
        new_articles = Article.objects.filter(
            processing_status=Article.ProcessingStatus.PROCESSED,
            duplicate_of__isnull=True,
        )
        if request.user.last_feed_seen_at:
            new_articles = new_articles.filter(
                Q(published_at__gt=request.user.last_feed_seen_at)
                | Q(
                    published_at__isnull=True,
                    collected_at__gt=request.user.last_feed_seen_at,
                )
            )
        context["new_articles_count"] = new_articles.count()
    if not request.GET:
        homepage_items = [
            {
                "@type": "ListItem",
                "position": index + 1,
                "url": article.canonical_url,
                "name": article.title,
            }
            for index, article in enumerate([*articles, *other_articles])
        ]
        homepage = context["canonical_url"]
        context["structured_data"] = json.dumps(
            {
                "@context": "https://schema.org",
                "@graph": [
                    _organization_schema(),
                    {
                        "@type": "WebSite",
                        "@id": f"{homepage}#website",
                        "url": homepage,
                        "name": "Newsflow",
                        "publisher": {"@id": f"{homepage}#organization"},
                        "potentialAction": {
                            "@type": "SearchAction",
                            "target": {
                                "@type": "EntryPoint",
                                "urlTemplate": _public_url("/search/?q={search_term_string}"),
                            },
                            "query-input": "required name=search_term_string",
                        },
                    },
                    {
                        "@type": "CollectionPage",
                        "@id": homepage,
                        "url": homepage,
                        "name": "Newsflow",
                        "description": context["og_description"],
                        "isPartOf": {"@id": f"{homepage}#website"},
                        "mainEntity": {
                            "@type": "ItemList",
                            "itemListElement": homepage_items,
                        },
                    },
                ],
            },
            ensure_ascii=False,
        ).replace("<", "\\u003c")
    if request.user.is_authenticated:
        context.update(preference_context(PreferenceForm(user=request.user)))
    else:
        normalized_filters = []
        normalized_filters.extend(
            ("categories", slug) for slug in sorted(selected_category_slugs)
        )
        normalized_filters.extend(
            ("preferred_sources", source_id) for source_id in sorted(selected_source_ids)
        )
        if selected_topic:
            normalized_filters.append(("topic", selected_topic.slug))
        guest_filter_path = reverse("feed")
        if normalized_filters:
            guest_filter_path = f"{guest_filter_path}?{urlencode(normalized_filters)}"
        context.update(
            {
                "preference_categories": available_categories(),
                "preference_sources": Source.objects.filter(is_active=True).order_by("name"),
                "selected_category_ids": selected_category_ids,
                "selected_category_slugs": selected_category_slugs,
                "selected_source_ids": selected_source_ids,
                "selected_topic_ids": selected_topic_ids,
                "selected_guest_topic": selected_topic,
                "guest_filter_path": guest_filter_path,
                "guest_auth_next": guest_filter_path,
                "has_selected_sources": bool(selected_source_ids),
                "has_selected_categories": bool(selected_category_ids),
                "has_selected_topics": bool(selected_topic_ids),
                "preference_topics": Topic.objects.filter(is_active=True)
                .select_related("category")
                .order_by("category__name", "name"),
            }
        )
    return render(request, "recommendations/feed.html", context)


@require_POST
@login_required
def track_shown_articles(request):
    try:
        payload = json.loads(request.body or "{}")
    except (TypeError, json.JSONDecodeError):
        return JsonResponse({"error": "Payload invalid."}, status=400)
    raw_ids = payload.get("article_ids")
    if not isinstance(raw_ids, list) or len(raw_ids) > 50:
        return JsonResponse({"error": "Sunt permise maximum 50 de articole."}, status=400)
    try:
        article_ids = {int(value) for value in raw_ids}
    except (TypeError, ValueError):
        return JsonResponse({"error": "ID-uri invalide."}, status=400)
    if any(article_id <= 0 for article_id in article_ids):
        return JsonResponse({"error": "ID-uri invalide."}, status=400)

    eligible_ids = Article.objects.filter(
        pk__in=article_ids,
        processing_status=Article.ProcessingStatus.PROCESSED,
        duplicate_of__isnull=True,
    ).values_list("pk", flat=True)
    try:
        Interaction.objects.bulk_create(
            [
                Interaction(
                    user=request.user,
                    article_id=article_id,
                    kind=Interaction.Kind.SHOWN,
                )
                for article_id in eligible_ids
            ],
            ignore_conflicts=True,
        )
        User.objects.filter(pk=request.user.pk).update(
            last_feed_seen_at=timezone.now()
        )
    except OperationalError:
        return JsonResponse({"tracked": False}, status=202)
    return JsonResponse({"tracked": True})


def search_results(request):
    query = request.GET.get("q", "").strip()
    articles = Article.objects.none()
    events = Event.objects.none()
    if query:
        article_base = (
            Article.objects.filter(
                processing_status=Article.ProcessingStatus.PROCESSED,
                duplicate_of__isnull=True,
            )
            .select_related("source", "primary_category")
            .prefetch_related("topic_matches__topic")
        )
        article_ids = _normalized_search_ids(
            article_base.values("id", "title", "first_paragraph", "source__name"),
            query,
            ("title", "first_paragraph", "source__name"),
        )
        articles = article_base.filter(pk__in=article_ids).order_by(
            "-published_at", "-collected_at"
        )
        event_base = _topics_of_day_events()
        event_ids = _normalized_search_ids(
            event_base.values("id", "title", "summary"),
            query,
            ("title", "summary"),
        )
        events = event_base.filter(pk__in=event_ids)[:12]
    page_obj = Paginator(articles, 24).get_page(request.GET.get("page"))
    events = _with_representative_images(events)
    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            request.user.interactions.filter(kind=Interaction.Kind.SAVED).values_list(
                "article_id", flat=True
            )
        )
    return render(
        request,
        "recommendations/search_results.html",
        {
            "query": query,
            "page_obj": page_obj,
            "articles": page_obj.object_list,
            "events": events,
            "events_count": len(events),
            "total_results": page_obj.paginator.count + len(events),
            "saved_ids": saved_ids,
            "saved_event_ids": _saved_event_ids(request),
            "canonical_url": _public_url(request.path),
        },
    )


def sitemap(request):
    base_articles = Article.objects.filter(
        processing_status=Article.ProcessingStatus.PROCESSED,
        duplicate_of__isnull=True,
    )
    homepage_dates = base_articles.aggregate(
        latest_published=Max("published_at"), latest_collected=Max("collected_at")
    )
    entries = [
        (
            _public_url(reverse("feed")),
            homepage_dates["latest_published"] or homepage_dates["latest_collected"],
        )
    ]
    entries.extend(
        (_public_url(reverse(route_name)), None)
        for route_name in ("about", "contact", "terms", "privacy", "cookies")
    )
    archive_specs = [
        (
            Category.objects.filter(is_active=True)
            .annotate(article_count=Count("articles", filter=Q(
                articles__processing_status=Article.ProcessingStatus.PROCESSED,
                articles__duplicate_of__isnull=True,
            )))
            .filter(article_count__gte=5),
            "category_archive",
            "articles",
        ),
        (
            Source.objects.filter(is_active=True)
            .annotate(article_count=Count("articles", filter=Q(
                articles__processing_status=Article.ProcessingStatus.PROCESSED,
                articles__duplicate_of__isnull=True,
            )))
            .filter(article_count__gte=5),
            "source_archive",
            "articles",
        ),
        (
            Topic.objects.filter(is_active=True)
            .annotate(article_count=Count("article_matches", filter=Q(
                article_matches__article__processing_status=Article.ProcessingStatus.PROCESSED,
                article_matches__article__duplicate_of__isnull=True,
            )))
            .filter(article_count__gte=5),
            "topic_archive",
            "article_matches",
        ),
    ]
    for entities, route_name, relation in archive_specs:
        for entity in entities:
            if relation == "article_matches":
                archive_articles = base_articles.filter(topic_matches__topic=entity)
            elif route_name == "category_archive":
                archive_articles = base_articles.filter(primary_category=entity)
            else:
                archive_articles = base_articles.filter(source=entity)
            archive_dates = archive_articles.aggregate(
                latest_published=Max("published_at"),
                latest_collected=Max("collected_at"),
            )
            lastmod = archive_dates["latest_published"] or archive_dates["latest_collected"]
            entries.append(
                (_public_url(reverse(route_name, kwargs={"slug": entity.slug})), lastmod)
            )
    entries.extend(
        (_public_url(event.public_path), event.last_generated_at)
        for event in Event.objects.filter(
            status__in=[Event.Status.INDEXABLE, Event.Status.STABLE]
        ).exclude(last_generated_at=None)
    )
    urls = []
    for location, lastmod in entries:
        lastmod_xml = (
            f"<lastmod>{lastmod.date().isoformat()}</lastmod>" if lastmod else ""
        )
        urls.append(f"<url><loc>{escape(location)}</loc>{lastmod_xml}</url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls)
        + "</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml")


def news_sitemap(request):
    cutoff = timezone.now() - timedelta(days=2)
    events = (
        Event.objects.filter(
            status__in=[Event.Status.INDEXABLE, Event.Status.STABLE],
            first_generated_at__gte=cutoff,
        )
        .exclude(first_generated_at=None)
        .order_by("-first_generated_at")[:1000]
    )
    urls = []
    for event in events:
        urls.append(
            "<url>"
            f"<loc>{escape(_public_url(event.public_path))}</loc>"
            "<news:news>"
            "<news:publication>"
            "<news:name>Newsflow</news:name>"
            "<news:language>ro</news:language>"
            "</news:publication>"
            f"<news:publication_date>{event.first_generated_at.isoformat()}</news:publication_date>"
            f"<news:title>{escape(event.title)}</news:title>"
            "</news:news>"
            "</url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">'
        + "".join(urls)
        + "</urlset>"
    )
    return HttpResponse(xml, content_type="application/xml")


def robots_txt(request):
    body = (
        "User-agent: *\nAllow: /\n\n"
        f"Sitemap: {_public_url(reverse('sitemap'))}\n"
        f"Sitemap: {_public_url(reverse('news_sitemap'))}\n"
    )
    return HttpResponse(body, content_type="text/plain")


@login_required
def saved_news(request):
    saved_article_ids = (
        request.user.interactions.filter(kind=Interaction.Kind.SAVED)
        .values_list("article_id", flat=True)
        .distinct()
    )
    articles = (
        Article.objects.filter(pk__in=saved_article_ids)
        .select_related("source", "primary_category")
        .order_by("-published_at", "-collected_at")
    )
    events = _with_representative_images(
        _public_events().filter(saved_by__user=request.user).distinct()
    )
    return render(
        request,
        "recommendations/saved.html",
        {
            "articles": articles,
            "events": events,
            "saved_ids": set(saved_article_ids),
            "saved_event_ids": _saved_event_ids(request),
        },
    )


@login_required
def recently_read(request):
    opened_ids = list(
        request.user.interactions.filter(kind=Interaction.Kind.OPENED)
        .order_by("-updated_at")
        .values_list("article_id", flat=True)
    )
    articles_by_id = {
        article.pk: article
        for article in Article.objects.filter(pk__in=opened_ids)
        .select_related("source", "primary_category")
        .prefetch_related("topic_matches__topic")
    }
    articles = [
        articles_by_id[article_id]
        for article_id in opened_ids
        if article_id in articles_by_id
    ]
    opened_event_ids = list(
        request.user.opened_events.order_by("-updated_at").values_list(
            "event_id", flat=True
        )
    )
    events_by_id = {
        event.pk: event
        for event in _with_representative_images(
            _public_events().filter(pk__in=opened_event_ids)
        )
    }
    events = [
        events_by_id[event_id]
        for event_id in opened_event_ids
        if event_id in events_by_id
    ]
    return render(
        request,
        "recommendations/recently_read.html",
        {
            "articles": articles,
            "events": events,
            "saved_ids": _saved_ids(request),
            "saved_event_ids": _saved_event_ids(request),
        },
    )


@login_required
def hidden_content(request):
    hidden_ids = request.user.interactions.filter(
        kind=Interaction.Kind.HIDDEN
    ).values_list("article_id", flat=True)
    articles = (
        Article.objects.filter(pk__in=hidden_ids)
        .select_related("source", "primary_category")
        .prefetch_related("topic_matches__topic")
        .order_by("-published_at", "-collected_at")
    )
    blocked_sources = Source.objects.filter(
        sourcepreference__user=request.user,
        sourcepreference__is_blocked=True,
    ).order_by("name")
    return render(
        request,
        "recommendations/hidden_content.html",
        {"articles": articles, "blocked_sources": blocked_sources},
    )


@login_required
def open_article(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    interaction, _ = Interaction.objects.get_or_create(
        user=request.user,
        article=article,
        kind=Interaction.Kind.OPENED,
    )
    Interaction.objects.filter(pk=interaction.pk).update(updated_at=timezone.now())
    return redirect(article.canonical_url)


@require_POST
@login_required
def toggle_saved(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    saved = Interaction.objects.filter(
        user=request.user, article=article, kind=Interaction.Kind.SAVED
    )
    if saved.exists():
        saved.delete()
        is_saved = False
        if not _wants_json(request):
            messages.info(request, "Articolul a fost scos din lista salvată.")
    else:
        Interaction.objects.create(user=request.user, article=article, kind=Interaction.Kind.SAVED)
        is_saved = True
        if not _wants_json(request):
            messages.success(request, "Articol salvat.")
    if _wants_json(request):
        return JsonResponse(
            {
                "saved": is_saved,
                "saved_count": request.user.interactions.filter(
                    kind=Interaction.Kind.SAVED
                ).count(),
            }
        )
    return redirect("saved_news" if request.POST.get("next") == "saved" else "feed")


@require_POST
@login_required
def toggle_saved_event(request, event_id):
    event = get_object_or_404(_public_events(), pk=event_id)
    saved = SavedEvent.objects.filter(user=request.user, event=event)
    if saved.exists():
        saved.delete()
        is_saved = False
        messages.info(request, "Subiectul a fost scos din lista salvată.")
    else:
        SavedEvent.objects.create(user=request.user, event=event)
        is_saved = True
        messages.success(request, "Subiect salvat.")
    if _wants_json(request):
        article_count = request.user.interactions.filter(
            kind=Interaction.Kind.SAVED
        ).count()
        return JsonResponse(
            {
                "saved": is_saved,
                "saved_count": article_count + request.user.saved_events.count(),
            }
        )
    target = request.POST.get("next", reverse("events_archive"))
    if target == "saved":
        target = reverse("saved_news")
    elif not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = reverse("events_archive")
    return redirect(target)


@require_POST
@login_required
def hide_article(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    with transaction.atomic():
        Interaction.objects.get_or_create(
            user=request.user, article=article, kind=Interaction.Kind.HIDDEN
        )
    if _wants_json(request):
        return JsonResponse(
            {
                "hidden": True,
                "undo_url": reverse(
                    "restore_article", kwargs={"article_id": article.pk}
                ),
            }
        )
    messages.info(request, "Articolul nu va mai apărea în flux.")
    return redirect("feed")


@require_POST
@login_required
def restore_article(request, article_id):
    Interaction.objects.filter(
        user=request.user,
        article_id=article_id,
        kind=Interaction.Kind.HIDDEN,
    ).delete()
    if _wants_json(request):
        return JsonResponse({"hidden": False})
    messages.success(request, "Știrea a fost restaurată.")
    return redirect("hidden_content")


@require_POST
@login_required
def restore_source(request, source_id):
    request.user.source_preferences.filter(
        source_id=source_id,
        is_blocked=True,
    ).delete()
    messages.success(request, "Publicația a fost restaurată.")
    return redirect("hidden_content")


@require_POST
@login_required
def set_display_mode(request):
    mode = request.POST.get("mode")
    valid_modes = {choice for choice, _ in request.user.FeedDisplayMode.choices}
    if mode not in valid_modes:
        return JsonResponse({"error": "Mod invalid."}, status=400)
    User.objects.filter(pk=request.user.pk).update(
        feed_display_mode=mode
    )
    request.user.feed_display_mode = mode
    if _wants_json(request):
        return JsonResponse({"mode": mode})
    return redirect("account_dashboard")


@require_POST
@login_required
def set_events_display_mode(request):
    mode = request.POST.get("mode")
    valid_modes = {
        request.user.EventsDisplayMode.CARDS,
        request.user.EventsDisplayMode.COMPACT,
    }
    if mode not in valid_modes:
        return JsonResponse({"error": "Mod invalid."}, status=400)
    User.objects.filter(pk=request.user.pk).update(events_display_mode=mode)
    request.user.events_display_mode = mode
    if _wants_json(request):
        return JsonResponse({"mode": mode})
    return redirect("feed")
