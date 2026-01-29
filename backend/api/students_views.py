from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.academic.models import AcademicYear, Program, RegistrationAdmin, StudentProfile
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, SysAuditLog

from .mixins import ScopeFilterMixin, _get_identity_from_request
from .permissions import SoDPermission, StudentPermission
from .serializers import RegistrationAdminSerializer, StudentProfileSerializer


class StudentsViewSet(ScopeFilterMixin, ModelViewSet):
    """
    ViewSet complet pour la gestion des étudiants avec permissions et logique métier.

    GET /api/students/ : Liste avec solde annoté, filtrée par rôle actif
    GET /api/students/<uuid>/ : Détail avec profil + inscriptions + statut finance
    POST /api/students/ : Inscription annuelle (vérifie finance_status)
    PUT /api/students/<uuid>/finance-status/ : Mise à jour statut finance (OPERATOR_FINANCE only)
    POST /api/students/<uuid>/validate-registration/ : Valider inscription (VALIDATOR_ACAD only)
    """

    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, StudentPermission, SoDPermission]

    def get_queryset(self):  # type: ignore[override]
        """
        Filtre le queryset selon le rôle actif et le scope.
        Annote le solde calculé via Subquery.
        """
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)

        if not role_active:
            return queryset.none()

        # Annotation du solde calculé via Subquery
        # Subquery pour calculer le total des factures par identité
        invoices_subquery = (
            Invoice.objects.filter(identity_uuid=OuterRef("identity_id"))
            .values("identity_uuid")
            .annotate(total=Sum("total_amount"))
            .values("total")[:1]
        )

        # Subquery pour calculer le total des paiements par identité
        payments_subquery = (
            Payment.objects.filter(invoice__identity_uuid=OuterRef("identity_id"))
            .values("invoice__identity_uuid")
            .annotate(total=Sum("amount"))
            .values("total")[:1]
        )

        queryset = queryset.select_related(
            "identity", "current_program", "current_program__faculty"
        ).prefetch_related("registrations_admin", "registrations_admin__pedagogical").annotate(
            total_invoices=Coalesce(
                Subquery(invoices_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            total_payments=Coalesce(
                Subquery(payments_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        ).annotate(
            calculated_balance=F("total_invoices") - F("total_payments")
        )

        # Utilise le mixin pour filtrer par scope
        queryset = self.filter_by_scope(queryset)

        # Filtre supplémentaire pour OPERATOR_FINANCE (seulement bloqués/moratoires)
        # Note: Ce filtre est appliqué uniquement pour la liste, pas pour le détail
        if role_active == "OPERATOR_FINANCE" and self.action == "list":
            queryset = queryset.filter(
                finance_status__in=["Bloqué", "Moratoire"]
            )

        return queryset

    def list(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """GET list : retourne la liste avec solde annoté."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """GET detail : profil + inscriptions + statut finance."""
        instance = self.get_object()
        # Utilise le solde annoté si disponible, sinon calcule
        balance = getattr(instance, "calculated_balance", None)
        if balance is None:
            balance = self._calculate_balance_for_identity(instance.identity_id)

        serializer = self.get_serializer(instance)
        registrations = RegistrationAdmin.objects.filter(student=instance).select_related(
            "academic_year"
        ).prefetch_related("pedagogical")
        registrations_serializer = RegistrationAdminSerializer(registrations, many=True)

        return Response(
            {
                "student": serializer.data,
                "registrations": registrations_serializer.data,
                "finance": {
                    "balance": float(balance),
                    "status": instance.finance_status,
                    "status_effective": self._get_effective_finance_status(
                        instance, balance
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )

    def create(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """
        POST inscription annuelle : vérifie finance_status avant création.

        Payload requis:
        - identity_uuid
        - matricule_permanent
        - date_entree
        - program_id
        - academic_year_id
        - level
        """
        role_active = getattr(request, "role_active", None)
        if role_active not in {"SCOLARITE", "ADMIN_SI", "RECTEUR"}:
            return Response(
                {"detail": "Création d'inscription réservée à SCOLARITE, ADMIN_SI ou RECTEUR."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = request.data
        identity_uuid = payload.get("identity_uuid")
        matricule_permanent = payload.get("matricule_permanent")
        date_entree = payload.get("date_entree")
        program_id = payload.get("program_id")
        academic_year_id = payload.get("academic_year_id")
        level = payload.get("level")
        finance_status = payload.get("finance_status", "OK")

        # Vérification des champs requis
        missing_fields = [
            field
            for field in (
                "identity_uuid",
                "matricule_permanent",
                "date_entree",
                "program_id",
                "academic_year_id",
                "level",
            )
            if not payload.get(field)
        ]
        if missing_fields:
            return Response(
                {"detail": f"Champs requis manquants: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Récupération de l'identité
        try:
            identity = CoreIdentity.objects.get(id=identity_uuid, is_active=True)
        except CoreIdentity.DoesNotExist:
            return Response(
                {"detail": "Identité introuvable."}, status=status.HTTP_404_NOT_FOUND
            )

        # Vérification du solde financier
        balance = self._calculate_balance_for_identity(identity.id)
        if balance > 0:
            return Response(
                {
                    "detail": "Inscription bloquée: solde négatif.",
                    "balance": float(balance),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérification du statut financier existant
        existing_profile = StudentProfile.objects.filter(identity=identity).first()
        if existing_profile:
            if existing_profile.finance_status == "Bloqué":
                return Response(
                    {
                        "detail": "Inscription impossible : statut financier 'Bloqué'.",
                        "student_id": str(existing_profile.id),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Récupération du programme
        try:
            program = Program.objects.get(id=program_id, is_active=True)
        except Program.DoesNotExist:
            return Response(
                {"detail": "Programme introuvable."}, status=status.HTTP_404_NOT_FOUND
            )

        # Récupération de l'année académique
        try:
            academic_year = AcademicYear.objects.get(id=academic_year_id)
        except AcademicYear.DoesNotExist:
            return Response(
                {"detail": "Année académique introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Création ou mise à jour du profil étudiant
        student_profile, created = StudentProfile.objects.get_or_create(
            identity=identity,
            defaults={
                "matricule_permanent": matricule_permanent,
                "date_entree": date_entree,
                "current_program": program,
                "finance_status": finance_status,
            },
        )
        if not created:
            student_profile.matricule_permanent = matricule_permanent
            student_profile.date_entree = date_entree
            student_profile.current_program = program
            if finance_status != "Bloqué":
                student_profile.finance_status = finance_status
            student_profile.save()

        # Création de l'inscription administrative
        try:
            registration = RegistrationAdmin.objects.create(
                student=student_profile,
                academic_year=academic_year,
                level=level,
                finance_status=student_profile.finance_status,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "detail": "Inscription créée avec succès.",
                "student_id": str(student_profile.id),
                "registration_id": str(registration.id),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["PUT", "PATCH"],
        url_path="finance-status",
    )
    def update_finance_status(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        PUT /api/students/<uuid>/finance-status/ : Mise à jour statut finance.

        Réservé à OPERATOR_FINANCE. Log audit avec rôle actif.
        """
        role_active = getattr(request, "role_active", None)
        if role_active != "OPERATOR_FINANCE":
            return Response(
                {"detail": "Accès réservé à OPERATOR_FINANCE."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student = self.get_object()
        new_status = request.data.get("finance_status")

        if not new_status:
            return Response(
                {"detail": "Champ 'finance_status' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_statuses = ["OK", "Bloqué", "Moratoire"]
        if new_status not in valid_statuses:
            return Response(
                {"detail": f"Statut invalide. Choix: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = student.finance_status
        student.finance_status = new_status
        student.save()

        # Log audit avec rôle actif
        actor_email = getattr(request.user, "email", "")
        SysAuditLog.objects.create(
            action="FINANCE_STATUS_UPDATED",
            entity_type="STUDENT_PROFILE",
            entity_id=student.id,
            actor_email=actor_email,
            active_role=role_active,
            payload={
                "student_id": str(student.id),
                "old_status": old_status,
                "new_status": new_status,
                "matricule": student.matricule_permanent,
            },
        )

        return Response(
            {
                "detail": "Statut financier mis à jour.",
                "student_id": str(student.id),
                "old_status": old_status,
                "new_status": new_status,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["POST"],
        url_path="validate-registration",
    )
    def validate_registration(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        POST /api/students/<uuid>/validate-registration/ : Valider inscription administrative.

        Réservé à VALIDATOR_ACAD. Valide la REGISTRATION_ADMIN pour l'année académique active.
        """
        role_active = getattr(request, "role_active", None)
        if role_active not in {"VALIDATOR_ACAD", "DOYEN", "RECTEUR", "ADMIN_SI"}:
            return Response(
                {"detail": "Accès réservé à VALIDATOR_ACAD, DOYEN, RECTEUR ou ADMIN_SI."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student = self.get_object()
        academic_year_id = request.data.get("academic_year_id")
        registration_id = request.data.get("registration_id")

        # Si registration_id est fourni, valider cette inscription spécifique
        if registration_id:
            try:
                registration = RegistrationAdmin.objects.get(
                    id=registration_id, student=student
                )
            except RegistrationAdmin.DoesNotExist:
                return Response(
                    {"detail": "Inscription introuvable."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        # Sinon, valider l'inscription pour l'année académique active
        elif academic_year_id:
            try:
                registration = RegistrationAdmin.objects.get(
                    student=student, academic_year_id=academic_year_id
                )
            except RegistrationAdmin.DoesNotExist:
                return Response(
                    {"detail": "Inscription introuvable pour cette année académique."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Prendre la dernière inscription
            registration = RegistrationAdmin.objects.filter(
                student=student
            ).order_by("-registration_date").first()
            if not registration:
                return Response(
                    {"detail": "Aucune inscription trouvée."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Vérification du scope (DOYEN/VALIDATOR_ACAD doivent valider leur faculté)
        if role_active in {"DOYEN", "VALIDATOR_ACAD"}:
            identity = _get_identity_from_request(request)
            if identity and student.current_program and student.current_program.faculty:
                if student.current_program.faculty.doyen_uuid_id != identity.id:
                    return Response(
                        {"detail": "Faculté non autorisée."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        # Validation : mettre à jour le finance_status à OK
        old_status = registration.finance_status
        registration.finance_status = "OK"
        registration.save()

        # Synchroniser avec le profil étudiant si nécessaire
        if student.finance_status == "Bloqué" and old_status == "Bloqué":
            student.finance_status = "OK"
            student.save()

        # Log audit
        actor_email = getattr(request.user, "email", "")
        SysAuditLog.objects.create(
            action="REGISTRATION_VALIDATED",
            entity_type="REGISTRATION_ADMIN",
            entity_id=registration.id,
            actor_email=actor_email,
            active_role=role_active,
            payload={
                "student_id": str(student.id),
                "registration_id": str(registration.id),
                "academic_year": registration.academic_year.code,
                "level": registration.level,
                "old_status": old_status,
                "new_status": "OK",
            },
        )

        return Response(
            {
                "detail": "Inscription validée.",
                "student_id": str(student.id),
                "registration_id": str(registration.id),
                "academic_year": registration.academic_year.code,
                "level": registration.level,
            },
            status=status.HTTP_200_OK,
        )

    def _calculate_balance_for_identity(self, identity_id) -> Decimal:
        """Calcule le solde d'une identité (somme des factures - paiements)."""
        if not identity_id:
            return Decimal("0")
        total_invoices = (
            Invoice.objects.filter(identity_uuid=identity_id).aggregate(
                total=Sum("total_amount")
            )["total"]
            or Decimal("0")
        )
        total_payments = (
            Payment.objects.filter(invoice__identity_uuid=identity_id).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0")
        )
        return total_invoices - total_payments

    def _get_effective_finance_status(
        self, student: StudentProfile, balance: Decimal
    ) -> str:
        """Calcule le statut financier effectif basé sur le solde."""
        if student.finance_status == "Moratoire":
            return "Moratoire"
        if balance > 0:
            return "Bloqué"
        return "OK"
