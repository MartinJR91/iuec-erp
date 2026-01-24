from __future__ import annotations

import base64
import json
import time
from typing import Any, Dict, Optional, Tuple

import jwt
from django.conf import settings
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
    role_active = payload.get("role_active")
    if isinstance(role_active, str) and role_active:
        return role_active
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


def _keycloak_openid() -> Optional[object]:
    try:
        from keycloak import KeycloakOpenID  # type: ignore
    except ImportError:
        return None

    config = settings.KEYCLOAK_CONFIG
    return KeycloakOpenID(
        server_url=config["server_url"],
        realm_name=config["realm"],
        client_id=config["client_id"],
    )


def _jwks_cache_key() -> Tuple[str, str, str]:
    config = settings.KEYCLOAK_CONFIG
    return (
        config["server_url"],
        config["realm"],
        config["client_id"],
    )


class KeycloakJWTMiddleware:
    """Valide le JWT via JWKS Keycloak avant traitement des vues."""

    _jwks_cache: Dict[Tuple[str, str, str], Tuple[float, Dict[str, Any]]] = {}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if str(getattr(settings, "KEYCLOAK_JWKS_ENABLED", "1")) != "1":
            return self.get_response(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return self.get_response(request)

        token = auth_header.replace("Bearer ", "", 1).strip()
        if not token:
            return self._unauthorized("Token manquant.")

        try:
            payload = self._validate_token(token)
        except jwt.PyJWTError:
            return self._unauthorized("Token invalide.")

        request.jwt_payload = payload
        return self.get_response(request)

    def _validate_token(self, token: str) -> Dict[str, Any]:
        jwks = self._get_jwks()
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise jwt.InvalidTokenError("kid manquant")

        keys = jwks.get("keys", [])
        matching = next((key for key in keys if key.get("kid") == kid), None)
        if not matching:
            raise jwt.InvalidTokenError("kid inconnu")

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(matching))
        config = settings.KEYCLOAK_CONFIG
        return jwt.decode(
            token,
            key=public_key,
            algorithms=config.get("jwt_algorithms", ["RS256"]),
            audience=config.get("audience"),
            issuer=config.get("issuer_url"),
            options={"verify_signature": True, "verify_exp": True},
        )

    def _get_jwks(self) -> Dict[str, Any]:
        config = settings.KEYCLOAK_CONFIG
        cache_key = _jwks_cache_key()
        now = time.time()
        cached = self._jwks_cache.get(cache_key)
        if cached:
            cached_at, payload = cached
            if now - cached_at < config.get("jwks_cache_seconds", 300):
                return payload

        openid = _keycloak_openid()
        if not openid:
            raise jwt.InvalidTokenError("Keycloak non disponible")
        jwks = openid.certs()
        self._jwks_cache[cache_key] = (now, jwks)
        return jwks

    @staticmethod
    def _unauthorized(detail: str) -> JsonResponse:
        return JsonResponse({"detail": detail}, status=401)


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
                payload = getattr(request, "jwt_payload", None) or _decode_jwt_payload(token)
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
