from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional

from django.http import HttpRequest, JsonResponse


def _decode_jwt_payload(token: str) -> Optional[Dict[str, Any]]:
    """Décoder un JWT sans vérification de signature (lecture-only)."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None


def _extract_role_from_jwt(payload: Dict[str, Any]) -> Optional[str]:
    """Extraire le rôle actif depuis un token Keycloak."""
    realm_access = payload.get("realm_access", {})
    roles = realm_access.get("roles")
    if isinstance(roles, list) and roles:
        return str(roles[0])
    resource_access = payload.get("resource_access", {})
    if isinstance(resource_access, dict):
        for client in resource_access.values():
            if isinstance(client, dict):
                client_roles = client.get("roles")
                if isinstance(client_roles, list) and client_roles:
                    return str(client_roles[0])
    return None


def _read_json_body(request: HttpRequest) -> Dict[str, Any]:
    """Lire un corps JSON sans lever d’exception."""
    try:
        if request.body:
            return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return {}


class ActiveRoleMiddleware:
    """Middleware pour injecter request.role_active et appliquer SoD."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        role_active = None

        header_role = request.headers.get("X-Role-Active")
        if header_role:
            role_active = header_role.strip()

        if not role_active:
            session_role = request.session.get("role_active")
            if isinstance(session_role, str) and session_role.strip():
                role_active = session_role.strip()

        if not role_active:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "", 1).strip()
                payload = _decode_jwt_payload(token)
                if payload:
                    role_active = _extract_role_from_jwt(payload)

        request.role_active = role_active

        if self._is_sod_violation(request):
            return JsonResponse(
                {"detail": "Action interdite par séparation des tâches (SoD)."},
                status=403,
            )

        return self.get_response(request)

    def _is_sod_violation(self, request: HttpRequest) -> bool:
        """Bloquer si un manager valide sa propre opération sensible."""
        if request.method not in {"POST", "PUT", "PATCH"}:
            return False
        if request.role_active != "MANAGER_RH_PAY":
            return False

        data = _read_json_body(request)
        identity_uuid = data.get("identity_uuid") or request.GET.get("identity_uuid")
        beneficiary_uuid = data.get("beneficiary_uuid") or request.GET.get(
            "beneficiary_uuid"
        )
        if identity_uuid and beneficiary_uuid:
            return str(identity_uuid) == str(beneficiary_uuid)
        return False
