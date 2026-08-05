from django.core.exceptions import ValidationError
from django.db import models
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from django.utils.text import slugify


class Source(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    domain = models.CharField(max_length=255, unique=True)
    feed_url = models.URLField(unique=True)
    description = models.TextField(blank=True)
    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=320, blank=True)
    is_active = models.BooleanField(default=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    consecutive_errors = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "sursa"
            candidate = base
            suffix = 2
            while Source.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                candidate = f"{base}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class Article(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "În așteptare"
        PROCESSED = "processed", "Procesat"
        FAILED = "failed", "Eșuat"

    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="articles")
    canonical_url = models.URLField(max_length=1000, unique=True)
    title = models.CharField(max_length=500)
    lead = models.TextField(blank=True)
    first_paragraph = models.TextField(blank=True)
    second_paragraph = models.TextField(blank=True)
    author = models.CharField(max_length=255, blank=True)
    image_url = models.URLField(max_length=1000, blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    collected_at = models.DateTimeField(auto_now_add=True, db_index=True)
    language = models.CharField(max_length=10, default="ro")
    source_sections = models.JSONField(default=list, blank=True)
    content_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    processing_status = models.CharField(
        max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING, db_index=True
    )
    processing_attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    primary_category = models.ForeignKey(
        "taxonomy.Category", on_delete=models.SET_NULL, null=True, blank=True, related_name="articles"
    )
    ai_suggested_category = models.ForeignKey(
        "taxonomy.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_suggested_articles",
    )
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_reason = models.CharField(max_length=300, blank=True)
    ai_model = models.CharField(max_length=100, blank=True)
    ai_classified_at = models.DateTimeField(null=True, blank=True)
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicate_articles",
        help_text="Articolul reprezentativ pentru acelasi eveniment.",
    )
    duplicate_score = models.FloatField(default=0)

    class Meta:
        ordering = ("-published_at", "-collected_at")

    def __str__(self):
        return self.title


class Event(models.Model):
    class Status(models.TextChoices):
        CANDIDATE = "candidate", "Candidat"
        PENDING = "pending", "În așteptare"
        GENERATED = "generated", "Generat"
        INDEXABLE = "indexable", "Indexabil"
        STABLE = "stable", "Stabil"
        BUDGET_BLOCKED = "budget_blocked", "Blocat de buget"
        FAILED = "failed", "Eșuat"

    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=220, blank=True, unique=True, editable=False)
    status = models.CharField(
        max_length=30, choices=Status.choices, default=Status.CANDIDATE, db_index=True
    )
    articles = models.ManyToManyField(
        Article, through="EventArticle", related_name="events"
    )
    summary = models.TextField(blank=True)
    differences = models.JSONField(default=list, blank=True)
    timeline = models.JSONField(default=list, blank=True)
    source_snapshot = models.JSONField(default=list, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_article_at = models.DateTimeField(null=True, blank=True, db_index=True)
    first_generated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_generated_at = models.DateTimeField(null=True, blank=True)
    next_generation_at = models.DateTimeField(null=True, blank=True)
    generated_source_count = models.PositiveIntegerField(default=0)
    generation_count = models.PositiveIntegerField(default=0)
    initial_cost_gbp = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    update_cost_gbp = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    total_cost_gbp = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ("-last_article_at", "-first_seen_at")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        persisted_slug = ""
        if self.pk:
            persisted_slug = (
                Event.objects.filter(pk=self.pk).values_list("slug", flat=True).first()
                or ""
            )
        if persisted_slug:
            self.slug = persisted_slug
        elif not self.slug:
            base_slug = (slugify(self.title) or "eveniment")[:220]
            candidate = base_slug
            suffix = 2
            while Event.objects.exclude(pk=self.pk).filter(slug=candidate).exists():
                suffix_text = f"-{suffix}"
                candidate = f"{base_slug[:220 - len(suffix_text)]}{suffix_text}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    @property
    def public_path(self):
        return f"/eveniment/{self.slug}/"

    @property
    def public_updated_at(self):
        """Latest public activity, including a newly attached report."""
        timestamps = [
            timestamp
            for timestamp in (self.last_generated_at, self.last_article_at)
            if timestamp is not None
        ]
        return max(timestamps, default=None)

    @property
    def is_publicly_updated(self):
        return bool(
            self.first_generated_at
            and self.public_updated_at
            and self.public_updated_at > self.first_generated_at
        )


class EventArticle(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="event_articles")
    article = models.OneToOneField(
        Article, on_delete=models.CASCADE, related_name="event_membership"
    )
    added_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("added_at",)


class EventBudget(models.Model):
    ai_enabled = models.BooleanField(default=True)
    max_new_events_per_day = models.PositiveIntegerField(default=100)
    max_new_events_per_month = models.PositiveIntegerField(default=2000)
    max_cost_gbp_per_day = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.75")
    )
    max_cost_gbp_per_month = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("20.00")
    )
    max_cost_gbp_per_event = models.DecimalField(
        max_digits=10, decimal_places=3, default=Decimal("0.025")
    )
    minimum_sources_for_creation = models.PositiveSmallIntegerField(default=2)
    minimum_sources_for_indexing = models.PositiveSmallIntegerField(default=2)
    reserved_cost_gbp = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Buget evenimente"
        verbose_name_plural = "Buget evenimente"

    def __str__(self):
        return "Buget evenimente"

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.minimum_sources_for_indexing < self.minimum_sources_for_creation:
            raise ValidationError(
                {
                    "minimum_sources_for_indexing": (
                        "Pragul de indexare nu poate fi mai mic decât pragul de creare."
                    )
                }
            )

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AutomaticUpdateLock(models.Model):
    name = models.CharField(max_length=50, primary_key=True, default="automatic_news_update")
    acquired_at = models.DateTimeField(null=True, blank=True)
    owner = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.name


class AutomaticUpdateSchedule(models.Model):
    enabled = models.BooleanField(default=True, verbose_name="Rulare activă")
    timezone_name = models.CharField(
        max_length=64, default="Europe/Bucharest", verbose_name="Fus orar"
    )
    start_hour = models.PositiveSmallIntegerField(
        default=8, verbose_name="Prima rulare (ora)"
    )
    end_hour = models.PositiveSmallIntegerField(
        default=21, verbose_name="Ultima rulare (ora)"
    )
    interval_hours = models.PositiveSmallIntegerField(
        default=1, verbose_name="Interval între rulări (ore)"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Program rulare automată"
        verbose_name_plural = "Program rulare automată"

    def __str__(self):
        return f"{self.start_hour:02d}:00–{self.end_hour:02d}:00 · la {self.interval_hours}h"

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        errors = {}
        if self.start_hour > 23:
            errors["start_hour"] = "Ora trebuie să fie între 0 și 23."
        if self.end_hour > 23:
            errors["end_hour"] = "Ora trebuie să fie între 0 și 23."
        if self.start_hour > self.end_hour:
            errors["end_hour"] = "Ultima rulare trebuie să fie după prima rulare."
        if self.interval_hours < 1:
            errors["interval_hours"] = "Intervalul trebuie să fie de cel puțin o oră."
        try:
            ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:
            errors["timezone_name"] = "Fusul orar nu este valid."
        if errors:
            raise ValidationError(errors)

    @property
    def runs_per_day(self):
        return ((self.end_hour - self.start_hour) // self.interval_hours) + 1

    def is_due(self, moment=None):
        if not self.enabled:
            return False
        local_moment = (moment or timezone.now()).astimezone(
            ZoneInfo(self.timezone_name)
        )
        return (
            self.start_hour <= local_moment.hour <= self.end_hour
            and (local_moment.hour - self.start_hour) % self.interval_hours == 0
        )

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ArticleTopic(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="topic_matches")
    topic = models.ForeignKey("taxonomy.Topic", on_delete=models.CASCADE, related_name="article_matches")
    score = models.PositiveIntegerField(default=0)
    matched_keywords = models.JSONField(default=list, blank=True)
    reasons = models.JSONField(default=list, blank=True)
    is_manual = models.BooleanField(default=False)

    class Meta:
        ordering = ("-score",)
        constraints = [
            models.UniqueConstraint(fields=["article", "topic"], name="unique_article_topic_match")
        ]


class RefreshRun(models.Model):
    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        AUTOMATIC = "automatic", "Automat"

    class Status(models.TextChoices):
        RUNNING = "running", "În desfășurare"
        COMPLETED = "completed", "Finalizat"
        PARTIAL = "partial", "Finalizat parțial"
        SKIPPED = "skipped", "Omis"
        FAILED = "failed", "Eșuat"

    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="refresh_runs"
    )
    trigger = models.CharField(
        max_length=20, choices=Trigger.choices, default=Trigger.MANUAL, db_index=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    sources_attempted = models.PositiveIntegerField(default=0)
    sources_succeeded = models.PositiveIntegerField(default=0)
    sources_failed = models.PositiveIntegerField(default=0)
    articles_collected = models.PositiveIntegerField(default=0)
    ai_calls = models.PositiveIntegerField(default=0)
    input_tokens = models.PositiveBigIntegerField(default=0)
    output_tokens = models.PositiveBigIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    cost_gbp = models.DecimalField(max_digits=12, decimal_places=6, default=0)
    classification_cost_gbp = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    event_cost_gbp = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    events_created = models.PositiveIntegerField(default=0)
    events_updated = models.PositiveIntegerField(default=0)
    events_budget_blocked = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ("-started_at",)

    def __str__(self):
        started = timezone.localtime(self.started_at).strftime("%d.%m.%Y %H:%M")
        return (
            f"Rularea #{self.pk} · {self.get_trigger_display()} · "
            f"{started} · {self.get_status_display()}"
        )


class AIUsage(models.Model):
    class UsageType(models.TextChoices):
        ARTICLE_CLASSIFICATION = "article_classification", "Clasificare articol"
        EVENT_CLAIM_EXTRACTION = "event_claim_extraction", "Extragere afirmații"
        EVENT_MERGE_CHECK = "event_merge_check", "Verificare unire evenimente"
        EVENT_UPDATE_CHECK = "event_update_check", "Verificare noutate eveniment"
        EVENT_SUMMARY = "event_summary", "Sinteză eveniment"
        EVENT_UPDATE = "event_update", "Actualizare eveniment"

    article = models.ForeignKey(
        Article, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_usage"
    )
    refresh_run = models.ForeignKey(
        RefreshRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_usage"
    )
    event = models.ForeignKey(
        Event, on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_usage"
    )
    usage_type = models.CharField(
        max_length=40,
        choices=UsageType.choices,
        default=UsageType.ARTICLE_CLASSIFICATION,
        db_index=True,
    )
    model = models.CharField(max_length=100, db_index=True)
    input_tokens = models.PositiveIntegerField(default=0)
    cached_input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    input_cost_usd = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    output_cost_usd = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    total_cost_usd = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    usd_to_gbp_rate = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    total_cost_gbp = models.DecimalField(max_digits=12, decimal_places=8, default=0)
    is_estimated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)


class EventAIUsage(AIUsage):
    class Meta:
        proxy = True
        verbose_name = "Consum AI eveniment"
        verbose_name_plural = "Consum AI evenimente"
