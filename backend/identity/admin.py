from __future__ import annotations

import logging
from typing import Iterable, List, Optional, Tuple

from django.contrib import admin, messages
from django.db.models import QuerySet

from .models import CoreIdentity, IdentityRoleLink, RbacRoleDef

logger = logging.getLogger(__name__)


class ActiveRoleFilter(admin.SimpleListFilter):
    title = "rôle actif"
    parameter_name = "active_role"

    def lookups(
        self, request, model_admin
    ) -> List[Tuple[str, str]]:  # type: ignore[override]
        roles = RbacRoleDef.objects.filter(is_active=True).order_by("code")
        return [(role.code, role.label) for role in roles]

    def queryset(self, request, queryset: QuerySet[CoreIdentity]) -> QuerySet[CoreIdentity]:
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(role_links__role__code=value, role_links__is_active=True)


class IdentityRoleLinkInline(admin.TabularInline):
    model = IdentityRoleLink
    extra = 0
    autocomplete_fields = ("role",)
    readonly_fields = ("created_at",)


@admin.register(CoreIdentity)
class CoreIdentityAdmin(admin.ModelAdmin):
    list_display = ("email", "phone", "first_name", "last_name", "is_active")
    search_fields = ("email", "phone", "first_name", "last_name")
    list_filter = ("is_active", ActiveRoleFilter)
    inlines = (IdentityRoleLinkInline,)

    def audit_log_preview(self, obj: CoreIdentity) -> str:
        return "Audit logs disponibles via django-auditlog."

    audit_log_preview.short_description = "Audit logs"  # type: ignore[attr-defined]

    def get_readonly_fields(
        self, request, obj: Optional[CoreIdentity] = None
    ) -> Iterable[str]:
        fields = ["audit_log_preview"]
        model_fields = {field.name for field in self.model._meta.get_fields()}
        if "hash_password" in model_fields:
            fields.append("hash_password")
        return fields


@admin.register(IdentityRoleLink)
class IdentityRoleLinkAdmin(admin.ModelAdmin):
    list_display = ("identity", "role", "is_active", "starts_at", "ends_at")
    search_fields = ("identity__email", "role__code", "role__label")
    list_filter = ("is_active", "role")
    readonly_fields = ("created_at",)
    actions = ["activate_bris_de_glace"]

    def activate_bris_de_glace(
        self, request, queryset: QuerySet[IdentityRoleLink]
    ) -> None:
        count = queryset.count()
        logger.warning("BRIS_DE_GLACE activé sur %s liens de rôles", count)
        print(f"ALERTE BRIS_DE_GLACE: {count} lien(s) sélectionné(s)")
        self.message_user(
            request,
            f"Mode Bris de Glace activé pour {count} lien(s).",
            level=messages.WARNING,
        )

    activate_bris_de_glace.short_description = "Activer mode Bris de Glace"
