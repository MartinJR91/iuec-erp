from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academic.models import (
    AcademicYear,
    Evaluation,
    Faculty,
    Program,
    RegistrationAdmin,
    RegistrationPedagogical,
    StudentProfile,
)
from identity.models import CoreIdentity, SysAuditLog


@pytest.mark.django_db
def test_workflow_jury_to_certificate() -> None:
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
    year = AcademicYear.objects.create(code="2024-2025", label="2024-2025", is_active=True)

    student_identity = CoreIdentity.objects.create(
        email="student@example.com",
        phone="90011",
        first_name="Student",
        last_name="Test",
    )
    student_profile = StudentProfile.objects.create(
        identity=student_identity,
        matricule_permanent="M001",
        date_entree=timezone.now().date(),
        current_program=program,
    )
    registration = RegistrationAdmin.objects.create(
        student=student_profile,
        academic_year=year,
        level="L1",
        finance_status="OK",
    )

    teacher_identity = CoreIdentity.objects.create(
        email="teacher@example.com",
        phone="90012",
        first_name="Teacher",
        last_name="Test",
        metadata={"scope_by_role": {"USER_TEACHER": "FASE"}},
    )
    teacher_user = User.objects.create_user(
        username="teacher", email=teacher_identity.email, password="secret"
    )

    course_id = uuid.uuid4()
    evaluation = Evaluation.objects.create(
        course_id=course_id,
        type=Evaluation.EvaluationType.CC,
        weight=Decimal("1"),
        max_score=Decimal("20"),
    )

    client = APIClient()
    client.force_authenticate(user=teacher_user)
    response = client.post(
        "/api/grades/",
        {
            "evaluation_id": str(evaluation.id),
            "grades": [
                {"student_uuid": str(student_profile.id), "value": "12.5"},
            ],
        },
        format="json",
        HTTP_X_ROLE_ACTIVE="USER_TEACHER",
    )
    assert response.status_code == 200

    validator_user = User.objects.create_user(
        username="validator", email="validator@example.com", password="secret"
    )
    client.force_authenticate(user=validator_user)
    response = client.post(
        "/api/grades/validate/",
        {"course_id": str(course_id)},
        format="json",
        HTTP_X_ROLE_ACTIVE="VALIDATOR_ACAD",
    )
    assert response.status_code == 200
    evaluation.refresh_from_db()
    assert evaluation.is_closed is True
    assert RegistrationPedagogical.objects.filter(
        registration=registration, teaching_unit_id=course_id
    ).exists()

    scolarite_user = User.objects.create_user(
        username="scolarite", email="scolarite@example.com", password="secret"
    )
    client.force_authenticate(user=scolarite_user)
    response = client.post(
        "/api/workflows/",
        {"workflow": "CERTIFICATE_ISSUE", "registration_id": str(registration.id)},
        format="json",
        HTTP_X_ROLE_ACTIVE="SCOLARITE",
    )
    assert response.status_code == 200
    assert SysAuditLog.objects.filter(action="WORKFLOW_VALIDATED").exists()
