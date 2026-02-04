"""ViewSet pour la gestion des demandes administratives."""
from __future__ import annotations

from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.academic.models import DemandeAdministrative, StudentProfile
from identity.models import CoreIdentity, SysAuditLog
from uuid import uuid4

from .mixins import _get_identity_from_request
from .permissions import DemandePermission, UserStudentPermission
from .serializers import DemandeAdministrativeCreateSerializer, DemandeAdministrativeSerializer


class DemandeViewSet(ModelViewSet):
    """
    ViewSet pour la gestion des demandes administratives.

    GET /api/demandes/ : Liste des demandes (filtrée par rôle)
    POST /api/demandes/ : Créer une demande (USER_STUDENT)
    PUT /api/demandes/<id>/traiter/ : Traiter une demande (SCOLARITE/RECTEUR)
    """

    queryset = DemandeAdministrative.objects.select_related("student", "student__identity", "traite_par").all()
    serializer_class = DemandeAdministrativeSerializer
    permission_classes = [IsAuthenticated, UserStudentPermission, DemandePermission]

    def get_queryset(self):  # type: ignore[override]
        """Filtre le queryset selon le rôle actif."""
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)

        if not role_active:
            return queryset.none()

        # USER_STUDENT : seulement ses propres demandes
        if role_active == "USER_STUDENT":
            identity = _get_identity_from_request(self.request)
            if identity:
                try:
                    student = StudentProfile.objects.get(identity=identity)
                    return queryset.filter(student=student)
                except StudentProfile.DoesNotExist:
                    return queryset.none()
            return queryset.none()

        # SCOLARITE, RECTEUR, ADMIN_SI : toutes les demandes
        if role_active in {"SCOLARITE", "RECTEUR", "ADMIN_SI"}:
            # Permettre le filtrage par statut via query param
            statut_filter = self.request.query_params.get("statut")
            if statut_filter:
                queryset = queryset.filter(statut=statut_filter)
            return queryset

        return queryset.none()

    def get_serializer_class(self):  # type: ignore[override]
        """Utilise le serializer de création pour POST."""
        if self.action == "create":
            return DemandeAdministrativeCreateSerializer
        return DemandeAdministrativeSerializer

    def perform_create(self, serializer):  # type: ignore[override]
        """Crée une demande avec l'étudiant actuel."""
        role_active = getattr(self.request, "role_active", None)
        identity = _get_identity_from_request(self.request)

        if not identity:
            raise ValueError("Identité introuvable.")

        if role_active != "USER_STUDENT":
            raise ValueError("Seuls les étudiants peuvent créer des demandes.")

        try:
            student = StudentProfile.objects.get(identity=identity)
        except StudentProfile.DoesNotExist:
            raise ValueError("Profil étudiant introuvable.")

        demande = serializer.save(
            student=student,
            statut=DemandeAdministrative.StatutChoices.EN_ATTENTE,
        )

        # Log audit
        SysAuditLog.objects.create(
            action="DEMANDE_ADMINISTRATIVE_CREATED",
            entity_type="DEMANDE_ADMINISTRATIVE",
            entity_id=uuid4(),
            actor_email=identity.email,
            active_role=role_active or "",
            payload={
                "demande_id": str(demande.id),
                "student_id": str(student.id),
                "matricule": student.matricule_permanent,
                "type_demande": demande.type_demande,
            },
        )

    def update(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """PUT : bloqué pour USER_STUDENT."""
        role_active = getattr(request, "role_active", None)
        if role_active == "USER_STUDENT":
            return Response(
                {"detail": "Accès réservé aux rôles administratifs. Vous ne pouvez pas modifier votre demande."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """PATCH : bloqué pour USER_STUDENT."""
        role_active = getattr(request, "role_active", None)
        if role_active == "USER_STUDENT":
            return Response(
                {"detail": "Accès réservé aux rôles administratifs. Vous ne pouvez pas modifier votre demande."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """DELETE : bloqué pour USER_STUDENT."""
        role_active = getattr(request, "role_active", None)
        if role_active == "USER_STUDENT":
            return Response(
                {"detail": "Accès réservé aux rôles administratifs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["PUT", "PATCH"],
        url_path="traiter",
    )
    def traiter(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        PUT /api/demandes/<id>/traiter/ : Traite une demande.
        Réservé à SCOLARITE, RECTEUR.
        """
        role_active = getattr(request, "role_active", None)
        if role_active not in {"SCOLARITE", "RECTEUR", "ADMIN_SI"}:
            return Response(
                {"detail": "Accès réservé à SCOLARITE, RECTEUR ou ADMIN_SI."},
                status=status.HTTP_403_FORBIDDEN,
            )

        demande = self.get_object()
        identity = _get_identity_from_request(request)

        if not identity:
            return Response(
                {"detail": "Identité introuvable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        statut = request.data.get("statut")
        commentaire = request.data.get("commentaire", "")

        if statut not in [DemandeAdministrative.StatutChoices.APPROUVEE, DemandeAdministrative.StatutChoices.REJETEE]:
            return Response(
                {"detail": "Statut invalide. Utilisez 'Approuvée' ou 'Rejetée'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_statut = demande.statut
        demande.statut = statut
        demande.commentaire = commentaire
        demande.traite_par = identity
        demande.date_traitement = timezone.now()
        demande.save(update_fields=["statut", "commentaire", "traite_par", "date_traitement"])

        # Log audit
        SysAuditLog.objects.create(
            action="DEMANDE_ADMINISTRATIVE_TRAITEE",
            entity_type="DEMANDE_ADMINISTRATIVE",
            entity_id=demande.id,
            actor_email=identity.email,
            active_role=role_active or "",
            payload={
                "demande_id": str(demande.id),
                "student_id": str(demande.student.id),
                "matricule": demande.student.matricule_permanent,
                "old_statut": old_statut,
                "new_statut": statut,
                "type_demande": demande.type_demande,
            },
        )

        return Response(
            {
                "detail": "Demande traitée avec succès.",
                "demande_id": str(demande.id),
                "old_statut": old_statut,
                "new_statut": statut,
            },
            status=status.HTTP_200_OK,
        )
