from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Interaction, Recommendation


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
