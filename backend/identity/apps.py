from __future__ import annotations

from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "identity"
    label = "core_identity"
    verbose_name = "Core Identity"
