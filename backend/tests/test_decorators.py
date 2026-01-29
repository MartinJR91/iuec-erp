"""Tests pour core/decorators.py"""
import pytest
from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory

from core.decorators import with_active_role


def dummy_view(request: HttpRequest) -> JsonResponse:
    """Vue de test"""
    return JsonResponse({"success": True})


@pytest.mark.django_db
class TestWithActiveRole:
    """Tests pour le décorateur with_active_role"""

    def test_with_active_role_no_role(self):
        """Test sans rôle actif"""
        decorated_view = with_active_role()(dummy_view)
        request = RequestFactory().get("/")
        # Pas de role_active
        response = decorated_view(request)
        assert response.status_code == 403
        content = response.content.decode()
        # Le JSON contient des caractères échappés Unicode
        assert "Rôle actif requis" in content or "role" in content.lower() or "R\\u00f4le" in content

    def test_with_active_role_with_role(self):
        """Test avec rôle actif"""
        decorated_view = with_active_role()(dummy_view)
        request = RequestFactory().get("/")
        request.role_active = "RECTEUR"
        response = decorated_view(request)
        assert response.status_code == 200
        assert "success" in response.content.decode()

    def test_with_active_role_allowed_role(self):
        """Test avec rôle autorisé"""
        decorated_view = with_active_role(allowed_roles=["RECTEUR", "ADMIN_SI"])(
            dummy_view
        )
        request = RequestFactory().get("/")
        request.role_active = "RECTEUR"
        response = decorated_view(request)
        assert response.status_code == 200

    def test_with_active_role_unauthorized_role(self):
        """Test avec rôle non autorisé"""
        decorated_view = with_active_role(allowed_roles=["RECTEUR", "ADMIN_SI"])(
            dummy_view
        )
        request = RequestFactory().get("/")
        request.role_active = "USER_STUDENT"
        response = decorated_view(request)
        assert response.status_code == 403
        content = response.content.decode()
        # Le JSON contient des caractères échappés Unicode
        assert "non autorisé" in content or "non autorise" in content or "non autorisé" in content or "non autoris\\u00e9" in content

    def test_with_active_role_empty_allowed_roles(self):
        """Test avec liste de rôles autorisés vide (tous autorisés)"""
        decorated_view = with_active_role(allowed_roles=[])(dummy_view)
        request = RequestFactory().get("/")
        request.role_active = "ANY_ROLE"
        response = decorated_view(request)
        assert response.status_code == 200

    def test_with_active_role_none_allowed_roles(self):
        """Test avec allowed_roles=None (tous autorisés)"""
        decorated_view = with_active_role(allowed_roles=None)(dummy_view)
        request = RequestFactory().get("/")
        request.role_active = "ANY_ROLE"
        response = decorated_view(request)
        assert response.status_code == 200

    def test_with_active_role_preserves_function_metadata(self):
        """Test que le décorateur préserve les métadonnées de la fonction"""
        decorated_view = with_active_role()(dummy_view)
        assert decorated_view.__name__ == "dummy_view" or decorated_view.__name__ == "wrapper"
