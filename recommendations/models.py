from django.conf import settings
from django.db import models
from django.utils import timezone


class Recommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    article = models.ForeignKey("news.Article", on_delete=models.CASCADE, related_name="recommendations")
    score = models.FloatField(default=0, db_index=True)
    reasons = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-score", "-article__published_at")
        constraints = [
            models.UniqueConstraint(fields=["user", "article"], name="unique_user_article_recommendation")
        ]


class Interaction(models.Model):
    class Kind(models.TextChoices):
        SHOWN = "shown", "Afișat"
        OPENED = "opened", "Deschis"
        SAVED = "saved", "Salvat"
        HIDDEN = "hidden", "Ascuns"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interactions")
    article = models.ForeignKey("news.Article", on_delete=models.CASCADE, related_name="interactions")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "article", "kind"])]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "article", "kind"],
                name="unique_user_article_interaction_kind",
            )
        ]


class SavedEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_events",
    )
    event = models.ForeignKey(
        "news.Event",
        on_delete=models.CASCADE,
        related_name="saved_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"], name="unique_user_saved_event"
            )
        ]


class OpenedEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="opened_events",
    )
    event = models.ForeignKey(
        "news.Event",
        on_delete=models.CASCADE,
        related_name="opened_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"], name="unique_user_opened_event"
            )
        ]
