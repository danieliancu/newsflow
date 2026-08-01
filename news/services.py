import hashlib
import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone as dt_timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import feedparser
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from taxonomy.models import Category, KeywordRule, Topic

from .models import Article, ArticleTopic, Source
from .ai_classifier import classify_article_with_ai

TRACKING_PARAMETERS = {"fbclid", "gclid", "ref", "source"}
TRACKING_PREFIXES = ("utm_",)
FIELD_WEIGHTS = (("title", 5), ("first_paragraph", 3))
DEDUPLICATION_WINDOW_HOURS = 48
TITLE_SIMILARITY_THRESHOLD = 0.62
LEAD_SIMILARITY_THRESHOLD = 0.72
STOP_WORDS = {
    "a", "ai", "al", "ale", "ale", "cu", "ca", "care", "ce", "de", "din", "dupa",
    "este", "fi", "fost", "in", "intr", "la", "le", "lui", "mai", "o", "pe", "pentru",
    "prin", "sa", "se", "si", "sunt", "un", "una", "unei", "unor",
}
BOILERPLATE_PREFIXES = (
    "abonează-te",
    "acceptă cookie",
    "citește și",
    "funcționăm ca organizație",
    "urmărește-ne",
)
BREADCRUMB_CATEGORY_MAP = {
    "externe": "Internațional",
    "international": "Internațional",
    "politica": "Politică",
    "economie": "Economie",
    "business": "Economie",
    "sport": "Sport",
    "sanatate": "Societate",
    "educatie": "Societate",
    "justitie": "Societate",
    "tehnologie": "Tehnologie",
    "stiinta": "Tehnologie",
    "mediu": "Mediu",
    "cultura": "Cultură",
}


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)).strip()


def decode_response_text(response):
    declared = (response.encoding or "").casefold()
    apparent = (response.apparent_encoding or "").casefold()
    latin_encodings = {"iso-8859-1", "latin-1", "windows-1252", "cp1252"}
    if (
        isinstance(response.content, (bytes, bytearray))
        and declared in latin_encodings
        and apparent in {"utf-8", "utf_8"}
    ):
        return response.content.decode("utf-8")
    return response.text


def normalize_text(value):
    return clean_text(value).casefold()


def comparison_tokens(value):
    normalized = unicodedata.normalize("NFKD", normalize_text(value))
    without_diacritics = "".join(character for character in normalized if not unicodedata.combining(character))
    without_source_suffix = re.sub(r"\s*[-–—|]\s*[^-–—|]{2,40}$", "", without_diacritics)
    return {
        token
        for token in re.findall(r"[a-z0-9]+", without_source_suffix)
        if len(token) > 1 and token not in STOP_WORDS
    }


def token_similarity(first, second):
    first_tokens = comparison_tokens(first)
    second_tokens = comparison_tokens(second)
    if not first_tokens or not second_tokens:
        return 0.0
    overlap = len(first_tokens & second_tokens)
    jaccard = overlap / len(first_tokens | second_tokens)
    containment = overlap / min(len(first_tokens), len(second_tokens))
    return (jaccard * 0.6) + (containment * 0.4)


def near_duplicate_score(first, second):
    title_score = token_similarity(first.title, second.title)
    paragraph_score = (
        token_similarity(first.first_paragraph, second.first_paragraph)
        if first.first_paragraph and second.first_paragraph
        else 0
    )
    if title_score >= TITLE_SIMILARITY_THRESHOLD:
        return title_score
    if title_score >= 0.48 and paragraph_score >= LEAD_SIMILARITY_THRESHOLD:
        return (title_score * 0.65) + (paragraph_score * 0.35)
    return 0.0


def assign_duplicate(article):
    reference_time = article.published_at or article.collected_at
    window_start = reference_time - timedelta(hours=DEDUPLICATION_WINDOW_HOURS)
    window_end = reference_time + timedelta(hours=DEDUPLICATION_WINDOW_HOURS)
    candidates = (
        Article.objects.filter(processing_status=Article.ProcessingStatus.PROCESSED)
        .filter(
            models.Q(published_at__range=(window_start, window_end))
            | models.Q(published_at__isnull=True, collected_at__range=(window_start, window_end))
        )
        .exclude(pk=article.pk)
        .exclude(duplicate_of=article)
        .order_by("published_at", "collected_at")
    )
    best_candidate = None
    best_score = 0.0
    for candidate in candidates:
        candidate_time = candidate.published_at or candidate.collected_at
        if candidate_time > reference_time or (
            candidate_time == reference_time and candidate.pk > article.pk
        ):
            continue
        score = near_duplicate_score(article, candidate)
        if score > best_score:
            best_candidate = candidate.duplicate_of or candidate
            best_score = score
    article.duplicate_of = best_candidate
    article.duplicate_score = best_score
    article.save(update_fields=["duplicate_of", "duplicate_score"])
    return best_candidate


def canonicalize_url(url):
    parts = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_PARAMETERS
        and not any(key.casefold().startswith(prefix) for prefix in TRACKING_PREFIXES)
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, urlencode(query), ""))


def content_fingerprint(title, first_paragraph, second_paragraph):
    payload = "|".join(normalize_text(value) for value in (title, first_paragraph))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _meta_content(soup, *selectors):
    for selector in selectors:
        element = soup.select_one(selector)
        if element and element.get("content"):
            return clean_text(element["content"])
    return ""


def extract_breadcrumbs(soup):
    sections = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or "")
        except (TypeError, json.JSONDecodeError):
            continue
        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if isinstance(node, dict) and "@graph" in node:
                nodes.extend(item for item in node["@graph"] if isinstance(item, dict))
            if not isinstance(node, dict) or node.get("@type") != "BreadcrumbList":
                continue
            for element in node.get("itemListElement", []):
                item = element.get("item", {}) if isinstance(element, dict) else {}
                name = item.get("name") if isinstance(item, dict) else None
                if name and normalize_text(name) not in {"home", "stiri", "știri"}:
                    sections.append(clean_text(name))
    return sections[:-1] if len(sections) > 1 else sections


def extract_image_url(soup, page_url):
    for selector in ('meta[property="og:image"]', 'meta[name="twitter:image"]'):
        element = soup.select_one(selector)
        candidate = str(element.get("content", "")).strip() if element else ""
        if not candidate:
            continue
        absolute_url = urljoin(page_url, candidate)
        if urlsplit(absolute_url).scheme.casefold() in {"http", "https"}:
            return absolute_url[:1000]
    return ""


def extract_image_url_from_html(html, page_url):
    return extract_image_url(BeautifulSoup(html, "html.parser"), page_url)


def extract_article(html, url):
    soup = BeautifulSoup(html, "html.parser")
    canonical = soup.select_one('link[rel="canonical"]')
    canonical_url = urljoin(url, canonical.get("href")) if canonical and canonical.get("href") else url
    title = _meta_content(soup, 'meta[property="og:title"]', 'meta[name="twitter:title"]')
    if not title and soup.title:
        title = clean_text(soup.title.string)
    article_root = soup.select_one("article") or soup.select_one("main") or soup
    title_element = article_root.find("h1") or soup.find("h1")
    candidates = title_element.find_all_next("p") if title_element else article_root.select("p")
    paragraphs = []
    seen = set()
    for paragraph in candidates:
        candidate = clean_text(paragraph.get_text(" ", strip=True))
        normalized_candidate = normalize_text(candidate)
        is_boilerplate = any(
            normalized_candidate.startswith(prefix) for prefix in BOILERPLATE_PREFIXES
        )
        if len(candidate) >= 40 and not is_boilerplate and normalized_candidate not in seen:
            paragraphs.append(candidate)
            seen.add(normalized_candidate)
        if paragraphs:
            break
    return {
        "canonical_url": canonicalize_url(canonical_url),
        "title": title,
        "first_paragraph": paragraphs[0] if paragraphs else "",
        "source_sections": extract_breadcrumbs(soup),
        "image_url": extract_image_url(soup, url),
    }


def classify_article(article, refresh_run=None):
    matches = {}
    source_category = None
    normalized_sections = {normalize_text(section) for section in article.source_sections}
    ascii_sections = {
        "".join(
            character
            for character in unicodedata.normalize("NFKD", section)
            if not unicodedata.combining(character)
        )
        for section in normalized_sections
    }
    for section in ascii_sections:
        category_name = BREADCRUMB_CATEGORY_MAP.get(section)
        if category_name:
            source_category = Category.objects.filter(name=category_name, is_active=True).first()
            if source_category:
                break
    for topic in Topic.objects.filter(is_active=True).select_related("category"):
        if normalize_text(topic.name) in normalized_sections:
            matches[topic.pk] = {
                "topic": topic,
                "score": 8,
                "keywords": set(),
                "reasons": [{"field": "breadcrumb", "keyword": topic.name, "occurrences": 1, "points": 8}],
            }

    for rule in KeywordRule.objects.filter(is_active=True, topic__is_active=True).select_related(
        "topic__category"
    ):
        phrase = normalize_text(rule.phrase)
        if not phrase:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.UNICODE)
        for field_name, weight in FIELD_WEIGHTS:
            field_value = getattr(article, field_name)
            if phrase == "ai":
                occurrences = len(re.findall(r"(?<!\w)AI(?!\w)", clean_text(field_value)))
            else:
                occurrences = len(pattern.findall(normalize_text(field_value)))
            if occurrences:
                match = matches.setdefault(
                    rule.topic_id,
                    {"topic": rule.topic, "score": 0, "keywords": set(), "reasons": []},
                )
                points = occurrences * weight
                match["score"] += points
                match["keywords"].add(rule.phrase)
                match["reasons"].append(
                    {"field": field_name, "keyword": rule.phrase, "occurrences": occurrences, "points": points}
                )

    with transaction.atomic():
        article.topic_matches.filter(is_manual=False).delete()
        for match in matches.values():
            ArticleTopic.objects.update_or_create(
                article=article,
                topic=match["topic"],
                defaults={
                    "score": match["score"],
                    "matched_keywords": sorted(match["keywords"]),
                    "reasons": match["reasons"],
                    "is_manual": False,
                },
            )
        category_scores = {}
        for topic_match in article.topic_matches.select_related("topic__category"):
            category = topic_match.topic.category
            category_scores[category] = category_scores.get(category, 0) + topic_match.score
        article.primary_category = (
            source_category
            or (max(category_scores, key=category_scores.get) if category_scores else None)
        )
        article.processing_status = Article.ProcessingStatus.PROCESSED
        article.last_error = ""
        article.save(update_fields=["primary_category", "processing_status", "last_error"])
    if article.primary_category_id is None:
        if (
            article.ai_suggested_category_id
            and article.ai_confidence is not None
            and article.ai_confidence >= settings.OPENAI_CLASSIFICATION_AUTO_THRESHOLD
        ):
            article.primary_category = article.ai_suggested_category
            article.save(update_fields=["primary_category"])
        elif article.ai_classified_at is None:
            classify_article_with_ai(article, refresh_run=refresh_run)
    return matches


def _can_fetch(url, session, robots_cache):
    domain = urlsplit(url).netloc
    if domain in robots_cache:
        parser = robots_cache[domain]
        return parser is None or parser.can_fetch(settings.NEWSFLOW_USER_AGENT, url)
    robots_url = f"https://{domain}/robots.txt"
    parser = RobotFileParser(robots_url)
    try:
        response = session.get(robots_url, timeout=settings.NEWSFLOW_REQUEST_TIMEOUT)
        if response.ok:
            parser.parse(response.text.splitlines())
            robots_cache[domain] = parser
            return parser.can_fetch(settings.NEWSFLOW_USER_AGENT, url)
    except requests.RequestException:
        pass
    robots_cache[domain] = None
    return True


def _published_at(entry):
    value = entry.get("published") or entry.get("updated")
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_timezone.utc)
    except (TypeError, ValueError, OverflowError):
        struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
        return datetime(*struct_time[:6], tzinfo=dt_timezone.utc) if struct_time else None


def ingest_source(source, refresh=False, refresh_run=None):
    headers = {"User-Agent": settings.NEWSFLOW_USER_AGENT}
    session = requests.Session()
    session.headers.update(headers)
    robots_cache = {}
    created_count = 0
    try:
        if not _can_fetch(source.feed_url, session, robots_cache):
            raise PermissionError("Accesul la feed este interzis de robots.txt.")
        feed_response = session.get(source.feed_url, timeout=settings.NEWSFLOW_REQUEST_TIMEOUT)
        feed_response.raise_for_status()
        feed = feedparser.parse(feed_response.content)
        if feed.bozo and not feed.entries:
            raise ValueError(f"Feed RSS invalid: {feed.bozo_exception}")

        for entry in feed.entries[: settings.NEWSFLOW_MAX_ENTRIES_PER_SOURCE]:
            raw_url = entry.get("link")
            if not raw_url:
                continue
            url = canonicalize_url(raw_url)
            existing = Article.objects.filter(canonical_url=url).first()
            if existing and existing.processing_status == Article.ProcessingStatus.PROCESSED and not refresh:
                continue
            if not _can_fetch(url, session, robots_cache):
                continue
            try:
                page_response = session.get(url, timeout=settings.NEWSFLOW_REQUEST_TIMEOUT)
                page_response.raise_for_status()
                extracted = extract_article(decode_response_text(page_response), url)
                title = extracted["title"] or clean_text(entry.get("title"))
                fingerprint = content_fingerprint(title, extracted["first_paragraph"], "")
                duplicate_query = Article.objects.filter(content_fingerprint=fingerprint)
                if existing:
                    duplicate_query = duplicate_query.exclude(pk=existing.pk)
                duplicate = duplicate_query.exists()
                if duplicate and not existing:
                    continue
                article = existing or Article(source=source)
                article.canonical_url = extracted["canonical_url"]
                article.title = title[:500]
                article.lead = ""
                article.first_paragraph = extracted["first_paragraph"]
                article.second_paragraph = ""
                article.author = ""
                article.image_url = extracted["image_url"]
                article.source_sections = extracted["source_sections"]
                article.published_at = _published_at(entry)
                article.content_fingerprint = fingerprint
                article.processing_attempts += 1
                article.processing_status = Article.ProcessingStatus.PENDING
                article.ai_suggested_category = None
                article.ai_confidence = None
                article.ai_reason = ""
                article.ai_model = ""
                article.ai_classified_at = None
                article.save()
                classify_article(article, refresh_run=refresh_run)
                assign_duplicate(article)
                created_count += 1
            except Exception as exc:
                if existing and existing.processing_status == Article.ProcessingStatus.PROCESSED and refresh:
                    existing.refresh_from_db()
                    existing.processing_attempts += 1
                    existing.last_error = str(exc)[:2000]
                    existing.save(update_fields=["processing_attempts", "last_error"])
                    continue
                failed = existing or Article(source=source, canonical_url=url)
                failed.title = clean_text(entry.get("title"))[:500] or url
                failed.published_at = _published_at(entry)
                failed.processing_status = Article.ProcessingStatus.FAILED
                failed.processing_attempts += 1
                failed.last_error = str(exc)[:2000]
                failed.save()

        source.last_checked_at = timezone.now()
        source.last_error = ""
        source.consecutive_errors = 0
        source.save(update_fields=["last_checked_at", "last_error", "consecutive_errors"])
    except Exception as exc:
        source.last_checked_at = timezone.now()
        source.last_error = str(exc)[:2000]
        source.consecutive_errors += 1
        source.save(update_fields=["last_checked_at", "last_error", "consecutive_errors"])
        raise
    return created_count
