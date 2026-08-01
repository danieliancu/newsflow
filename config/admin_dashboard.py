from calendar import monthrange

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from accounts.models import User
from news.models import (
    AIUsage,
    Article,
    AutomaticUpdateSchedule,
    Event,
    EventBudget,
    RefreshRun,
    Source,
)
from recommendations.models import Interaction
from taxonomy.models import Category, Topic


def dashboard_callback(request, context):
    ai_totals = AIUsage.objects.aggregate(
        calls=Count("id"),
        input_tokens=Sum("input_tokens"),
        output_tokens=Sum("output_tokens"),
        total_tokens=Sum("total_tokens"),
        cost_usd=Sum("total_cost_usd"),
        cost_gbp=Sum("total_cost_gbp"),
    )
    interaction_counts = dict(
        Interaction.objects.values_list("kind").annotate(total=Count("id"))
    )
    total_articles = Article.objects.count()
    processed_articles = Article.objects.filter(processing_status="processed").count()
    refresh_count = RefreshRun.objects.count()
    event_budget = EventBudget.get_solo()
    automatic_schedule = AutomaticUpdateSchedule.get_solo()
    now = timezone.now()
    local_now = timezone.localtime(now)
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    event_usage = AIUsage.objects.filter(event__isnull=False)
    event_day_cost = event_usage.filter(created_at__gte=day_start).aggregate(
        value=Sum("total_cost_gbp")
    )["value"] or 0
    event_month_cost = event_usage.filter(created_at__gte=month_start).aggregate(
        value=Sum("total_cost_gbp")
    )["value"] or 0
    event_day_count = Event.objects.filter(first_generated_at__gte=day_start).count()
    event_month_count = Event.objects.filter(first_generated_at__gte=month_start).count()
    elapsed_days = max(1, local_now.day)
    days_in_month = monthrange(local_now.year, local_now.month)[1]
    projected_month_cost = event_month_cost / elapsed_days * days_in_month
    average_event_cost = (
        Event.objects.exclude(first_generated_at=None).aggregate(
            value=Avg("total_cost_gbp")
        )["value"]
        or 0
    )

    primary_metrics = [
        {
            "label": "Articole",
            "value": f"{total_articles:,}",
            "detail": f"{processed_articles:,} procesate",
            "tone": "red",
        },
        {
            "label": "Cost AI total",
            "value": f"£{ai_totals['cost_gbp'] or 0:.4f}",
            "detail": f"{ai_totals['calls'] or 0:,} apeluri",
            "tone": "green",
        },
        {
            "label": "Refresh-uri",
            "value": f"{refresh_count:,}",
            "detail": f"{RefreshRun.objects.filter(status__in=['completed', 'partial']).count():,} finalizate",
            "tone": "blue",
        },
        {
            "label": "Utilizatori",
            "value": f"{User.objects.count():,}",
            "detail": f"{User.objects.filter(is_active=True).count():,} activi",
            "tone": "violet",
        },
    ]
    content_metrics = [
        ("Articole eșuate", Article.objects.filter(processing_status="failed").count()),
        ("Duplicate", Article.objects.exclude(duplicate_of=None).count()),
        (
            "Fără categorie",
            Article.objects.filter(
                primary_category=None, processing_status="processed"
            ).count(),
        ),
        ("Categorii active", Category.objects.filter(is_active=True).count()),
        ("Subiecte active", Topic.objects.filter(is_active=True).count()),
    ]
    operation_metrics = [
        ("Surse active", Source.objects.filter(is_active=True).count()),
        ("Surse cu erori", Source.objects.filter(consecutive_errors__gt=0).count()),
        ("Refresh-uri omise", RefreshRun.objects.filter(status="skipped").count()),
        ("Tokeni AI", f"{ai_totals['total_tokens'] or 0:,}"),
        ("Cost AI USD", f"${ai_totals['cost_usd'] or 0:.4f}"),
        ("Buget evenimente azi", f"£{event_day_cost:.4f} / £{event_budget.max_cost_gbp_per_day}"),
        ("Buget evenimente lunar", f"£{event_month_cost:.4f} / £{event_budget.max_cost_gbp_per_month}"),
        ("Evenimente blocate", Event.objects.filter(status=Event.Status.BUDGET_BLOCKED).count()),
        (
            "Evenimente azi",
            f"{event_day_count} / {event_budget.max_new_events_per_day or '∞'}",
        ),
        (
            "Evenimente luna aceasta",
            f"{event_month_count} / {event_budget.max_new_events_per_month or '∞'}",
        ),
        ("Cost mediu/eveniment", f"£{average_event_cost:.4f}"),
        ("Proiecție cost lunar", f"£{projected_month_cost:.2f}"),
    ]
    engagement_metrics = [
        ("Articole deschise", interaction_counts.get("opened", 0)),
        ("Articole salvate", interaction_counts.get("saved", 0)),
        ("Articole ascunse", interaction_counts.get("hidden", 0)),
    ]

    articles_by_source = list(
        Source.objects.annotate(article_count=Count("articles"))
        .order_by("-article_count")[:10]
    )
    articles_by_category = list(
        Category.objects.annotate(article_count=Count("articles"))
        .order_by("-article_count")
    )
    source_max = max((row.article_count for row in articles_by_source), default=1)
    category_max = max((row.article_count for row in articles_by_category), default=1)
    for row in articles_by_source:
        row.dashboard_percent = round(row.article_count / source_max * 100)
    for row in articles_by_category:
        row.dashboard_percent = round(row.article_count / category_max * 100)

    context.update(
        {
            "primary_metrics": primary_metrics,
            "content_metrics": content_metrics,
            "operation_metrics": operation_metrics,
            "engagement_metrics": engagement_metrics,
            "ai_totals": ai_totals,
            "recent_refreshes": RefreshRun.objects.select_related("requested_by")[:12],
            "recent_ai_usage": AIUsage.objects.select_related(
                "article", "refresh_run"
            )[:20],
            "ai_by_model": AIUsage.objects.values("model", "is_estimated")
            .annotate(
                calls=Count("id"),
                input_tokens=Sum("input_tokens"),
                output_tokens=Sum("output_tokens"),
                cost_gbp=Sum("total_cost_gbp"),
            )
            .order_by("-calls"),
            "articles_by_source": articles_by_source,
            "articles_by_category": articles_by_category,
            "event_budget": event_budget,
            "automatic_schedule": automatic_schedule,
            "event_day_cost": event_day_cost,
            "event_month_cost": event_month_cost,
            "event_day_count": event_day_count,
            "event_month_count": event_month_count,
            "projected_month_cost": projected_month_cost,
            "average_event_cost": average_event_cost,
        }
    )
    return context
