from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Interaction, Recommendation, SavedEvent


@admin.register(Recommendation)
class RecommendationAdmin(ModelAdmin):
    list_display = ("user", "article", "score", "generated_at")
    list_filter = ("generated_at",)
    search_fields = ("user__email", "article__title")
    readonly_fields = ("generated_at",)


@admin.register(Interaction)
class InteractionAdmin(ModelAdmin):
    list_display = ("user", "article", "kind", "created_at")
    list_filter = ("kind", "created_at")
    search_fields = ("user__email", "article__title")


@admin.register(SavedEvent)
class SavedEventAdmin(ModelAdmin):
    list_display = ("user", "event", "created_at")
    search_fields = ("user__email", "event__title")
    readonly_fields = ("created_at",)
