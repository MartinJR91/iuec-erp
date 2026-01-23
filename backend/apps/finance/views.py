from __future__ import annotations

from django.http import JsonResponse
from django.views import View


class FinanceHealthView(View):
    def get(self, request) -> JsonResponse:  # type: ignore[override]
        return JsonResponse({"status": "ok"})
