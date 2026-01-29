from __future__ import annotations

from typing import Iterable, Optional

from django.http import HttpRequest
from rest_framework.permissions import BasePermission, SAFE_METHODS


class ActiveRolePermission(BasePermission):
    """Permission basée sur le rôle actif injecté par middleware."""

    allowed_roles: Optional[Iterable[str]] = None

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        if request.method == "OPTIONS":
            return True
        role_active = getattr(request, "role_active", None)
        if not role_active:
            return False
        if self.allowed_roles is None:
            return True
        return role_active in set(self.allowed_roles)


class CoreIdentityPermission(ActiveRolePermission):
    """Lecture pour tout rôle actif, écriture réservée à ADMIN_SI."""

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        if request.method == "OPTIONS":
            return True
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
        if request.method == "OPTIONS":
            return True
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


class FacultyPermission(ActiveRolePermission):
    """CRUD facultés: lecture pour RECTEUR/ADMIN_SI/VALIDATOR_ACAD, écriture ADMIN_SI/VALIDATOR_ACAD."""

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        if request.method == "OPTIONS":
            return True
        role_active = getattr(request, "role_active", None)
        if not role_active:
            return False
        if request.method in SAFE_METHODS:
            return role_active in {"RECTEUR", "ADMIN_SI", "VALIDATOR_ACAD", "DOYEN"}
        return role_active in {"ADMIN_SI", "VALIDATOR_ACAD", "DOYEN"}


class ProgramPermission(ActiveRolePermission):
    """CRUD programmes: lecture globale RECTEUR/ADMIN_SI, écriture ADMIN_SI/VALIDATOR_ACAD/DOYEN."""

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        if request.method == "OPTIONS":
            return True
        role_active = getattr(request, "role_active", None)
        if not role_active:
            return False
        if request.method in SAFE_METHODS:
            return role_active in {"RECTEUR", "ADMIN_SI", "VALIDATOR_ACAD", "DOYEN"}
        return role_active in {"ADMIN_SI", "VALIDATOR_ACAD", "DOYEN"}


class StudentPermission(ActiveRolePermission):
    """
    Permission pour la gestion des étudiants :
    - RECTEUR / VIEWER_STRATEGIC : accès total
    - DOYEN / VALIDATOR_ACAD : filter queryset par faculté du rôle actif
    - OPERATOR_SCOLA / OPERATOR_FINANCE : accès total (liste + actions)
    - USER_STUDENT : seulement son propre profil (obj == request.user.student_profile)
    - SAFE_METHODS → lecture, sinon check rôle
    """

    def has_permission(self, request: HttpRequest, view) -> bool:  # type: ignore[override]
        if request.method == "OPTIONS":
            return True
        role_active = getattr(request, "role_active", None)
        if not role_active:
            return False

        # SAFE_METHODS → lecture autorisée pour les rôles suivants
        if request.method in SAFE_METHODS:
            return role_active in {
                "RECTEUR",
                "VIEWER_STRATEGIC",
                "ADMIN_SI",
                "DOYEN",
                "VALIDATOR_ACAD",
                "USER_STUDENT",
                "SCOLARITE",
                "OPERATOR_FINANCE",
            }

        # Écriture réservée à certains rôles
        return role_active in {
            "RECTEUR",
            "ADMIN_SI",
            "SCOLARITE",
            "OPERATOR_FINANCE",
        }

    def has_object_permission(
        self, request: HttpRequest, view, obj: StudentProfile
    ) -> bool:  # type: ignore[override]
        """Vérifie l'accès à un objet spécifique."""
        role_active = getattr(request, "role_active", None)
        if not role_active:
            return False

        # RECTEUR et VIEWER_STRATEGIC ont accès global
        if role_active in {"RECTEUR", "VIEWER_STRATEGIC", "ADMIN_SI"}:
            return True

        # USER_STUDENT peut voir uniquement son propre profil
        if role_active == "USER_STUDENT":
            identity = _get_identity_from_request(request)
            if identity and obj.identity_id == identity.id:
                return request.method in SAFE_METHODS
            return False

        # DOYEN / VALIDATOR_ACAD peuvent voir les étudiants de leur faculté
        if role_active in {"DOYEN", "VALIDATOR_ACAD"}:
            identity = _get_identity_from_request(request)
            if not identity:
                return False
            if obj.current_program and obj.current_program.faculty:
                # Vérifie si l'identité est doyen de la faculté
                return obj.current_program.faculty.doyen_uuid_id == identity.id
            return False

        # SCOLARITE et OPERATOR_FINANCE ont accès total
        if role_active in {"SCOLARITE", "OPERATOR_FINANCE"}:
            return True

        return False


# Alias pour compatibilité
StudentProfilePermission = StudentPermission


def _get_identity_from_request(request: HttpRequest):
    """Récupère l'identité depuis la requête."""
    from identity.models import CoreIdentity

    email = getattr(request.user, "email", None)
    if not email:
        return None
    return CoreIdentity.objects.filter(email__iexact=email, is_active=True).first()