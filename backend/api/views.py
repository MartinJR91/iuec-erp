from __future__ import annotations

from datetime import datetime, timedelta

from django.db.models import Count, Q
from django.http import HttpRequest
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from identity.models import CoreIdentity, IdentityRoleLink


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_data(request: HttpRequest) -> Response:
    """
    Endpoint pour récupérer les données du dashboard selon le rôle actif.
    GET /api/dashboard/?role=RECTEUR (optionnel, utilise request.role_active par défaut)
    """
    # Récupérer le rôle depuis query param ou request.role_active (injecté par middleware)
    role = request.GET.get("role") or getattr(request, "role_active", None)

    if not role:
        return Response(
            {"detail": "Rôle actif requis. Fournissez ?role=XXX ou header X-Role-Active."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Vérifier que l'utilisateur a bien ce rôle
    if request.user.is_authenticated:
        try:
            identity = CoreIdentity.objects.get(email__iexact=request.user.email, is_active=True)
            user_roles = list(
                IdentityRoleLink.objects.filter(identity=identity, is_active=True)
                .values_list("role__code", flat=True)
            )
            if role not in user_roles:
                return Response(
                    {"detail": f"Rôle '{role}' non autorisé pour cet utilisateur."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except CoreIdentity.DoesNotExist:
            return Response(
                {"detail": "Identité introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

    # Générer les données selon le rôle
    data: dict = {}

    if role in ("RECTEUR", "DAF", "SG", "VIEWER_STRATEGIC"):
        # Dashboard institutionnel : KPI + graphique évolution
        total_students = CoreIdentity.objects.filter(
            identityrolelink__role__code="USER_STUDENT",
            identityrolelink__is_active=True,
            is_active=True,
        ).distinct().count()

        # Mock revenue (à remplacer par vraie query sur Invoice)
        monthly_revenue = "45 000 000 XAF"

        # Mock SoD alerts (à remplacer par vraie query sur audit log)
        sod_alerts = 2

        # Mock attendance rate
        attendance_rate = 92

        # Graphique évolution inscriptions (mock, à remplacer par vraie query)
        enrollment_evolution = [
            {"month": "Jan 2025", "value": 1100},
            {"month": "Fév 2025", "value": 1150},
            {"month": "Mar 2025", "value": 1180},
            {"month": "Avr 2025", "value": 1200},
            {"month": "Mai 2025", "value": 1220},
            {"month": "Juin 2025", "value": 1200},
            {"month": "Jan 2026", "value": total_students or 1245},
        ]

        data = {
            "kpis": {
                "studentsCount": total_students or 1245,
                "monthlyRevenue": monthly_revenue,
                "sodAlerts": sod_alerts,
                "attendanceRate": attendance_rate,
            },
            "graph": enrollment_evolution,
        }

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
            identity = CoreIdentity.objects.get(email__iexact=request.user.email, is_active=True)
        except CoreIdentity.DoesNotExist:
            identity = None

        # Mock grades (à remplacer par vraie query sur GradeEntry)
        grades = [
            {"ueCode": "UE_MATH", "average": 14.5, "status": "Validée"},
            {"ueCode": "UE_PHYS", "average": 11.2, "status": "Validée"},
            {"ueCode": "UE_INFO", "average": 8.5, "status": "Ajourné"},
            {"ueCode": "UE_STAT", "average": 12.8, "status": "Validée"},
        ]

        # Mock balance (à remplacer par vraie query sur Invoice)
        balance = 150000

        data = {
            "grades": grades,
            "balance": balance,
        }

    elif role == "OPERATOR_FINANCE":
        # Dashboard finance : factures impayées
        # Mock invoices (à remplacer par vraie query sur Invoice)
        unpaid_invoices = [
            {"student": "KONE Salif", "amount": 250000, "dueDate": "2026-02-15"},
            {"student": "DIAKITE Amadou", "amount": 180000, "dueDate": "2026-02-10"},
            {"student": "TRAORE Fatou", "amount": 320000, "dueDate": "2026-02-20"},
            {"student": "SANGARE Mariam", "amount": 150000, "dueDate": "2026-02-05"},
            {"student": "COULIBALY Ibrahim", "amount": 280000, "dueDate": "2026-02-12"},
        ]

        total_pending = sum(inv["amount"] for inv in unpaid_invoices)

        data = {
            "unpaidInvoices": unpaid_invoices,
            "totalPending": total_pending,
        }

    else:
        # Rôle non géré
        data = {"message": f"Dashboard non disponible pour le rôle '{role}'."}

    return Response(data, status=status.HTTP_200_OK)
