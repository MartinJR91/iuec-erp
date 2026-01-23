from __future__ import annotations

import uuid

import pytest
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
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

    response = DummySalaryView.as_view()(request)
    assert response.status_code == 403
