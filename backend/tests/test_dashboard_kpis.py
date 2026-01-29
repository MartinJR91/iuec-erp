from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academic.models import Faculty, Program, StudentProfile
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, SysAuditLog


@pytest.mark.django_db
def test_recteur_dashboard_kpis() -> None:
    faculty = Faculty.objects.create(code="FASE", name="Faculté", tutelle="MINESUP")
    program = Program.objects.create(
        code="FASE_ING",
        name="FASE Ingénierie",
        faculty=faculty,
        academic_rules_json={
            "grading_system": {"min_validate": 10, "compensation": True},
            "financial_rules": {},
        },
    )
    identity = CoreIdentity.objects.create(
        email="student-kpi@example.com",
        phone="90021",
        first_name="Student",
        last_name="KPI",
    )
    StudentProfile.objects.create(
        identity=identity,
        matricule_permanent="KPI001",
        date_entree=timezone.now().date(),
        current_program=program,
    )

    invoice = Invoice.objects.create(
        identity_uuid=identity.id,
        program_code=program.code,
        status=Invoice.STATUS_PAID,
        line_items=[{"code": "SCOLARITE", "label": "Scolarité", "amount": "100000"}],
        issue_date=timezone.now().date(),
    )
    Payment.objects.create(
        invoice=invoice, amount=Decimal("100000"), method=Payment.METHOD_CASH
    )

    user = User.objects.create_user(username="recteur", password="secret")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/dashboard/?role=RECTEUR", HTTP_X_ROLE_ACTIVE="RECTEUR")
    assert response.status_code == 200
    payload = response.json()
    assert payload["kpis"]["studentsCount"] >= 1
    assert "monthlyRevenue" in payload["kpis"]
    assert payload["kpis"]["studentsByFaculty"][0]["facultyCode"] == "FASE"
    assert payload["graph"]
    assert SysAuditLog.objects.filter(action="KPI_ACCESS").exists()
