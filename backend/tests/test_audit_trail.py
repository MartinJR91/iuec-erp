from __future__ import annotations

import uuid

import pytest

from identity.models import SysAuditLog


@pytest.mark.django_db
def test_audit_trail_records_active_role() -> None:
    entry = SysAuditLog.objects.create(
        id=uuid.uuid4(),
        action="SALARY_VALIDATE",
        entity_type="FINANCE_SALARY",
        entity_id=uuid.uuid4(),
        actor_email="manager@example.com",
        active_role="MANAGER_RH_PAY",
        payload={"note": "auto-validation"},
    )
    assert entry.active_role == "MANAGER_RH_PAY"
