from __future__ import annotations

from typing import Any, Dict, List

from django.db.models import Q
from django.http import HttpRequest
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academic.models import (
    CourseElement,
    Evaluation,
    Grade,
    RegistrationPedagogical,
    StudentProfile,
    TeachingUnit,
)
from identity.models import CoreIdentity, SysAuditLog
from uuid import uuid4

from .mixins import _get_identity_from_request
from .permissions import GradesPermission, JuryClosePermission
from .serializers import BulkGradeSerializer, GradeSerializer


class GradesViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des notes.
    
    GET /api/grades/ : Liste filtrée par rôle
    - TEACHER → ses cours
    - STUDENT → ses notes
    - VALIDATOR_ACAD → PV jury
    """
    
    queryset = Grade.objects.select_related(
        "evaluation__course_element__teaching_unit",
        "student__identity",
        "teacher",
    )
    serializer_class = GradeSerializer
    permission_classes = [IsAuthenticated, GradesPermission]
    
    def get_queryset(self):  # type: ignore[override]
        """Filtre le queryset selon le rôle actif."""
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)
        
        if not role_active:
            return queryset.none()
        
        # RECTEUR et ADMIN_SI voient tout
        if role_active in {"RECTEUR", "ADMIN_SI"}:
            return queryset
        
        # TEACHER : seulement les notes de ses cours
        if role_active == "USER_TEACHER":
            identity = _get_identity_from_request(self.request)
            if not identity:
                return queryset.none()
            
            # Récupérer les UE où l'enseignant est assigné
            teaching_units = TeachingUnit.objects.filter(teachers=identity)
            # Récupérer les CourseElement de ces UE
            course_elements = CourseElement.objects.filter(
                teaching_unit__in=teaching_units
            )
            # Récupérer les évaluations de ces éléments de cours
            evaluations = Evaluation.objects.filter(
                course_element__in=course_elements
            )
            # Filtrer les notes par ces évaluations
            return queryset.filter(evaluation__in=evaluations)
        
        # STUDENT : seulement ses propres notes
        if role_active == "USER_STUDENT":
            identity = _get_identity_from_request(self.request)
            if not identity:
                return queryset.none()
            try:
                student = StudentProfile.objects.get(identity=identity)
                return queryset.filter(student=student)
            except StudentProfile.DoesNotExist:
                return queryset.none()
        
        # VALIDATOR_ACAD : PV jury (inscriptions pédagogiques validées)
        if role_active == "VALIDATOR_ACAD":
            identity = _get_identity_from_request(self.request)
            if not identity:
                return queryset.none()
            
            # Récupérer les inscriptions pédagogiques de la faculté du validateur
            # (simplifié : on retourne toutes les notes pour l'instant)
            # TODO: Filtrer par faculté du validateur
            return queryset
        
        # DOYEN : notes de sa faculté
        if role_active == "DOYEN":
            identity = _get_identity_from_request(self.request)
            if not identity:
                return queryset.none()
            
            # Récupérer les UE de la faculté où l'identité est doyen
            teaching_units = TeachingUnit.objects.filter(
                program__faculty__doyen_uuid=identity
            )
            course_elements = CourseElement.objects.filter(
                teaching_unit__in=teaching_units
            )
            evaluations = Evaluation.objects.filter(
                course_element__in=course_elements
            )
            return queryset.filter(evaluation__in=evaluations)
        
        return queryset.none()
    
    def perform_create(self, serializer):  # type: ignore[override]
        """Sauvegarde une note avec le rôle actif."""
        role_active = getattr(self.request, "role_active", None)
        identity = _get_identity_from_request(self.request)
        
        # Vérifier que l'enseignant a accès à ce cours
        if role_active == "USER_TEACHER":
            evaluation_id = serializer.validated_data.get("evaluation")
            if evaluation_id:
                evaluation = Evaluation.objects.select_related(
                    "course_element__teaching_unit"
                ).get(id=evaluation_id.id if hasattr(evaluation_id, "id") else evaluation_id)
                
                # Vérifier que l'enseignant est assigné à l'UE
                if identity and evaluation.course_element:
                    teaching_unit = evaluation.course_element.teaching_unit
                    if teaching_unit and identity not in teaching_unit.teachers.all():
                        raise PermissionDenied(
                            "Vous n'êtes pas autorisé à saisir des notes pour ce cours."
                        )
        
        # Stocker le rôle actif
        serializer.save(
            teacher=identity,
            created_by_role=role_active or "",
        )
    
    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request: HttpRequest) -> Response:
        """
        POST /api/grades/bulk-update/ : Mise à jour en masse des notes.
        TEACHER only, vérifie le scope des cours.
        """
        role_active = getattr(request, "role_active", None)
        if role_active != "USER_TEACHER":
            raise PermissionDenied("Seuls les enseignants peuvent mettre à jour les notes en masse.")
        
        identity = _get_identity_from_request(request)
        if not identity:
            return Response(
                {"detail": "Identité non trouvée."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        serializer = BulkGradeSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        
        # Récupérer les UE où l'enseignant est assigné
        teaching_units = TeachingUnit.objects.filter(teachers=identity)
        course_elements = CourseElement.objects.filter(teaching_unit__in=teaching_units)
        allowed_evaluations = Evaluation.objects.filter(
            course_element__in=course_elements
        )
        allowed_evaluation_ids = set(allowed_evaluations.values_list("id", flat=True))
        
        created_count = 0
        updated_count = 0
        errors: List[Dict[str, Any]] = []
        
        for item in serializer.validated_data:
            evaluation_id = item["evaluation_id"]
            student_id = item["student_id"]
            
            # Vérifier le scope
            if evaluation_id not in allowed_evaluation_ids:
                errors.append({
                    "evaluation_id": evaluation_id,
                    "student_id": student_id,
                    "error": "Vous n'êtes pas autorisé à saisir des notes pour cette évaluation.",
                })
                continue
            
            try:
                evaluation = Evaluation.objects.get(id=evaluation_id)
                student = StudentProfile.objects.get(id=student_id)
                
                # Créer ou mettre à jour la note
                grade, created = Grade.objects.update_or_create(
                    evaluation=evaluation,
                    student=student,
                    defaults={
                        "value": item.get("value"),
                        "is_absent": item.get("is_absent", False),
                        "teacher": identity,
                        "created_by_role": role_active or "",
                    },
                )
                
                if created:
                    created_count += 1
                else:
                    updated_count += 1
                    
            except (Evaluation.DoesNotExist, StudentProfile.DoesNotExist) as e:
                errors.append({
                    "evaluation_id": evaluation_id,
                    "student_id": student_id,
                    "error": str(e),
                })
        
        return Response(
            {
                "detail": "Mise à jour en masse terminée.",
                "created": created_count,
                "updated": updated_count,
                "errors": errors,
            },
            status=status.HTTP_200_OK,
        )


# Fonctions séparées pour les endpoints

from rest_framework.decorators import api_view, permission_classes


@api_view(["POST"])
@permission_classes([IsAuthenticated, JuryClosePermission])
def jury_close(request: HttpRequest) -> Response:
    """
    POST /api/jury/close/ : Clôture le PV jury.
    VALIDATOR_ACAD only, set statut irréversible, log audit.
    """
    role_active = getattr(request, "role_active", None)
    if role_active != "VALIDATOR_ACAD":
        raise PermissionDenied("Seuls les validateurs académiques peuvent clôturer le PV jury.")
    
    registration_id = request.data.get("registration_id")
    if not registration_id:
        raise ValidationError("registration_id est requis.")
    
    try:
        registration = RegistrationPedagogical.objects.select_related(
            "registration_admin__student__identity"
        ).get(id=registration_id)
    except RegistrationPedagogical.DoesNotExist:
        return Response(
            {"detail": "Inscription pédagogique non trouvée."},
            status=status.HTTP_404_NOT_FOUND,
        )
    
    # Vérifier que le statut n'est pas déjà définitif
    if registration.status in {"Validé", "Ajourné"}:
        return Response(
            {"detail": "Le PV est déjà clôturé."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    # Calculer le statut final (déjà fait par le signal, mais on force la mise à jour)
    from apps.academic.services.note_calculator import NoteCalculatorService
    
    statut = NoteCalculatorService.calcule_statut_ue(registration)
    status_mapping = {
        "Validée": "Validé",
        "Ajourné": "Ajourné",
        "Bloquée": "Ajourné",
    }
    new_status = status_mapping.get(statut, "Ajourné")
    
    # Mettre à jour le statut (irréversible)
    registration.status = new_status
    registration.save(update_fields=["status"])
    
    # Log audit
    identity = _get_identity_from_request(request)
    actor_email = identity.email if identity else ""
    SysAuditLog.objects.create(
        action="JURY_PV_CLOSED",
        entity_type="REGISTRATION_PEDAGOGICAL",
        entity_id=uuid4(),
        actor_email=actor_email,
        active_role=role_active or "",
        payload={
            "registration_id": str(registration.id),
            "final_status": new_status,
            "calculated_status": statut,
        },
    )
    
    return Response(
        {
            "detail": "PV clôturé avec succès.",
            "registration_id": registration.id,
            "final_status": new_status,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, GradesPermission])
def my_courses(request: HttpRequest) -> Response:
    """
    GET /api/courses/my-courses/ : Liste les cours de l'enseignant.
    TEACHER only.
    """
    role_active = getattr(request, "role_active", None)
    if role_active != "USER_TEACHER":
        return Response(
            {"detail": "Seuls les enseignants peuvent accéder à cette ressource."},
            status=status.HTTP_403_FORBIDDEN,
        )
    
    identity = _get_identity_from_request(request)
    if not identity:
        return Response(
            {"detail": "Identité non trouvée."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    
    # Récupérer les UE où l'enseignant est assigné
    teaching_units = TeachingUnit.objects.filter(teachers=identity).select_related(
        "program", "program__faculty"
    )
    
    # Récupérer les éléments de cours de ces UE
    course_elements = CourseElement.objects.filter(
        teaching_unit__in=teaching_units,
        is_active=True,
    ).select_related("teaching_unit", "teaching_unit__program")
    
    # Récupérer les évaluations de ces éléments
    evaluations = Evaluation.objects.filter(
        course_element__in=course_elements,
    ).select_related("course_element", "course_element__teaching_unit")
    
    courses_data = []
    for evaluation in evaluations:
        course_element = evaluation.course_element
        teaching_unit = course_element.teaching_unit if course_element else None
        
        courses_data.append({
            "evaluation_id": evaluation.id,
            "course_element_code": course_element.code if course_element else None,
            "course_element_name": course_element.name if course_element else None,
            "teaching_unit_code": teaching_unit.code if teaching_unit else None,
            "teaching_unit_name": teaching_unit.name if teaching_unit else None,
            "evaluation_type": evaluation.type,
            "session_date": evaluation.session_date,
            "is_closed": evaluation.is_closed,
        })
    
    return Response(
        {
            "count": len(courses_data),
            "results": courses_data,
        },
        status=status.HTTP_200_OK,
    )
