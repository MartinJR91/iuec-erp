from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core import signals as _signals  # noqa: F401
from apps.academic.models import (
    AcademicYear,
    Evaluation,
    Grade,
    Program,
    RegistrationAdmin,
    RegistrationPedagogical,
    StudentProfile,
    TeachingUnit,
)
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, IdentityRoleLink, SysAuditLog
from .serializers import StudentProfileSerializer
from apps.academic.services.note_calculator import EvaluationScore, UEGradeCalculator


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_data(request: HttpRequest) -> Response:
    """
    Endpoint pour récupérer les données du dashboard selon le rôle actif.
    GET /api/dashboard/?role=RECTEUR (optionnel, utilise request.role_active par défaut)
    """
    try:
        # Récupérer le rôle depuis query param ou request.role_active (injecté par middleware)
        role = request.GET.get("role") or getattr(request, "role_active", None)

        if not role:
            return Response(
                {"detail": "Rôle actif requis. Fournissez ?role=XXX ou header X-Role-Active."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier que l'utilisateur a bien ce rôle
        user_email = getattr(request.user, "email", "")
        if request.user.is_authenticated and user_email:
            try:
                identity = CoreIdentity.objects.get(email__iexact=user_email, is_active=True)
                user_roles = list(
                    IdentityRoleLink.objects.filter(identity=identity, is_active=True)
                    .select_related("role")
                    .values_list("role__code", flat=True)
                )
                # Si pas de rôles, permettre quand même l'accès (pour la démo)
                if user_roles and role not in user_roles:
                    return Response(
                        {"detail": f"Rôle '{role}' non autorisé pour cet utilisateur.", "available_roles": user_roles},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except CoreIdentity.DoesNotExist:
                # En démo, permettre l'accès même si l'identité n'existe pas
                pass
            except Exception as e:
                # Log l'erreur mais ne bloque pas (pour la démo)
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Erreur lors de la vérification des rôles: {str(e)}")

        # Générer les données selon le rôle
        data: dict = {}

        if role in ("RECTEUR", "DAF", "SG", "VIEWER_STRATEGIC", "ADMIN_SI"):
            # Dashboard institutionnel : KPI + graphique évolution
            total_students = StudentProfile.objects.count()
            total_registrations = RegistrationAdmin.objects.count()
            attendance_rate = (
                int((total_registrations / total_students) * 100)
                if total_students
                else 0
            )

            month_start = timezone.now().date().replace(day=1)
            monthly_total = (
                Invoice.objects.filter(
                    status=Invoice.STATUS_PAID, issue_date__gte=month_start
                ).aggregate(total=Sum("total_amount"))["total"]
                or Decimal("0")
            )
            monthly_revenue = f"{int(monthly_total):,}".replace(",", " ") + " XAF"

            sod_since = timezone.now() - timedelta(days=30)
            sod_alerts = SysAuditLog.objects.filter(
                action__icontains="SOD", created_at__gte=sod_since
            ).count()

            students_by_faculty = (
                StudentProfile.objects.values("current_program__faculty__code")
                .annotate(count=Count("id"))
                .order_by("current_program__faculty__code")
            )

            enrollment_evolution = []
            for item in (
                StudentProfile.objects.annotate(month=TruncMonth("date_entree"))
                .values("month")
                .annotate(count=Count("id"))
                .order_by("month")
            ):
                month = item["month"]
                if not month:
                    continue
                enrollment_evolution.append(
                    {"month": month.strftime("%b %Y"), "value": item["count"]}
                )

            data = {
                "kpis": {
                    "studentsCount": total_students,
                    "monthlyRevenue": monthly_revenue,
                    "sodAlerts": sod_alerts,
                    "attendanceRate": attendance_rate,
                    "studentsByFaculty": [
                        {
                            "facultyCode": item["current_program__faculty__code"] or "N/A",
                            "students": item["count"],
                        }
                        for item in students_by_faculty
                    ],
                },
                "graph": enrollment_evolution,
            }

            SysAuditLog.objects.create(
                action="KPI_ACCESS",
                entity_type="DASHBOARD",
                entity_id=uuid4(),
                actor_email=user_email,
                active_role=role,
                payload={
                    "kpis": ["studentsCount", "monthlyRevenue", "sodAlerts", "attendanceRate"],
                    "studentsByFaculty": True,
                },
            )

        elif role in ("USER_TEACHER", "ENSEIGNANT"):
            # Dashboard enseignant : liste des cours
            # Mock courses (à remplacer par vraie query sur TeachingSession ou Course)
            courses = [
                {
                    "code": "MATH101",
                    "name": "Mathématiques Fondamentales",
                    "studentCount": 45,
                    "nextClass": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
                },
                {
                    "code": "PHYS201",
                    "name": "Physique Quantique",
                    "studentCount": 32,
                    "nextClass": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
                },
                {
                    "code": "INFO301",
                    "name": "Algorithmes Avancés",
                    "studentCount": 28,
                    "nextClass": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
                },
                {
                    "code": "STAT202",
                    "name": "Statistiques",
                    "studentCount": 38,
                    "nextClass": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),
                },
            ]

            # Mock stats (à remplacer par vraie query sur GradeEntry)
            stats = {
                "gradedStudents": 85,
                "totalStudents": 120,
            }

            data = {
                "courses": courses,
                "stats": stats,
            }

        elif role == "USER_STUDENT":
            # Dashboard étudiant : notes récentes + solde
            try:
                CoreIdentity.objects.get(email__iexact=user_email, is_active=True)
            except CoreIdentity.DoesNotExist:
                pass

            # Mock grades (à remplacer par vraie query sur GradeEntry)
            grades = [
                {"ueCode": "UE_MATH", "average": 14.5, "status": "Validée"},
                {"ueCode": "UE_PHYS", "average": 11.2, "status": "Validée"},
                {"ueCode": "UE_INFO", "average": 8.5, "status": "Ajourné"},
                {"ueCode": "UE_STAT", "average": 12.8, "status": "Validée"},
            ]

            balance = _get_balance_for_identity(
                CoreIdentity.objects.filter(email__iexact=user_email).values_list(
                    "id", flat=True
                ).first()
            )

            data = {
                "grades": grades,
                "balance": float(balance or 0),
            }

        elif role == "OPERATOR_FINANCE":
            # Dashboard finance : factures impayées (vraies données)
            from apps.finance.models import Invoice, Payment
            from django.db.models import Sum, F

            # Récupérer les factures non payées (status ISSUED ou DRAFT, montant > paiements)
            unpaid_invoices_qs = Invoice.objects.filter(
                status__in=[Invoice.STATUS_ISSUED, Invoice.STATUS_DRAFT]
            ).annotate(
                total_paid=Sum("payments__amount")
            ).filter(
                total_amount__gt=F("total_paid") + Decimal("0")
            )[:20]  # Limiter à 20 pour performance

            unpaid_invoices = []
            for invoice in unpaid_invoices_qs:
                try:
                    student_profile = StudentProfile.objects.select_related("identity").get(
                        identity_id=invoice.identity_uuid
                    )
                    student_name = f"{student_profile.identity.last_name} {student_profile.identity.first_name}"
                except StudentProfile.DoesNotExist:
                    student_name = f"Étudiant {invoice.identity_uuid}"

                total_paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
                remaining = invoice.total_amount - total_paid

                unpaid_invoices.append({
                    "id": str(invoice.id),
                    "invoice_number": invoice.number or f"INV-{invoice.id}",
                    "student": student_name,
                    "amount": float(remaining),
                    "total_amount": float(invoice.total_amount),
                    "dueDate": invoice.due_date.isoformat() if invoice.due_date else None,
                    "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
                })

            total_pending = sum(inv["amount"] for inv in unpaid_invoices)

            data = {
                "unpaidInvoices": unpaid_invoices,
                "totalPending": total_pending,
            }

        elif role == "SCOLARITE":
            # Dashboard scolarité : statistiques inscriptions
            total_students = StudentProfile.objects.count()
            total_registrations = RegistrationAdmin.objects.count()
            registrations_this_year = RegistrationAdmin.objects.filter(
                academic_year__is_active=True
            ).count()

            data = {
                "kpis": {
                    "totalStudents": total_students,
                    "totalRegistrations": total_registrations,
                    "registrationsThisYear": registrations_this_year,
                },
            }

        else:
            # Rôle non géré
            data = {"message": f"Dashboard non disponible pour le rôle '{role}'."}

        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        # Gestion d'erreur globale pour éviter les 500
        import logging
        import traceback

        logger = logging.getLogger(__name__)
        error_details = traceback.format_exc()
        logger.error(f"Erreur dans dashboard_data: {str(e)}\n{error_details}")

        return Response(
            {
                "detail": "Erreur serveur lors de la récupération des données du dashboard.",
                "error": str(e) if __debug__ else None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _get_scope_code(identity: CoreIdentity, role_code: str) -> str | None:
    metadata = identity.metadata or {}
    scope_by_role = metadata.get("scope_by_role", {})
    scope = None
    if isinstance(scope_by_role, dict):
        scope = scope_by_role.get(role_code)
    return str(scope) if scope else None


def _get_balance_for_identity(identity_id) -> Decimal:
    if not identity_id:
        return Decimal("0")
    invoices_total = (
        Invoice.objects.filter(identity_uuid=identity_id).aggregate(
            total=Sum("total_amount")
        )["total"]
        or Decimal("0")
    )
    paid_total = (
        Payment.objects.filter(invoice__identity_uuid=identity_id).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0")
    )
    return invoices_total - paid_total


def _get_balances_for_identities(identity_ids: list) -> dict:
    if not identity_ids:
        return {}
    invoices = (
        Invoice.objects.filter(identity_uuid__in=identity_ids)
        .values("identity_uuid")
        .annotate(total=Sum("total_amount"))
    )
    payments = (
        Payment.objects.filter(invoice__identity_uuid__in=identity_ids)
        .values("invoice__identity_uuid")
        .annotate(total=Sum("amount"))
    )
    invoice_map = {row["identity_uuid"]: row["total"] or Decimal("0") for row in invoices}
    payment_map = {
        row["invoice__identity_uuid"]: row["total"] or Decimal("0")
        for row in payments
    }
    balances = {}
    for identity_id in identity_ids:
        balances[identity_id] = invoice_map.get(identity_id, Decimal("0")) - payment_map.get(
            identity_id, Decimal("0")
        )
    return balances


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def students_endpoint(request: HttpRequest) -> Response:
    role_active = getattr(request, "role_active", None)
    if not role_active:
        return Response({"detail": "Rôle actif requis."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        queryset = StudentProfile.objects.select_related(
            "identity", "current_program", "current_program__faculty"
        )
        if role_active in {"RECTEUR", "ADMIN_SI"}:
            pass
        elif role_active == "OPERATOR_FINANCE":
            queryset = queryset.filter(
                finance_status__in=[
                    StudentProfile.FinanceStatus.BLOCKED,
                    StudentProfile.FinanceStatus.MORATORIUM,
                ]
            )
        elif role_active in {"USER_TEACHER", "ENSEIGNANT"}:
            identity = CoreIdentity.objects.filter(
                email__iexact=getattr(request.user, "email", "")
            ).first()
            if not identity:
                queryset = queryset.none()
            else:
                scope_code = _get_scope_code(identity, "USER_TEACHER")
                if scope_code:
                    queryset = queryset.filter(current_program__code__iexact=scope_code)
                else:
                    queryset = queryset.none()
        elif role_active == "USER_STUDENT":
            identity = CoreIdentity.objects.filter(
                email__iexact=getattr(request.user, "email", "")
            ).first()
            if identity:
                queryset = queryset.filter(identity=identity)
            else:
                queryset = queryset.none()
        else:
            return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

        identity_ids = list(queryset.values_list("identity_id", flat=True))
        balances = _get_balances_for_identities(identity_ids)
        serializer = StudentProfileSerializer(
            queryset, many=True, context={"balances": balances}
        )

        total_students = queryset.count()
        total_registrations = RegistrationAdmin.objects.filter(
            student__in=queryset
        ).count()
        inscription_rate = (
            int((total_registrations / total_students) * 100)
            if total_students
            else 0
        )
        faculty_stats = (
            queryset.values("current_program__faculty__code")
            .annotate(count=Count("id"))
            .order_by("current_program__faculty__code")
        )

        return Response(
            {
                "results": serializer.data,
                "stats": {
                    "total_students": total_students,
                    "total_registrations": total_registrations,
                    "inscription_rate": inscription_rate,
                    "by_faculty": [
                        {
                            "faculty_code": item["current_program__faculty__code"],
                            "students": item["count"],
                        }
                        for item in faculty_stats
                    ],
                },
            },
            status=status.HTTP_200_OK,
        )

    allowed_roles = {
        "RECTEUR",
        "ADMIN_SI",
        "VALIDATOR_ACAD",
        "DOYEN",
        "USER_STUDENT",
        "OPERATOR_FINANCE",
    }
    if role_active not in allowed_roles:
        return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data if hasattr(request, "data") else {}
    identity_uuid = payload.get("identity_uuid")
    matricule_permanent = payload.get("matricule_permanent") or payload.get("matricule")  # Compatibilité
    date_entree = payload.get("date_entree")
    program_id = payload.get("program_id")
    year_id = payload.get("year_id")
    level = payload.get("level")
    finance_status = payload.get("finance_status", StudentProfile.FinanceStatus.OK)

    missing_fields = [
        field
        for field in ("identity_uuid", "matricule_permanent", "date_entree", "program_id", "year_id", "level")
        if not payload.get(field) and field != "matricule_permanent" or not matricule_permanent
    ]
    if missing_fields:
        return Response(
            {"detail": f"Champs requis manquants: {', '.join(missing_fields)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    identity = CoreIdentity.objects.filter(id=identity_uuid).first()
    if not identity:
        return Response({"detail": "Identité introuvable."}, status=status.HTTP_404_NOT_FOUND)

    balance = _get_balance_for_identity(identity.id)
    if balance > 0:
        return Response(
            {"detail": "Inscription bloquée: solde négatif."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    current_identity = CoreIdentity.objects.filter(
        email__iexact=getattr(request.user, "email", "")
    ).first()

    if role_active == "USER_STUDENT" and current_identity and identity.id != current_identity.id:
        return Response({"detail": "Inscription interdite pour un autre étudiant."}, status=status.HTTP_403_FORBIDDEN)
    if role_active not in {"USER_STUDENT", "OPERATOR_FINANCE"} and current_identity and identity.id == current_identity.id:
        return Response({"detail": "SoD: inscription interdite pour soi-même."}, status=status.HTTP_403_FORBIDDEN)
    if role_active == "OPERATOR_FINANCE" and finance_status != StudentProfile.FinanceStatus.MORATORIUM:
        return Response(
            {"detail": "OPERATOR_FINANCE peut uniquement appliquer un moratoire."},
            status=status.HTTP_403_FORBIDDEN,
        )

    program = Program.objects.filter(id=program_id).first()
    if not program:
        return Response({"detail": "Programme introuvable."}, status=status.HTTP_404_NOT_FOUND)

    academic_year = AcademicYear.objects.filter(id=year_id).first()
    if not academic_year:
        return Response({"detail": "Année académique introuvable."}, status=status.HTTP_404_NOT_FOUND)

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
        student_profile.finance_status = finance_status
        student_profile.save()

    registration = RegistrationAdmin.objects.create(
        student=student_profile,
        academic_year=academic_year,
        level=level,
        finance_status=finance_status,
    )

    return Response(
        {
            "detail": "Inscription créée.",
            "student_id": str(student_profile.id),
            "registration_id": str(registration.id),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_registration(request: HttpRequest) -> Response:
    role_active = getattr(request, "role_active", None)
    if role_active not in {"DOYEN", "VALIDATOR_ACAD", "RECTEUR", "ADMIN_SI"}:
        return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data if hasattr(request, "data") else {}
    registration_ids = payload.get("registration_ids", [])
    registration_id = payload.get("registration_id")
    student_id = payload.get("student_id")
    finance_status = payload.get("finance_status", StudentProfile.FinanceStatus.OK)
    
    # Support pour validation multiple
    if registration_ids and isinstance(registration_ids, list):
        validated_count = 0
        errors = []
        for reg_id in registration_ids:
            try:
                registration = RegistrationAdmin.objects.select_related(
                    "student", "student__identity", "student__current_program__faculty"
                ).get(id=reg_id)
                
                # Vérification SoD
                current_identity = CoreIdentity.objects.filter(
                    email__iexact=getattr(request.user, "email", "")
                ).first()
                if current_identity and str(registration.student.identity_id) == str(current_identity.id):
                    errors.append(f"Inscription {reg_id}: SoD violation")
                    continue
                
                # Vérification scope pour DOYEN/VALIDATOR_ACAD
                if role_active in {"DOYEN", "VALIDATOR_ACAD"} and current_identity:
                    scope_code = _get_scope_code(current_identity, role_active)
                    if registration.student.current_program:
                        faculty_code = registration.student.current_program.faculty.code
                        if scope_code and scope_code.upper() != faculty_code.upper():
                            errors.append(f"Inscription {reg_id}: Faculté non autorisée")
                            continue
                
                registration.finance_status = finance_status
                registration.save(update_fields=["finance_status"])
                registration.student.finance_status = finance_status
                registration.student.save(update_fields=["finance_status"])
                validated_count += 1
            except RegistrationAdmin.DoesNotExist:
                errors.append(f"Inscription {reg_id}: introuvable")
            except Exception as e:
                errors.append(f"Inscription {reg_id}: {str(e)}")
        
        return Response(
            {
                "detail": f"{validated_count} inscription(s) validée(s).",
                "validated_count": validated_count,
                "errors": errors if errors else None,
            },
            status=status.HTTP_200_OK,
        )
    
    # Support pour validation unique (rétrocompatibilité)
    if not registration_id and not student_id:
        return Response(
            {"detail": "registration_id, student_id ou registration_ids requis."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    registration_query = RegistrationAdmin.objects.select_related(
        "student", "student__identity", "student__current_program__faculty"
    )
    if registration_id:
        registration = registration_query.filter(id=registration_id).first()
    else:
        registration = (
            registration_query.filter(student_id=student_id)
            .order_by("-id")
            .first()
        )
    if not registration:
        return Response({"detail": "Inscription introuvable."}, status=status.HTTP_404_NOT_FOUND)

    current_identity = CoreIdentity.objects.filter(
        email__iexact=getattr(request.user, "email", "")
    ).first()
    if current_identity and registration.student.identity_id == current_identity.id:
        SysAuditLog.objects.create(
            action="SOD_CONFLICT",
            entity_type="REGISTRATION",
            entity_id=uuid4(),
            actor_email=current_identity.email,
            active_role=role_active or "",
            payload={"reason": "self_validation", "student_id": str(registration.student_id)},
        )
        return Response({"detail": "SoD: validation interdite pour soi-même."}, status=status.HTTP_403_FORBIDDEN)

    if role_active in {"DOYEN", "VALIDATOR_ACAD"} and current_identity:
        scope_code = _get_scope_code(current_identity, role_active)
        if not registration.student.current_program:
            return Response({"detail": "Étudiant sans programme."}, status=status.HTTP_400_BAD_REQUEST)
        faculty_code = registration.student.current_program.faculty.code
        if scope_code and scope_code.upper() != faculty_code.upper():
            return Response({"detail": "Faculté non autorisée."}, status=status.HTTP_403_FORBIDDEN)

    registration.finance_status = finance_status
    registration.save(update_fields=["finance_status"])
    registration.student.finance_status = finance_status
    registration.student.save(update_fields=["finance_status"])

    return Response(
        {"detail": "Inscription validée.", "registration_id": str(registration.id)},
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def grades_endpoint(request: HttpRequest) -> Response:
    role_active = getattr(request, "role_active", None)
    if not role_active:
        return Response({"detail": "Rôle actif requis."}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        if role_active not in {"VALIDATOR_ACAD", "DOYEN", "RECTEUR", "ADMIN_SI", "USER_STUDENT", "USER_TEACHER", "ENSEIGNANT"}:
            return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
        course_id = request.GET.get("course_id")
        program_code = request.GET.get("program")
        if not course_id:
            if role_active == "USER_STUDENT":
                identity = CoreIdentity.objects.filter(
                    email__iexact=getattr(request.user, "email", "")
                ).first()
                if identity and hasattr(identity, "student_profile"):
                    balance = _get_balance_for_identity(identity.id)
                    if balance > 0 or identity.student_profile.finance_status in {
                        StudentProfile.FinanceStatus.BLOCKED,
                        StudentProfile.FinanceStatus.MORATORIUM,
                    }:
                        return Response(
                            {"detail": "Accès aux cours bloqué pour raison financière."},
                            status=status.HTTP_403_FORBIDDEN,
                        )
                    if identity.student_profile.current_program:
                        program_code = identity.student_profile.current_program.code
                    else:
                        return Response(
                            {"detail": "Étudiant sans programme."},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
            if not program_code:
                return Response(
                    {"detail": "course_id ou program requis."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            students = StudentProfile.objects.select_related(
                "identity", "current_program"
            ).filter(current_program__code__iexact=program_code)
            results = [
                {
                    "student_id": str(student.id),
                    "matricule_permanent": student.matricule_permanent,
                    "email": student.identity.email,
                    "program_code": student.current_program.code if student.current_program else None,
                    "average": None,
                    "status": "N/A",
                }
                for student in students
            ]
            return Response(
                {
                    "course_id": None,
                    "program": program_code,
                    "evaluations_count": 0,
                    "results": results,
                },
                status=status.HTTP_200_OK,
            )

        evaluations = Evaluation.objects.filter(course_id=course_id)
        grades = (
            Grade.objects.select_related("student", "evaluation", "student__current_program")
            .filter(evaluation__course_id=course_id)
            .order_by("student_id")
        )

        student_map: dict[int, list[EvaluationScore]] = {}
        student_grades_map: dict[int, dict[str, float]] = {}  # {student_id: {"CC": value, "TP": value, "EXAM": value}}
        
        for grade in grades:
            student_id = grade.student_id
            eval_type = grade.evaluation.type
            
            # Ajouter à student_map pour calcul moyenne
            student_map.setdefault(student_id, []).append(
                EvaluationScore(
                    component=eval_type,
                    value=grade.value,
                    weight=grade.evaluation.weight,
                    max_score=grade.evaluation.max_score,
                )
            )
            
            # Stocker les notes par composante
            if student_id not in student_grades_map:
                student_grades_map[student_id] = {}
            student_grades_map[student_id][eval_type] = float(grade.value)

        results = []
        for student_id, items in student_map.items():
            student = grades.filter(student_id=student_id).first()
            if not student:
                continue
            if not student.student.current_program:
                continue
            rules = student.student.current_program.academic_rules_json
            ue_result = UEGradeCalculator.calculate(items, rules)
            grades_data = student_grades_map.get(student_id, {})
            results.append(
                {
                    "student_id": str(student.student_id),
                    "matricule_permanent": student.student.matricule_permanent,
                    "email": student.student.identity.email,
                    "program_code": student.student.current_program.code,
                    "cc": grades_data.get("CC"),
                    "tp": grades_data.get("TP"),
                    "exam": grades_data.get("EXAM"),
                    "average": float(ue_result.average),
                    "status": "VALIDÉ" if ue_result.validated else "AJOURNÉ",
                }
            )

        return Response(
            {
                "course_id": course_id,
                "evaluations_count": evaluations.count(),
                "results": results,
            },
            status=status.HTTP_200_OK,
        )

    if role_active not in {"USER_TEACHER", "ENSEIGNANT"}:
        return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data if hasattr(request, "data") else {}
    evaluation_id = payload.get("evaluation_id")
    grades_payload = payload.get("grades", [])
    if not evaluation_id or not isinstance(grades_payload, list):
        return Response(
            {"detail": "evaluation_id et grades[] requis."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    evaluation = Evaluation.objects.filter(id=evaluation_id).first()
    if not evaluation:
        return Response({"detail": "Evaluation introuvable."}, status=status.HTTP_404_NOT_FOUND)
    if evaluation.is_closed:
        return Response({"detail": "Évaluation clôturée."}, status=status.HTTP_400_BAD_REQUEST)

    teacher_identity = CoreIdentity.objects.filter(
        email__iexact=getattr(request.user, "email", "")
    ).first()
    scope_code = _get_scope_code(teacher_identity, "USER_TEACHER") if teacher_identity else None

    created = 0
    for item in grades_payload:
        student_uuid = item.get("student_uuid")
        value = item.get("value")
        if not student_uuid or value is None:
            continue
        student = StudentProfile.objects.select_related("current_program", "identity").filter(
            id=student_uuid
        ).first()
        if not student:
            continue
        if scope_code and student.current_program and not student.current_program.code.upper().startswith(scope_code.upper()):
            return Response(
                {"detail": "Scope enseignant non autorisé."},
                status=status.HTTP_403_FORBIDDEN,
            )
        Grade.objects.update_or_create(
            evaluation=evaluation,
            student=student,
            defaults={
                "value": value,
                "teacher": teacher_identity,
            },
        )
        created += 1

    return Response({"detail": "Notes enregistrées.", "count": created}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def courses_endpoint(request: HttpRequest) -> Response:
    """GET /api/courses/?teacher=me : Liste des cours d'un enseignant."""
    role_active = getattr(request, "role_active", None)
    if role_active not in {"USER_TEACHER", "ENSEIGNANT"}:
        return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
    
    teacher_identity = CoreIdentity.objects.filter(
        email__iexact=getattr(request.user, "email", "")
    ).first()
    if not teacher_identity:
        return Response({"detail": "Identité enseignant introuvable."}, status=status.HTTP_404_NOT_FOUND)
    
    # Récupérer les course_id uniques depuis les Grades créés par cet enseignant
    course_ids = (
        Grade.objects.filter(teacher=teacher_identity)
        .values_list("evaluation__course_id", flat=True)
        .distinct()
    )
    
    # Récupérer les TeachingUnits correspondantes (si course_id correspond à TeachingUnit.id)
    courses = []
    for course_id in course_ids:
        try:
            # Essayer de trouver une TeachingUnit avec cet ID
            teaching_unit = TeachingUnit.objects.filter(id=course_id).first()
            if teaching_unit:
                courses.append({
                    "id": str(course_id),
                    "code": teaching_unit.code,
                    "name": teaching_unit.name,
                    "program_code": teaching_unit.program.code if teaching_unit.program else None,
                })
            else:
                # Sinon, créer une entrée générique
                courses.append({
                    "id": str(course_id),
                    "code": f"COURSE-{str(course_id)[:8]}",
                    "name": f"Cours {str(course_id)[:8]}",
                    "program_code": None,
                })
        except Exception:
            continue
    
    return Response({"results": courses}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_update_grades(request: HttpRequest) -> Response:
    """POST /api/grades/bulk-update/ : Mise à jour en masse des notes."""
    role_active = getattr(request, "role_active", None)
    if role_active not in {"USER_TEACHER", "ENSEIGNANT"}:
        return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
    
    payload = request.data if hasattr(request, "data") else {}
    course_id = payload.get("course_id")
    grades_data = payload.get("grades", [])  # [{student_uuid, cc, tp, exam}, ...]
    
    if not course_id or not isinstance(grades_data, list):
        return Response(
            {"detail": "course_id et grades[] requis."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    teacher_identity = CoreIdentity.objects.filter(
        email__iexact=getattr(request.user, "email", "")
    ).first()
    if not teacher_identity:
        return Response({"detail": "Identité enseignant introuvable."}, status=status.HTTP_404_NOT_FOUND)
    
    # Récupérer ou créer les évaluations pour ce cours
    evaluation_cc, _ = Evaluation.objects.get_or_create(
        course_id=course_id,
        type=Evaluation.EvaluationType.CC,
        defaults={"weight": Decimal("0.3"), "max_score": Decimal("20")},
    )
    evaluation_tp, _ = Evaluation.objects.get_or_create(
        course_id=course_id,
        type=Evaluation.EvaluationType.TP,
        defaults={"weight": Decimal("0.2"), "max_score": Decimal("20")},
    )
    evaluation_exam, _ = Evaluation.objects.get_or_create(
        course_id=course_id,
        type=Evaluation.EvaluationType.EXAM,
        defaults={"weight": Decimal("0.5"), "max_score": Decimal("20")},
    )
    
    updated_count = 0
    for item in grades_data:
        student_uuid = item.get("student_uuid")
        if not student_uuid:
            continue
        
        student = StudentProfile.objects.filter(id=student_uuid).first()
        if not student:
            continue
        
        # Mise à jour CC
        if "cc" in item and item["cc"] is not None:
            Grade.objects.update_or_create(
                evaluation=evaluation_cc,
                student=student,
                defaults={"value": Decimal(str(item["cc"])), "teacher": teacher_identity},
            )
        
        # Mise à jour TP
        if "tp" in item and item["tp"] is not None:
            Grade.objects.update_or_create(
                evaluation=evaluation_tp,
                student=student,
                defaults={"value": Decimal(str(item["tp"])), "teacher": teacher_identity},
            )
        
        # Mise à jour Exam
        if "exam" in item and item["exam"] is not None:
            Grade.objects.update_or_create(
                evaluation=evaluation_exam,
                student=student,
                defaults={"value": Decimal(str(item["exam"])), "teacher": teacher_identity},
            )
        
        updated_count += 1
    
    return Response(
        {"detail": f"{updated_count} étudiant(s) mis à jour.", "count": updated_count},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def validate_grades(request: HttpRequest) -> Response:
    role_active = getattr(request, "role_active", None)
    if role_active not in {"VALIDATOR_ACAD", "DOYEN", "RECTEUR", "ADMIN_SI"}:
        return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data if hasattr(request, "data") else {}
    course_id = payload.get("course_id")
    course_ids = payload.get("course_ids")
    student_ids = payload.get("student_ids", [])
    if not course_id and not course_ids:
        return Response(
            {"detail": "course_id ou course_ids requis."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    current_identity = CoreIdentity.objects.filter(
        email__iexact=getattr(request.user, "email", "")
    ).first()

    course_id_list = []
    if course_id:
        course_id_list = [course_id]
    if isinstance(course_ids, list):
        course_id_list.extend(course_ids)

    grades = Grade.objects.select_related(
        "student", "evaluation", "student__current_program"
    ).filter(evaluation__course_id__in=course_id_list)
    if student_ids:
        grades = grades.filter(student_id__in=student_ids)

    if current_identity and grades.filter(student__identity_id=current_identity.id).exists():
        SysAuditLog.objects.create(
            action="SOD_CONFLICT",
            entity_type="COURSE",
            entity_id=course_id_list[0] if course_id_list else course_id,
            actor_email=current_identity.email,
            active_role=role_active or "",
            payload={"reason": "student_in_jury", "course_ids": course_id_list},
        )
        return Response(
            {"detail": "SoD: validation interdite pour soi-même."},
            status=status.HTTP_403_FORBIDDEN,
        )

    evaluations = Evaluation.objects.filter(course_id__in=course_id_list)
    if evaluations.filter(is_closed=True).exists():
        return Response({"detail": "PV déjà clôturé."}, status=status.HTTP_400_BAD_REQUEST)

    student_items: dict[int, list[EvaluationScore]] = {}
    for grade in grades:
        student_items.setdefault(grade.student_id, []).append(
            EvaluationScore(
                component=grade.evaluation.type,
                value=grade.value,
                weight=grade.evaluation.weight,
                max_score=grade.evaluation.max_score,
            )
        )

    processed = 0
    for student_id, items in student_items.items():
        student = grades.filter(student_id=student_id).first()
        if not student:
            continue
        if not student.student.current_program:
            continue
        rules = student.student.current_program.academic_rules_json
        result = UEGradeCalculator.calculate(items, rules)
        registration = (
            RegistrationAdmin.objects.filter(student_id=student_id)
            .order_by("-id")
            .first()
        )
        if not registration:
            continue
        for course in course_id_list:
            RegistrationPedagogical.objects.update_or_create(
                registration_admin=registration,
                teaching_unit=course,
                defaults={
                    "status": RegistrationPedagogical.Status.VALIDATED
                    if result.validated
                    else RegistrationPedagogical.Status.FAILED
                },
            )
            processed += 1

    evaluations.update(is_closed=True)

    SysAuditLog.objects.create(
        action="JURY_VALIDATE",
        entity_type="COURSE",
        entity_id=course_id_list[0] if course_id_list else course_id,
        actor_email=getattr(request.user, "email", ""),
        active_role=role_active or "",
        payload={
            "course_ids": course_id_list,
            "students": student_ids,
            "count": processed,
        },
    )

    return Response(
        {"detail": "PV validé.", "count": processed}, status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def workflows_validate(request: HttpRequest) -> Response:
    role_active = getattr(request, "role_active", None)
    if not role_active:
        return Response({"detail": "Rôle actif requis."}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data if hasattr(request, "data") else {}
    workflow = payload.get("workflow")
    registration_id = payload.get("registration_id")
    if not workflow:
        return Response({"detail": "workflow requis."}, status=status.HTTP_400_BAD_REQUEST)

    if workflow == "JURY_VALIDATION":
        if role_active not in {"VALIDATOR_ACAD", "DOYEN", "RECTEUR", "ADMIN_SI"}:
            return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
    elif workflow == "CERTIFICATE_ISSUE":
        if role_active not in {"SCOLARITE", "ADMIN_SI"}:
            return Response({"detail": "Accès refusé."}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({"detail": "Workflow inconnu."}, status=status.HTTP_400_BAD_REQUEST)

    current_identity = CoreIdentity.objects.filter(
        email__iexact=getattr(request.user, "email", "")
    ).first()
    if registration_id:
        registration = RegistrationAdmin.objects.filter(id=registration_id).first()
        if registration and current_identity and registration.student.identity_id == current_identity.id:
            SysAuditLog.objects.create(
                action="SOD_CONFLICT",
                entity_type="WORKFLOW",
                entity_id=uuid4(),
                actor_email=current_identity.email,
                active_role=role_active or "",
                payload={"reason": "self_validation", "workflow": workflow},
            )
            return Response(
                {"detail": "SoD: validation interdite pour soi-même."},
                status=status.HTTP_403_FORBIDDEN,
            )

    SysAuditLog.objects.create(
        action="WORKFLOW_VALIDATED",
        entity_type="WORKFLOW",
        entity_id=uuid4(),
        actor_email=getattr(request.user, "email", ""),
        active_role=role_active or "",
        payload={"workflow": workflow, "registration_id": registration_id},
    )

    return Response({"detail": "Workflow validé."}, status=status.HTTP_200_OK)
