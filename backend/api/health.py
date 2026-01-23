from __future__ import annotations

from django import get_version
from django.db import connection
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    db_status = "ok"
    try:
        connection.ensure_connection()
    except Exception:
        db_status = "error"
    return Response(
        {
            "status": "healthy",
            "db": db_status,
            "django": get_version(),
            "timestamp": timezone.now().isoformat(),
        },
        status=200,
    )
