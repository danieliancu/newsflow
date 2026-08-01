from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Category, KeywordRule, Topic


class TopicInline(TabularInline):
    model = Topic
    extra = 0


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ("name", "slug", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description", "seo_title", "seo_description")
    inlines = (TopicInline,)


class KeywordRuleInline(TabularInline):
    model = KeywordRule
    extra = 1


@admin.register(Topic)
class TopicAdmin(ModelAdmin):
    list_display = ("name", "category", "is_active")
    list_filter = ("category", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description", "seo_title", "seo_description")
    inlines = (KeywordRuleInline,)


@admin.register(KeywordRule)
class KeywordRuleAdmin(ModelAdmin):
    list_display = ("phrase", "topic", "is_active")
    list_filter = ("topic__category", "topic", "is_active")
    search_fields = ("phrase",)
