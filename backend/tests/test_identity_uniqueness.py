from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError

from identity.models import CoreIdentity


@pytest.mark.django_db
def test_core_identity_unique_email() -> None:
    CoreIdentity.objects.create(
        id=uuid.uuid4(),
        email="test@example.com",
        phone="12345",
        first_name="Test",
        last_name="User",
    )
    with pytest.raises(IntegrityError):
        CoreIdentity.objects.create(
            id=uuid.uuid4(),
            email="test@example.com",
            phone="67890",
            first_name="Test2",
            last_name="User2",
        )


@pytest.mark.django_db
def test_core_identity_unique_phone() -> None:
    CoreIdentity.objects.create(
        id=uuid.uuid4(),
        email="test2@example.com",
        phone="11111",
        first_name="Test",
        last_name="User",
    )
    with pytest.raises(IntegrityError):
        CoreIdentity.objects.create(
            id=uuid.uuid4(),
            email="test3@example.com",
            phone="11111",
            first_name="Test3",
            last_name="User3",
        )
