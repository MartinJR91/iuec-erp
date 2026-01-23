from __future__ import annotations

from typing import Iterable, Optional

from django.http import HttpRequest
from rest_framework.permissions import BasePermission, SAFE_METHODS


class ActiveRolePermission(BasePermission):
    """Permission basée sur le rôle actif injecté par middleware."""

    allowed_roles: Optional[Iterable[str]] = None

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        role_active = getattr(request, "role_active", None)
        if not role_active:
            return False
        if self.allowed_roles is None:
            return True
        return role_active in set(self.allowed_roles)


class CoreIdentityPermission(ActiveRolePermission):
    """Lecture pour tout rôle actif, écriture réservée à ADMIN_SI."""

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        role_active = getattr(request, "role_active", None)
        if not role_active:
            return False
        if request.method in SAFE_METHODS:
            return True
        return role_active == "ADMIN_SI"


class GradePermission(ActiveRolePermission):
    """Saisie des notes réservée à USER_TEACHER + scope check basique."""

    allowed_roles = ("USER_TEACHER",)

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        # Scope check simple via header X-Teacher-Scope (liste UE séparées par virgule).
        scope_header = request.headers.get("X-Teacher-Scope", "")
        if not scope_header:
            return False
        requested_ue = request.data.get("ue_code") if hasattr(request, "data") else None
        if not requested_ue:
            return True
        allowed = {item.strip().upper() for item in scope_header.split(",") if item.strip()}
        return str(requested_ue).upper() in allowed


class SoDPermission(BasePermission):
    """Bloque certaines actions quand l'acteur est son propre bénéficiaire."""

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        role_active = getattr(request, "role_active", None)
        if role_active != "MANAGER_RH_PAY":
            return True
        if request.method in SAFE_METHODS:
            return True
        identity_uuid = request.data.get("identity_uuid") if hasattr(request, "data") else None
        beneficiary_uuid = request.data.get("beneficiary_uuid") if hasattr(request, "data") else None
        if identity_uuid and beneficiary_uuid:
            return str(identity_uuid) != str(beneficiary_uuid)
        return True


class AdminSIPermission(ActiveRolePermission):
    allowed_roles = ("ADMIN_SI",)


class OperatorFinancePermission(ActiveRolePermission):
    allowed_roles = ("OPERATOR_FINANCE",)
