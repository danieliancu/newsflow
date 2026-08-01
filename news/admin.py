from django.contrib import admin
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import (
    AIUsage,
    Article,
    ArticleTopic,
    Event,
    EventAIUsage,
    EventArticle,
    EventBudget,
    AutomaticUpdateSchedule,
    RefreshRun,
    Source,
)


@admin.register(Source)
class SourceAdmin(ModelAdmin):
    list_display = ("name", "slug", "domain", "is_active", "last_checked_at", "consecutive_errors")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "domain")
    prepopulated_fields = {"slug": ("name",)}


class ArticleTopicInline(TabularInline):
    model = ArticleTopic
    extra = 0


class EventArticleInline(TabularInline):
    model = EventArticle
    extra = 0
    readonly_fields = ("article", "added_at")
    can_delete = False


@admin.register(Article)
class ArticleAdmin(ModelAdmin):
    list_display = (
        "title", "source", "primary_category", "ai_suggested_category",
        "ai_confidence", "published_at", "processing_status",
    )
    list_filter = (
        "source", "primary_category", "ai_suggested_category",
        "processing_status", "duplicate_of",
    )
    search_fields = ("title", "first_paragraph", "second_paragraph", "canonical_url")
    readonly_fields = (
        "collected_at", "content_fingerprint", "duplicate_score", "image_url",
        "ai_suggested_category", "ai_confidence", "ai_reason",
        "ai_model", "ai_classified_at",
    )
    inlines = (ArticleTopicInline,)


@admin.register(ArticleTopic)
class ArticleTopicAdmin(ModelAdmin):
    list_display = ("article", "topic", "score", "is_manual")
    list_filter = ("topic__category", "topic", "is_manual")


@admin.register(AIUsage)
class AIUsageAdmin(ModelAdmin):
    list_display = (
        "created_at", "usage_type", "model", "article", "event", "input_tokens", "output_tokens",
        "total_tokens", "total_cost_gbp", "cost_type", "display_refresh_run",
    )
    list_filter = ("usage_type", "model", "is_estimated", "created_at")
    search_fields = ("article__title", "event__title", "model")
    readonly_fields = (
        "article", "event", "refresh_run", "usage_type", "model", "input_tokens", "cached_input_tokens",
        "output_tokens", "total_tokens", "input_cost_usd", "output_cost_usd",
        "total_cost_usd", "usd_to_gbp_rate", "total_cost_gbp", "is_estimated",
        "created_at",
    )
    date_hierarchy = "created_at"

    @display(description="Tip", label={"Exact": "success", "Estimat": "warning"})
    def cost_type(self, obj):
        return "Estimat" if obj.is_estimated else "Exact"

    @display(description="Rulare", ordering="refresh_run")
    def display_refresh_run(self, obj):
        if not obj.refresh_run_id:
            return "-"
        url = reverse("admin:news_refreshrun_change", args=(obj.refresh_run_id,))
        return format_html(
            '<a class="nf-refresh-run-link" href="{}">{}</a>',
            url,
            str(obj.refresh_run),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EventAIUsage)
class EventAIUsageAdmin(AIUsageAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(event__isnull=False)


@admin.register(RefreshRun)
class RefreshRunAdmin(ModelAdmin):
    change_form_template = "admin/news/refreshrun/change_form.html"
    list_display = (
        "started_at", "trigger", "display_status", "requested_by", "sources_succeeded",
        "sources_failed", "articles_collected", "ai_calls", "input_tokens",
        "output_tokens", "classification_cost_gbp", "event_cost_gbp", "cost_gbp",
    )
    list_filter = ("trigger", "status", "started_at")
    search_fields = ("requested_by__email", "ip_address", "note")
    readonly_fields = (
        "requested_by", "ip_address", "trigger", "status", "started_at", "finished_at",
        "sources_attempted", "sources_succeeded", "sources_failed",
        "articles_collected", "ai_calls", "input_tokens", "output_tokens",
        "classification_cost_gbp", "event_cost_gbp", "cost_usd", "cost_gbp",
        "events_created", "events_updated", "events_budget_blocked", "note",
    )
    date_hierarchy = "started_at"

    @display(
        description="Status",
        label={
            RefreshRun.Status.COMPLETED: "success",
            RefreshRun.Status.PARTIAL: "warning",
            RefreshRun.Status.SKIPPED: "info",
            RefreshRun.Status.FAILED: "danger",
            RefreshRun.Status.RUNNING: "primary",
        },
    )
    def display_status(self, obj):
        return obj.status

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        run = self.get_object(request, object_id)
        context = dict(extra_context or {})
        if run:
            end = run.finished_at or timezone.now()
            duration_seconds = max(0, int((end - run.started_at).total_seconds()))
            articles = Article.objects.filter(
                collected_at__gte=run.started_at,
                collected_at__lte=end,
            )
            processed_articles = articles.filter(
                processing_status=Article.ProcessingStatus.PROCESSED
            )
            failed_articles = list(
                articles.filter(processing_status=Article.ProcessingStatus.FAILED)
                .select_related("source")
                .order_by("source__name", "title")
            )
            duplicate_count = processed_articles.filter(
                duplicate_of__isnull=False
            ).count()
            eligible_count = processed_articles.filter(
                duplicate_of__isnull=True
            ).count()
            usage_labels = dict(AIUsage.UsageType.choices)
            usage_rows = list(
                run.ai_usage.values("usage_type", "model")
                .annotate(
                    calls=Count("id"),
                    input_tokens=Sum("input_tokens"),
                    output_tokens=Sum("output_tokens"),
                    cost_gbp=Sum("total_cost_gbp"),
                )
                .order_by("usage_type", "model")
            )
            max_usage_cost = max(
                (float(row["cost_gbp"] or 0) for row in usage_rows),
                default=0,
            )
            for row in usage_rows:
                row["label"] = usage_labels.get(row["usage_type"], row["usage_type"])
                row["cost_percent"] = round(
                    (float(row["cost_gbp"] or 0) / max_usage_cost * 100)
                    if max_usage_cost
                    else 0,
                    1,
                )
            touched_events = Event.objects.filter(
                ai_usage__refresh_run=run
            ).distinct()
            created_events = list(
                touched_events.filter(
                    first_generated_at__gte=run.started_at,
                    first_generated_at__lte=end,
                ).order_by("first_generated_at")
            )
            updated_events = list(
                touched_events.filter(
                    ai_usage__refresh_run=run,
                    ai_usage__usage_type=AIUsage.UsageType.EVENT_UPDATE,
                    first_generated_at__lt=run.started_at,
                ).distinct().order_by("last_generated_at")
            )
            source_success_percent = round(
                run.sources_succeeded / run.sources_attempted * 100
                if run.sources_attempted
                else 0,
                1,
            )
            context["refresh_report"] = {
                "duration_seconds": duration_seconds,
                "duration_minutes": duration_seconds // 60,
                "duration_remainder": duration_seconds % 60,
                "processed_count": processed_articles.count(),
                "failed_articles": failed_articles,
                "failed_article_count": len(failed_articles),
                "duplicate_count": duplicate_count,
                "eligible_count": eligible_count,
                "source_success_percent": source_success_percent,
                "usage_rows": usage_rows,
                "created_events": created_events,
                "updated_events": updated_events,
            }
        return super().change_view(request, object_id, form_url, context)


@admin.register(Event)
class EventAdmin(ModelAdmin):
    list_display = (
        "title",
        "display_status",
        "generated_source_count",
        "generation_count",
        "last_article_at",
        "last_generated_at",
        "total_cost_gbp",
    )
    list_filter = ("status", "last_article_at", "last_generated_at")
    search_fields = ("title", "summary", "articles__title")
    readonly_fields = (
        "slug",
        "first_seen_at",
        "first_generated_at",
        "last_article_at",
        "last_generated_at",
        "next_generation_at",
        "generated_source_count",
        "generation_count",
        "initial_cost_gbp",
        "update_cost_gbp",
        "total_cost_gbp",
    )
    inlines = (EventArticleInline,)
    date_hierarchy = "last_article_at"

    @display(
        description="Status",
        label={
            Event.Status.CANDIDATE: "info",
            Event.Status.PENDING: "warning",
            Event.Status.GENERATED: "primary",
            Event.Status.INDEXABLE: "success",
            Event.Status.STABLE: "success",
            Event.Status.BUDGET_BLOCKED: "warning",
            Event.Status.FAILED: "danger",
        },
    )
    def display_status(self, obj):
        return obj.status


@admin.register(EventBudget)
class EventBudgetAdmin(ModelAdmin):
    fieldsets = (
        ("Generare", {"fields": ("ai_enabled",)}),
        (
            "Limite numerice",
            {"fields": ("max_new_events_per_day", "max_new_events_per_month")},
        ),
        (
            "Limite cost GBP",
            {
                "fields": (
                    "max_cost_gbp_per_day",
                    "max_cost_gbp_per_month",
                    "max_cost_gbp_per_event",
                )
            },
        ),
        (
            "Praguri surse",
            {
                "fields": (
                    "minimum_sources_for_creation",
                    "minimum_sources_for_indexing",
                )
            },
        ),
        ("Stare internă", {"fields": ("reserved_cost_gbp", "updated_at")}),
    )
    readonly_fields = ("reserved_cost_gbp", "updated_at")

    def has_add_permission(self, request):
        return not EventBudget.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AutomaticUpdateSchedule)
class AutomaticUpdateScheduleAdmin(ModelAdmin):
    fieldsets = (
        ("Stare", {"fields": ("enabled",)}),
        (
            "Program zilnic",
            {
                "fields": (
                    "timezone_name",
                    "start_hour",
                    "end_hour",
                    "interval_hours",
                ),
                "description": (
                    "Configurația recomandată execută 14 rulări pe zi, din oră în "
                    "oră, între 08:00 și 21:00 inclusiv. Cronul sistemului trebuie "
                    "să apeleze comanda în fiecare oră."
                ),
            },
        ),
        ("Stare internă", {"fields": ("updated_at",)}),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not AutomaticUpdateSchedule.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
