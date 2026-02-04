"""
ViewSet pour la gestion des moratoires étudiants.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.academic.models import Moratoire, StudentProfile
from identity.models import CoreIdentity, SysAuditLog

from .mixins import _get_identity_from_request
from .permissions import MoratoirePermission, SoDPermission
from .serializers import MoratoireSerializer


class MoratoireViewSet(ModelViewSet):
    """
    ViewSet pour la gestion des moratoires.

    GET /api/moratoires/ : Liste des moratoires (filtrée par rôle)
    POST /api/moratoires/ : Créer un moratoire (OPERATOR_FINANCE/SCOLARITE)
    PUT /api/moratoires/<id>/respecter/ : Marquer comme 'Respecté'
    DELETE /api/moratoires/<id>/ : Supprimer (ADMIN_SI ou si non actif)
    """

    queryset = Moratoire.objects.select_related("student", "student__identity", "accorde_par").all()
    serializer_class = MoratoireSerializer
    permission_classes = [IsAuthenticated, MoratoirePermission, SoDPermission]

    def get_queryset(self):  # type: ignore[override]
        """Filtre le queryset selon le rôle actif."""
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)

        if not role_active:
            return queryset.none()

        # RECTEUR et ADMIN_SI voient tous les moratoires
        if role_active in {"RECTEUR", "ADMIN_SI"}:
            return queryset

        # OPERATOR_FINANCE, SCOLARITE, OPERATOR_SCOLA voient tous les moratoires
        if role_active in {"OPERATOR_FINANCE", "SCOLARITE", "OPERATOR_SCOLA"}:
            return queryset

        # USER_STUDENT voit uniquement ses propres moratoires
        if role_active == "USER_STUDENT":
            identity = _get_identity_from_request(self.request)
            if identity:
                return queryset.filter(student__identity=identity)
            return queryset.none()

        return queryset.none()

    def perform_create(self, serializer):  # type: ignore[override]
        """Crée un moratoire avec validation SoD."""
        role_active = getattr(self.request, "role_active", None)
        identity = _get_identity_from_request(self.request)

        if not identity:
            raise ValidationError("Identité introuvable.")

        # SoD : OPERATOR_FINANCE ne peut pas s'accorder moratoire à soi-même
        student = serializer.validated_data["student"]
        if role_active == "OPERATOR_FINANCE" and student.identity_id == identity.id:
            raise ValidationError("SoD: impossible de s'accorder un moratoire à soi-même.")

        # Calculer date_fin si non fournie
        duree_jours = serializer.validated_data.get("duree_jours", 30)
        if "date_fin" not in serializer.validated_data or not serializer.validated_data.get("date_fin"):
            date_fin = timezone.now().date() + timedelta(days=duree_jours)
            serializer.validated_data["date_fin"] = date_fin

        # Sauvegarder avec accorde_par et created_by_role
        serializer.save(
            accorde_par=identity,
            created_by_role=role_active or "",
        )

    @action(
        detail=True,
        methods=["PUT", "PATCH"],
        url_path="respecter",
    )
    def respecter(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        PUT /api/moratoires/<id>/respecter/ : Marque un moratoire comme 'Respecté'.
        
        Réservé à OPERATOR_FINANCE, SCOLARITE, OPERATOR_SCOLA.
        """
        role_active = getattr(request, "role_active", None)
        if role_active not in {"OPERATOR_FINANCE", "SCOLARITE", "OPERATOR_SCOLA", "ADMIN_SI"}:
            return Response(
                {"detail": "Accès réservé à OPERATOR_FINANCE, SCOLARITE, OPERATOR_SCOLA ou ADMIN_SI."},
                status=status.HTTP_403_FORBIDDEN,
            )

        moratoire = self.get_object()

        if moratoire.statut != "Actif":
            return Response(
                {"detail": f"Le moratoire n'est plus actif (statut: {moratoire.statut})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_statut = moratoire.statut
        moratoire.statut = "Respecté"
        moratoire.save(update_fields=["statut"])

        # Log audit
        actor_email = getattr(request.user, "email", "")
        SysAuditLog.objects.create(
            action="MORATOIRE_RESPECTE",
            entity_type="MORATOIRE",
            entity_id=moratoire.id,
            actor_email=actor_email,
            active_role=role_active,
            payload={
                "student_id": str(moratoire.student.id),
                "matricule": moratoire.student.matricule_permanent,
                "old_statut": old_statut,
                "new_statut": "Respecté",
            },
        )

        return Response(
            {
                "detail": "Moratoire marqué comme respecté.",
                "moratoire_id": str(moratoire.id),
                "old_statut": old_statut,
                "new_statut": "Respecté",
            },
            status=status.HTTP_200_OK,
        )

    def perform_destroy(self, instance: Moratoire) -> None:  # type: ignore[override]
        """Supprime un moratoire (seulement ADMIN_SI ou si non actif)."""
        role_active = getattr(self.request, "role_active", None)

        if role_active != "ADMIN_SI" and instance.statut == "Actif":
            raise ValidationError("Impossible de supprimer un moratoire actif. Seul ADMIN_SI peut le faire.")

        # Log audit avant suppression
        actor_email = getattr(self.request.user, "email", "")
        SysAuditLog.objects.create(
            action="MORATOIRE_SUPPRIME",
            entity_type="MORATOIRE",
            entity_id=instance.id,
            actor_email=actor_email,
            active_role=role_active or "",
            payload={
                "student_id": str(instance.student.id),
                "matricule": instance.student.matricule_permanent,
                "statut": instance.statut,
            },
        )

        super().perform_destroy(instance)
