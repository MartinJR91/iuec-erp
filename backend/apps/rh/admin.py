from __future__ import annotations

from django.contrib import admin

from .models import Department


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "is_active")
    search_fields = ("code", "label")
