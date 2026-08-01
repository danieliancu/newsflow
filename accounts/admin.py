from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin

from .models import CategoryPreference, FollowedTerm, SourcePreference, TopicPreference, User


@admin.register(User)
class NewsflowUserAdmin(UserAdmin, ModelAdmin):
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_active", "created_at")
    search_fields = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Drepturi", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Date", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )


admin.site.register(CategoryPreference, ModelAdmin)
admin.site.register(TopicPreference, ModelAdmin)
admin.site.register(SourcePreference, ModelAdmin)
admin.site.register(FollowedTerm, ModelAdmin)
