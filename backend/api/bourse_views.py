"""
ViewSet pour la gestion des bourses étudiants.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from uuid import uuid4

from apps.academic.models import Bourse, StudentProfile
from identity.models import CoreIdentity, SysAuditLog

from .mixins import _get_identity_from_request
from .permissions import BoursePermission, SoDPermission
from .serializers import BourseSerializer


class BourseViewSet(ModelViewSet):
    """
    ViewSet pour la gestion des bourses.

    GET /api/bourses/ : Liste des bourses (filtrée par rôle)
    POST /api/bourses/ : Créer une bourse (SCOLARITE/RECTEUR)
    PUT /api/bourses/<id>/suspendre/ : Suspendre une bourse (RECTEUR)
    DELETE /api/bourses/<id>/ : Supprimer (ADMIN_SI)
    """

    queryset = Bourse.objects.select_related(
        "student", "student__identity", "accorde_par", "annee_academique"
    ).all()
    serializer_class = BourseSerializer
    permission_classes = [IsAuthenticated, BoursePermission, SoDPermission]

    def get_queryset(self):  # type: ignore[override]
        """Filtre le queryset selon le rôle actif et les paramètres de requête."""
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)

        if not role_active:
            return queryset.none()

        # Filtrer par statut si fourni dans les paramètres de requête
        statut_param = self.request.query_params.get("statut")
        if statut_param:
            queryset = queryset.filter(statut=statut_param)

        # RECTEUR voit toutes les bourses
        if role_active == "RECTEUR":
            return queryset

        # SCOLARITE voit toutes les bourses (pour attribution)
        if role_active == "SCOLARITE":
            return queryset

        # OPERATOR_FINANCE voit toutes les bourses (pour suivi)
        if role_active == "OPERATOR_FINANCE":
            return queryset

        # USER_STUDENT voit uniquement ses propres bourses
        if role_active == "USER_STUDENT":
            identity = _get_identity_from_request(self.request)
            if identity:
                return queryset.filter(student__identity=identity)
            return queryset.none()

        # ADMIN_SI voit toutes les bourses
        if role_active == "ADMIN_SI":
            return queryset

        return queryset.none()

    def perform_create(self, serializer):  # type: ignore[override]
        """Crée une bourse avec validation SoD."""
        role_active = getattr(self.request, "role_active", None)
        identity = _get_identity_from_request(self.request)

        if not identity:
            raise ValidationError("Identité introuvable.")

        # SoD : SCOLARITE ne peut pas s'accorder bourse à soi-même
        student = serializer.validated_data["student"]
        if role_active == "SCOLARITE" and student.identity_id == identity.id:
            raise ValidationError("SoD: impossible de s'accorder une bourse à soi-même.")

        # Sauvegarder avec accorde_par et created_by_role
        serializer.save(
            accorde_par=identity,
            created_by_role=role_active or "",
        )

    @action(
        detail=True,
        methods=["PUT", "PATCH"],
        url_path="suspendre",
    )
    def suspendre(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        PUT /api/bourses/<id>/suspendre/ : Suspend une bourse (statut → 'Suspendue').
        
        Réservé à RECTEUR.
        """
        role_active = getattr(request, "role_active", None)
        if role_active not in {"RECTEUR", "ADMIN_SI"}:
            return Response(
                {"detail": "Accès réservé à RECTEUR ou ADMIN_SI."},
                status=status.HTTP_403_FORBIDDEN,
            )

        bourse = self.get_object()

        if bourse.statut == Bourse.StatutChoices.TERMINEE:
            return Response(
                {"detail": f"La bourse est déjà terminée (statut: {bourse.statut})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_statut = bourse.statut
        bourse.statut = Bourse.StatutChoices.SUSPENDUE
        bourse.save(update_fields=["statut"])

        # Recalculer le solde de l'étudiant (la bourse n'est plus active)
        from apps.academic.services.frais_echeance_calculator import FraisEcheanceCalculator

        calculator = FraisEcheanceCalculator()
        calculator.update_solde_etudiant(bourse.student)

        # Log audit
        actor_email = getattr(request.user, "email", "")
        SysAuditLog.objects.create(
            action="BOURSE_SUSPENDUE",
            entity_type="BOURSE",
            entity_id=uuid4(),
            actor_email=actor_email,
            active_role=role_active or "",
            payload={
                "bourse_id": str(bourse.id),
                "student_id": str(bourse.student.id),
                "matricule": bourse.student.matricule_permanent,
                "old_statut": old_statut,
                "new_statut": Bourse.StatutChoices.SUSPENDUE,
            },
        )

        return Response(
            {
                "detail": "Bourse suspendue avec succès.",
                "bourse_id": str(bourse.id),
                "old_statut": old_statut,
                "new_statut": Bourse.StatutChoices.SUSPENDUE,
            },
            status=status.HTTP_200_OK,
        )

    def perform_destroy(self, instance: Bourse) -> None:  # type: ignore[override]
        """Supprime une bourse (seulement ADMIN_SI)."""
        role_active = getattr(self.request, "role_active", None)

        if role_active != "ADMIN_SI":
            raise ValidationError("Seul ADMIN_SI peut supprimer une bourse.")

        # Recalculer le solde de l'étudiant avant suppression
        from apps.academic.services.frais_echeance_calculator import FraisEcheanceCalculator

        calculator = FraisEcheanceCalculator()
        calculator.update_solde_etudiant(instance.student)

        # Log audit avant suppression
        actor_email = getattr(self.request.user, "email", "")
        SysAuditLog.objects.create(
            action="BOURSE_SUPPRIMEE",
            entity_type="BOURSE",
            entity_id=uuid4(),
            actor_email=actor_email,
            active_role=role_active or "",
            payload={
                "bourse_id": str(instance.id),
                "student_id": str(instance.student.id),
                "matricule": instance.student.matricule_permanent,
                "type_bourse": instance.type_bourse,
                "montant": str(instance.montant),
                "statut": instance.statut,
            },
        )

        super().perform_destroy(instance)
