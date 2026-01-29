from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import QuerySet, Q

from identity.models import CoreIdentity

if TYPE_CHECKING:
    from django.http import HttpRequest


def _get_identity_from_request(request: "HttpRequest") -> CoreIdentity | None:
    """Récupère l'identité depuis la requête."""
    email = getattr(request.user, "email", None)
    if not email:
        return None
    return CoreIdentity.objects.filter(email__iexact=email, is_active=True).first()


def _get_scope_code(identity: CoreIdentity, role_code: str) -> str | None:
    """Récupère le code de scope depuis les métadonnées de l'identité."""
    metadata = identity.metadata or {}
    scope_by_role = metadata.get("scope_by_role", {})
    scope = None
    if isinstance(scope_by_role, dict):
        scope = scope_by_role.get(role_code)
    return str(scope) if scope else None


class ScopeFilterMixin:
    """Mixin pour filtrer les querysets selon le scope du rôle actif."""

    def filter_by_scope(
        self, queryset: QuerySet, faculty_field: str = "current_program__faculty"
    ) -> QuerySet:
        """
        Filtre le queryset selon le rôle actif et son scope.

        Args:
            queryset: Le queryset à filtrer
            faculty_field: Le chemin du champ faculté (par défaut: "current_program__faculty")

        Returns:
            QuerySet filtré selon le rôle actif
        """
        role_active = getattr(self.request, "role_active", None)
        if not role_active:
            return queryset.none()

        # RECTEUR et ADMIN_SI voient tout
        if role_active in {"RECTEUR", "ADMIN_SI"}:
            return queryset

        # USER_STUDENT voit uniquement son propre profil
        if role_active == "USER_STUDENT":
            identity = _get_identity_from_request(self.request)
            if identity:
                return queryset.filter(identity=identity)
            return queryset.none()

        # DOYEN et VALIDATOR_ACAD voient les étudiants de leur faculté
        if role_active in {"DOYEN", "VALIDATOR_ACAD"}:
            identity = _get_identity_from_request(self.request)
            if not identity:
                return queryset.none()
            scope_code = _get_scope_code(identity, role_active)
            # Filtre par faculté où l'identité est doyen ou par scope_code
            filters = Q(**{f"{faculty_field}__doyen_uuid": identity})
            if scope_code:
                filters |= Q(**{f"{faculty_field}__code__iexact": scope_code})
            return queryset.filter(filters)

        # SCOLARITE et OPERATOR_FINANCE voient tout (pour leurs opérations)
        if role_active in {"SCOLARITE", "OPERATOR_FINANCE"}:
            return queryset

        return queryset.none()
