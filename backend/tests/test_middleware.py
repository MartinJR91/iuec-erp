"""Tests pour core/middleware.py"""
import json
from unittest.mock import Mock, patch

import jwt
import pytest
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory

from core.middleware import (
    ActiveRoleMiddleware,
    KeycloakJWTMiddleware,
    _decode_jwt_payload,
    _extract_role_from_jwt,
    _read_json_body,
)


@pytest.mark.django_db
class TestDecodeJWT:
    """Tests pour les fonctions utilitaires JWT"""

    def test_decode_jwt_payload_valid(self):
        """Test décodage d'un JWT valide"""
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="test", email="test@iuec.cm")
        refresh = RefreshToken.for_user(user)
        refresh["email"] = "test@iuec.cm"
        refresh["role_active"] = "RECTEUR"
        token = str(refresh.access_token)

        payload = _decode_jwt_payload(token)
        assert payload is not None
        assert payload.get("email") == "test@iuec.cm"
        assert payload.get("role_active") == "RECTEUR"

    def test_decode_jwt_payload_invalid(self):
        """Test avec token invalide"""
        payload = _decode_jwt_payload("invalid.token.here")
        assert payload is None

    def test_extract_role_from_jwt_role_active(self):
        """Test extraction du rôle depuis role_active"""
        payload = {"role_active": "RECTEUR", "email": "test@iuec.cm"}
        role = _extract_role_from_jwt(payload)
        assert role == "RECTEUR"

    def test_extract_role_from_jwt_realm_access(self):
        """Test extraction du rôle depuis realm_access"""
        payload = {
            "realm_access": {"roles": ["RECTEUR", "ADMIN_SI"]},
            "email": "test@iuec.cm",
        }
        role = _extract_role_from_jwt(payload)
        assert role == "RECTEUR"

    def test_extract_role_from_jwt_resource_access(self):
        """Test extraction du rôle depuis resource_access"""
        payload = {
            "resource_access": {
                "client1": {"roles": ["ADMIN_SI"]},
                "client2": {"roles": ["RECTEUR"]},
            },
            "email": "test@iuec.cm",
        }
        role = _extract_role_from_jwt(payload)
        assert role == "ADMIN_SI"

    def test_extract_role_from_jwt_no_role(self):
        """Test sans rôle dans le payload"""
        payload = {"email": "test@iuec.cm"}
        role = _extract_role_from_jwt(payload)
        assert role is None

    def test_read_json_body_valid(self):
        """Test lecture d'un corps JSON valide"""
        request = Mock(spec=HttpRequest)
        request.body = b'{"key": "value"}'
        data = _read_json_body(request)
        assert data == {"key": "value"}

    def test_read_json_body_invalid(self):
        """Test avec JSON invalide"""
        request = Mock(spec=HttpRequest)
        request.body = b"invalid json"
        data = _read_json_body(request)
        assert data == {}

    def test_read_json_body_empty(self):
        """Test avec corps vide"""
        request = Mock(spec=HttpRequest)
        request.body = b""
        data = _read_json_body(request)
        assert data == {}


@pytest.mark.django_db
class TestKeycloakJWTMiddleware:
    """Tests pour KeycloakJWTMiddleware"""

    def test_middleware_jwks_disabled(self):
        """Test avec JWKS désactivé"""
        with patch.object(settings, "KEYCLOAK_JWKS_ENABLED", "0"):
            get_response = Mock(return_value=JsonResponse({}))
            middleware = KeycloakJWTMiddleware(get_response)

            request = RequestFactory().get("/")
            response = middleware(request)

            get_response.assert_called_once()
            assert not hasattr(request, "jwt_payload")

    def test_middleware_no_auth_header(self):
        """Test sans header Authorization"""
        get_response = Mock(return_value=JsonResponse({}))
        middleware = KeycloakJWTMiddleware(get_response)

        request = RequestFactory().get("/")
        response = middleware(request)

        get_response.assert_called_once()
        assert not hasattr(request, "jwt_payload")

    def test_middleware_no_bearer(self):
        """Test avec header Authorization mais sans Bearer"""
        get_response = Mock(return_value=JsonResponse({}))
        middleware = KeycloakJWTMiddleware(get_response)

        request = RequestFactory().get("/", HTTP_AUTHORIZATION="Token abc123")
        response = middleware(request)

        get_response.assert_called_once()

    def test_middleware_empty_token(self):
        """Test avec token vide"""
        get_response = Mock(return_value=JsonResponse({}))
        middleware = KeycloakJWTMiddleware(get_response)

        request = RequestFactory().get("/", HTTP_AUTHORIZATION="Bearer ")
        response = middleware(request)

        assert response.status_code == 401
        assert "Token manquant" in response.content.decode()

    def test_middleware_no_kid(self):
        """Test avec token sans kid (doit passer pour SimpleJWT)"""
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="test", email="test@iuec.cm")
        refresh = RefreshToken.for_user(user)
        token = str(refresh.access_token)

        get_response = Mock(return_value=JsonResponse({}))
        middleware = KeycloakJWTMiddleware(get_response)

        request = RequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        response = middleware(request)

        # Devrait passer car pas de kid
        get_response.assert_called_once()


@pytest.mark.django_db
class TestActiveRoleMiddleware:
    """Tests pour ActiveRoleMiddleware"""

    def test_middleware_x_role_active_header(self):
        """Test avec header X-Role-Active"""
        get_response = Mock(return_value=JsonResponse({}))
        middleware = ActiveRoleMiddleware(get_response)

        request = RequestFactory().get("/", HTTP_X_ROLE_ACTIVE="RECTEUR")
        response = middleware(request)

        assert request.role_active == "RECTEUR"
        get_response.assert_called_once()

    def test_middleware_session_role(self):
        """Test avec rôle dans la session"""
        get_response = Mock(return_value=JsonResponse({}))
        middleware = ActiveRoleMiddleware(get_response)

        request = RequestFactory().get("/")
        request.session = {"role_active": "ADMIN_SI"}
        response = middleware(request)

        assert request.role_active == "ADMIN_SI"
        get_response.assert_called_once()

    def test_middleware_jwt_payload(self):
        """Test avec rôle depuis JWT payload"""
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="test", email="test@iuec.cm")
        refresh = RefreshToken.for_user(user)
        refresh["role_active"] = "RECTEUR"
        token = str(refresh.access_token)

        get_response = Mock(return_value=JsonResponse({}))
        middleware = ActiveRoleMiddleware(get_response)

        request = RequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        # Simuler jwt_payload depuis KeycloakJWTMiddleware
        request.jwt_payload = None
        # Ajouter un mock pour request.session
        from unittest.mock import MagicMock
        request.session = MagicMock()
        request.session.get = MagicMock(return_value=None)
        response = middleware(request)

        # Le middleware devrait extraire le rôle depuis le token
        assert request.role_active == "RECTEUR"
        get_response.assert_called_once()

    def test_middleware_sod_violation(self):
        """Test violation SoD (MANAGER_RH_PAY valide son propre salaire)"""
        get_response = Mock(return_value=JsonResponse({}))
        middleware = ActiveRoleMiddleware(get_response)

        from identity.models import CoreIdentity
        identity = CoreIdentity.objects.create(
            email="manager@iuec.cm",
            phone="690000005",
            first_name="Manager",
            last_name="RH",
            is_active=True,
        )

        request = RequestFactory().post(
            "/api/finance/salary/",
            data=json.dumps(
                {
                    "identity_uuid": str(identity.id),
                    "beneficiary_uuid": str(identity.id),
                }
            ),
            content_type="application/json",
            HTTP_X_ROLE_ACTIVE="MANAGER_RH_PAY",
        )
        from unittest.mock import MagicMock
        request.session = MagicMock()
        request.session.get = MagicMock(return_value=None)
        response = middleware(request)

        assert response.status_code == 403
        assert "SoD" in response.content.decode() or "séparation" in response.content.decode().lower()
        get_response.assert_not_called()

    def test_middleware_sod_no_violation_get(self):
        """Test SoD avec méthode GET (pas de violation)"""
        get_response = Mock(return_value=JsonResponse({}))
        middleware = ActiveRoleMiddleware(get_response)

        request = RequestFactory().get("/api/finance/salary/")
        request.role_active = "MANAGER_RH_PAY"
        from unittest.mock import MagicMock
        request.session = MagicMock()
        request.session.get = MagicMock(return_value=None)
        response = middleware(request)

        get_response.assert_called_once()

    def test_middleware_sod_no_violation_different_uuids(self):
        """Test SoD avec UUID différents (pas de violation)"""
        get_response = Mock(return_value=JsonResponse({}))
        middleware = ActiveRoleMiddleware(get_response)

        from identity.models import CoreIdentity
        identity1 = CoreIdentity.objects.create(
            email="manager1@iuec.cm",
            phone="690000006",
            first_name="Manager",
            last_name="1",
            is_active=True,
        )
        identity2 = CoreIdentity.objects.create(
            email="manager2@iuec.cm",
            phone="690000007",
            first_name="Manager",
            last_name="2",
            is_active=True,
        )

        request = RequestFactory().post(
            "/api/finance/salary/",
            data=json.dumps(
                {
                    "identity_uuid": str(identity1.id),
                    "beneficiary_uuid": str(identity2.id),
                }
            ),
            content_type="application/json",
        )
        request.role_active = "MANAGER_RH_PAY"
        from unittest.mock import MagicMock
        request.session = MagicMock()
        request.session.get = MagicMock(return_value=None)
        response = middleware(request)

        get_response.assert_called_once()
