from datetime import timedelta
import re
import unicodedata

from django.db.models import Q
from django.utils import timezone

from news.models import Article

from .models import Interaction

RANKING_CANDIDATE_LIMIT = 500


def _normalize_match_text(value):
    value = unicodedata.normalize("NFKD", (value or "").casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return " ".join(value.split())


def _matches_term(text, normalized_term):
    return bool(re.search(rf"(?<!\w){re.escape(normalized_term)}(?!\w)", text))


def _accent_tolerant_pattern(normalized_term):
    variants = {
        "a": "[aăâ]",
        "i": "[iî]",
        "s": "[sșş]",
        "t": "[tțţ]",
    }
    return "".join(
        r"\s+" if character.isspace() else variants.get(character, re.escape(character))
        for character in normalized_term
    )


def _recency_score(article, now):
    published = article.published_at or article.collected_at
    age = max(now - published, timedelta())
    return max(0.0, 3.0 - age.total_seconds() / 86400 / 2)


def ranked_feed(
    user,
    limit=50,
    category_ids=None,
    source_ids=None,
    topic_ids=None,
    personalized=True,
):
    articles = Article.objects.filter(
        processing_status=Article.ProcessingStatus.PROCESSED,
        duplicate_of__isnull=True,
    ).select_related("source", "primary_category").prefetch_related("topic_matches__topic")
    now = timezone.now()

    if not user.is_authenticated:
        if category_ids:
            articles = articles.filter(primary_category_id__in=category_ids)
        if source_ids:
            articles = articles.filter(source_id__in=source_ids)
        if topic_ids:
            articles = articles.filter(topic_matches__topic_id__in=topic_ids)
        return list(articles.distinct().order_by("-published_at", "-collected_at")[:limit])

    blocked_source_ids = set(
        user.source_preferences.filter(is_blocked=True).values_list("source_id", flat=True)
    )
    hidden_article_ids = set(
        user.interactions.filter(kind=Interaction.Kind.HIDDEN).values_list("article_id", flat=True)
    )
    articles = articles.exclude(source_id__in=blocked_source_ids).exclude(pk__in=hidden_article_ids)
    category_weights = dict(user.category_preferences.values_list("category_id", "weight"))
    source_weights = dict(
        user.source_preferences.filter(is_blocked=False).values_list("source_id", "weight")
    )
    topic_weights = dict(
        user.topic_preferences.filter(is_blocked=False).values_list("topic_id", "weight")
    )
    followed_terms = list(user.followed_terms.values_list("term", "normalized_term"))
    has_preferences = bool(category_weights or source_weights or topic_weights or followed_terms)
    seen_ids = set(
        user.interactions.filter(kind__in=[Interaction.Kind.SHOWN, Interaction.Kind.OPENED]).values_list(
            "article_id", flat=True
        )
    )

    candidate_ids = set(
        articles.values_list("pk", flat=True)[:RANKING_CANDIDATE_LIMIT]
    )
    if has_preferences:
        preferred_filter = Q()
        if category_weights:
            preferred_filter |= Q(primary_category_id__in=category_weights)
        if source_weights:
            preferred_filter |= Q(source_id__in=source_weights)
        if topic_weights:
            preferred_filter |= Q(topic_matches__topic_id__in=topic_weights)
        for term, normalized_term in followed_terms:
            tolerant_pattern = _accent_tolerant_pattern(normalized_term)
            preferred_filter |= (
                Q(title__icontains=term)
                | Q(lead__icontains=term)
                | Q(first_paragraph__icontains=term)
                | Q(second_paragraph__icontains=term)
                | Q(title__iregex=tolerant_pattern)
                | Q(lead__iregex=tolerant_pattern)
                | Q(first_paragraph__iregex=tolerant_pattern)
                | Q(second_paragraph__iregex=tolerant_pattern)
            )
        candidate_ids.update(
            articles.filter(preferred_filter).values_list("pk", flat=True)[
                :RANKING_CANDIDATE_LIMIT
            ]
        )

    ranked = []
    for article in articles.filter(pk__in=candidate_ids).distinct():
        score = _recency_score(article, now)
        matches_preferences = False
        reasons = [{"type": "recency", "points": round(score, 2)}]
        category_weight = category_weights.get(article.primary_category_id)
        if category_weight:
            matches_preferences = True
            points = 6 * category_weight
            score += points
            reasons.append({"type": "category", "name": article.primary_category.name, "points": points})
        source_weight = source_weights.get(article.source_id)
        if source_weight:
            matches_preferences = True
            points = 2 * source_weight
            score += points
            reasons.append({"type": "source", "name": article.source.name, "points": points})
        matched_topic = next(
            (
                match.topic
                for match in article.topic_matches.all()
                if match.topic_id in topic_weights
            ),
            None,
        )
        if matched_topic:
            matches_preferences = True
            points = 4 * topic_weights[matched_topic.pk]
            score += points
            reasons.append(
                {"type": "topic", "name": matched_topic.name, "points": points}
            )
        searchable_text = _normalize_match_text(
            " ".join(
                [
                    article.title,
                    article.lead,
                    article.first_paragraph,
                    article.second_paragraph,
                ]
            )
        )
        matched_term = next(
            (
                term
                for term, normalized_term in followed_terms
                if _matches_term(searchable_text, normalized_term)
            ),
            None,
        )
        if matched_term:
            matches_preferences = True
            score += 5
            reasons.append({"type": "term", "name": matched_term, "points": 5})
        if article.id in seen_ids:
            score -= 4
            reasons.append({"type": "already_seen", "points": -4})
        article.feed_score = score
        article.feed_reasons = reasons
        article.feed_reason = next(
            (reason for reason in reasons if reason["type"] != "recency"),
            None,
        )
        article.matches_preferences = matches_preferences if has_preferences else True
        ranked.append(article)

    if personalized:
        ranked.sort(
            key=lambda article: (
                article.matches_preferences,
                article.feed_score,
                article.published_at or article.collected_at,
            ),
            reverse=True,
        )
    else:
        ranked.sort(
            key=lambda article: article.published_at or article.collected_at,
            reverse=True,
        )
    return ranked[:limit]
