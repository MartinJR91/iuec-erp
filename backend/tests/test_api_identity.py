from __future__ import annotations

import uuid

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from identity.models import CoreIdentity


@pytest.mark.django_db
def test_api_identity_list_authenticated() -> None:
    CoreIdentity.objects.create(
        id=uuid.uuid4(),
        email="api@example.com",
        phone="90001",
        first_name="Api",
        last_name="User",
    )
    user = User.objects.create_user(username="tester", password="secret")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/identities/", HTTP_X_ROLE_ACTIVE="RECTEUR")
    assert response.status_code == 200
