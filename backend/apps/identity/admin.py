from __future__ import annotations

from django.contrib import admin

from .models import Identity


@admin.register(Identity)
class IdentityAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "is_active", "created_at")
    search_fields = ("email", "phone")
