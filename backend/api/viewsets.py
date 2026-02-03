from __future__ import annotations

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets

from apps.academic.models import Faculty, GradeEntry, Program, StudentProfile
from apps.finance.models import Invoice
from identity.models import CoreIdentity, IdentityRoleLink

from .permissions import (
    AdminSIPermission,
    CoreIdentityPermission,
    FacultyPermission,
    GradePermission,
    OperatorFinancePermission,
    ProgramPermission,
    SoDPermission,
    StudentProfilePermission,
)
from .serializers import (
    CoreIdentitySerializer,
    FacultySerializer,
    GradeEntrySerializer,
    IdentityRoleLinkSerializer,
    InvoiceSerializer,
    ProgramSerializer,
    StudentProfileSerializer,
)


class CoreIdentityViewSet(viewsets.ModelViewSet):
    queryset = CoreIdentity.objects.all()
    serializer_class = CoreIdentitySerializer
    permission_classes = (CoreIdentityPermission, SoDPermission)


class IdentityRoleLinkViewSet(viewsets.ModelViewSet):
    queryset = IdentityRoleLink.objects.all()
    serializer_class = IdentityRoleLinkSerializer
    permission_classes = (AdminSIPermission, SoDPermission)


class GradeEntryViewSet(viewsets.ModelViewSet):
    queryset = GradeEntry.objects.all()
    serializer_class = GradeEntrySerializer
    permission_classes = (GradePermission, SoDPermission)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = (OperatorFinancePermission, SoDPermission)


class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = (FacultyPermission, SoDPermission)

    def get_queryset(self):  # type: ignore[override]
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)
        if role_active in {"RECTEUR", "ADMIN_SI"}:
            return queryset

        if role_active in {"VALIDATOR_ACAD", "DOYEN"}:
            identity = _get_identity(self.request)
            if not identity:
                return queryset.none()
            scope_code = _get_scope_code(identity, role_active)
            if scope_code:
                return queryset.filter(
                    Q(doyen_uuid=identity) | Q(code__iexact=scope_code)
                )
            return queryset.filter(doyen_uuid=identity)

        return queryset.none()

    def perform_create(self, serializer):  # type: ignore[override]
        role_active = getattr(self.request, "role_active", None)
        if role_active in {"VALIDATOR_ACAD", "DOYEN"}:
            identity = _get_identity(self.request)
            if identity:
                serializer.save(doyen_uuid=identity)
                return
        serializer.save()

    def perform_update(self, serializer):  # type: ignore[override]
        role_active = getattr(self.request, "role_active", None)
        if role_active in {"VALIDATOR_ACAD", "DOYEN"}:
            identity = _get_identity(self.request)
            if identity:
                serializer.save(doyen_uuid=identity)
                return
        serializer.save()


class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.select_related("faculty")
    serializer_class = ProgramSerializer
    permission_classes = (ProgramPermission, SoDPermission)

    def get_queryset(self):  # type: ignore[override]
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)
        if role_active in {"RECTEUR", "ADMIN_SI", "OPERATOR_SCOLA", "SCOLARITE"}:
            return queryset

        if role_active in {"VALIDATOR_ACAD", "DOYEN"}:
            identity = _get_identity(self.request)
            if not identity:
                return queryset.none()
            scope_code = _get_scope_code(identity, role_active)
            if scope_code:
                return queryset.filter(
                    Q(faculty__doyen_uuid=identity) | Q(faculty__code__iexact=scope_code)
                )
            return queryset.filter(faculty__doyen_uuid=identity)

        return queryset.none()

    def perform_create(self, serializer):  # type: ignore[override]
        role_active = getattr(self.request, "role_active", None)
        if role_active in {"VALIDATOR_ACAD", "DOYEN"}:
            faculty = serializer.validated_data.get("faculty")
            if faculty is None:
                raise PermissionDenied("Faculté requise.")
            if not _is_faculty_allowed(self.request, faculty):
                raise PermissionDenied("Faculté non autorisée.")
        serializer.save()

    def perform_update(self, serializer):  # type: ignore[override]
        role_active = getattr(self.request, "role_active", None)
        if role_active in {"VALIDATOR_ACAD", "DOYEN"}:
            faculty = serializer.validated_data.get("faculty", serializer.instance.faculty)
            if not _is_faculty_allowed(self.request, faculty):
                raise PermissionDenied("Faculté non autorisée.")
        serializer.save()


def _get_identity(request) -> CoreIdentity | None:
    email = getattr(request.user, "email", None)
    if not email:
        return None
    return CoreIdentity.objects.filter(email__iexact=email, is_active=True).first()


def _get_scope_code(identity: CoreIdentity, role_code: str) -> str | None:
    metadata = identity.metadata or {}
    scope_by_role = metadata.get("scope_by_role", {})
    scope = None
    if isinstance(scope_by_role, dict):
        scope = scope_by_role.get(role_code)
    return str(scope) if scope else None


def _is_faculty_allowed(request, faculty: Faculty) -> bool:
    identity = _get_identity(request)
    if not identity:
        return False
    scope_code = _get_scope_code(identity, getattr(request, "role_active", ""))
    if scope_code and faculty.code.upper() == scope_code.upper():
        return True
    return faculty.doyen_uuid_id == identity.id


class StudentProfileViewSet(viewsets.ModelViewSet):
    """ViewSet pour STUDENT_PROFILE avec permissions RBAC."""

    queryset = StudentProfile.objects.select_related("identity", "current_program", "current_program__faculty")
    serializer_class = StudentProfileSerializer
    permission_classes = (StudentProfilePermission, SoDPermission)

    def get_queryset(self):  # type: ignore[override]
        """Filtre le queryset selon le rôle actif."""
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)

        # RECTEUR et ADMIN_SI voient tout
        if role_active in {"RECTEUR", "ADMIN_SI"}:
            return queryset

        # USER_STUDENT voit uniquement son propre profil
        if role_active == "USER_STUDENT":
            identity = _get_identity(self.request)
            if identity:
                return queryset.filter(identity=identity)
            return queryset.none()

        # DOYEN et VALIDATOR_ACAD voient les étudiants de leur faculté
        if role_active in {"DOYEN", "VALIDATOR_ACAD"}:
            identity = _get_identity(self.request)
            if not identity:
                return queryset.none()
            # Filtre par faculté où l'identité est doyen
            return queryset.filter(
                Q(current_program__faculty__doyen_uuid=identity)
                | Q(current_program__faculty__code__iexact=_get_scope_code(identity, role_active) or "")
            )

        # SCOLARITE et OPERATOR_FINANCE voient tout (pour leurs opérations)
        if role_active in {"SCOLARITE", "OPERATOR_FINANCE"}:
            return queryset

        return queryset.none()

    def perform_create(self, serializer):  # type: ignore[override]
        """Création réservée à SCOLARITE et ADMIN_SI."""
        role_active = getattr(self.request, "role_active", None)
        if role_active not in {"SCOLARITE", "ADMIN_SI"}:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Création réservée à SCOLARITE et ADMIN_SI.")
        serializer.save()

    def perform_update(self, serializer):  # type: ignore[override]
        """Mise à jour réservée à SCOLARITE et ADMIN_SI."""
        role_active = getattr(self.request, "role_active", None)
        if role_active not in {"SCOLARITE", "ADMIN_SI"}:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Mise à jour réservée à SCOLARITE et ADMIN_SI.")
        serializer.save()
