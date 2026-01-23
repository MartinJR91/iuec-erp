from __future__ import annotations

from django.contrib import admin

from .models import FeeCategory


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "is_active")
    search_fields = ("code", "label")
