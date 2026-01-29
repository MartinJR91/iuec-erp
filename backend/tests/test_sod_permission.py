from __future__ import annotations

import uuid

import pytest
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from api.permissions import SoDPermission


class DummySalaryView(APIView):
    permission_classes = (SoDPermission,)

    def post(self, request, *args, **kwargs):
        return Response({"status": "ok"})


@pytest.mark.django_db
def test_sod_violation_returns_403() -> None:
    factory = APIRequestFactory()
    payload = {
        "identity_uuid": str(uuid.uuid4()),
        "beneficiary_uuid": "same-uuid",
    }
    payload["identity_uuid"] = payload["beneficiary_uuid"]
    request = factory.post("/api/salary/validate/", payload, format="json")
    request.role_active = "MANAGER_RH_PAY"
    user = User.objects.create_user(username="sod-user", password="secret")
    force_authenticate(request, user=user)

    response = DummySalaryView.as_view()(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_sod_rh_pay_auto_salary_blocked() -> None:
    factory = APIRequestFactory()
    payload = {
        "identity_uuid": str(uuid.uuid4()),
        "beneficiary_uuid": "same-uuid",
    }
    payload["identity_uuid"] = payload["beneficiary_uuid"]
    request = factory.post("/api/rh-pay/validate/", payload, format="json")
    request.role_active = "MANAGER_RH_PAY"
    user = User.objects.create_user(username="sod-user-2", password="secret")
    force_authenticate(request, user=user)

    response = DummySalaryView.as_view()(request)
    assert response.status_code == 403