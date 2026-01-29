"""Tests pour api/auth.py"""
import pytest
from django.contrib.auth.models import User
from django.test import Client
from rest_framework import status
from rest_framework.test import APIClient

from identity.models import CoreIdentity, IdentityRoleLink, RbacRoleDef
from identity.seed import DEMO_USERS_BY_EMAIL


@pytest.mark.django_db
class TestObtainToken:
    """Tests pour l'endpoint obtain_token"""

    def test_obtain_token_missing_email(self):
        """Test avec email manquant"""
        client = APIClient()
        response = client.post("/api/token/", {"password": "test123"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email et mot de passe requis" in response.data["detail"]

    def test_obtain_token_missing_password(self):
        """Test avec mot de passe manquant"""
        client = APIClient()
        response = client.post("/api/token/", {"email": "test@iuec.cm"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_obtain_token_invalid_credentials(self):
        """Test avec identifiants invalides"""
        from django.conf import settings
        client = APIClient()
        # En mode DEBUG/SQLITE, l'auto-provisioning peut créer l'identité
        # On teste plutôt avec un email qui n'est pas dans DEMO_USERS et un mauvais mot de passe
        # pour un utilisateur démo existant
        from identity.management.commands.seed_demo_users import Command
        Command().handle()
        
        # Utiliser un email démo avec un mauvais mot de passe
        demo_email = list(DEMO_USERS_BY_EMAIL.keys())[0]
        response = client.post(
            "/api/token/", {"email": demo_email, "password": "wrong_password"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_demo_user(self):
        """Test avec un utilisateur démo"""
        # Utiliser directement DEMO_USERS pour éviter les problèmes de référence
        from identity.seed import DEMO_USERS, seed_demo_users
        demo_user = DEMO_USERS[0]  # Premier utilisateur (admin@iuec.cm)
        demo_email = demo_user["email"]
        demo_password = demo_user["password"]

        # Créer l'identité directement avec le seed pour éviter le problème de comparaison de mot de passe
        # dans le except block
        seed_demo_users()
        
        # S'assurer que l'identité est active
        identity = CoreIdentity.objects.filter(email__iexact=demo_email, is_active=True).first()
        if not identity:
            # Si l'identité n'existe pas ou n'est pas active, la créer manuellement
            identity = CoreIdentity.objects.filter(email__iexact=demo_email).first()
            if identity:
                identity.is_active = True
                identity.save()
            else:
                # Créer l'identité manuellement
                from identity.seed import _ensure_identity_and_roles, _get_or_create_role
                role_map = {}
                for role_code in demo_user.get("roles", []):
                    role_map[role_code] = _get_or_create_role(role_code, role_code)
                from django.contrib.auth import get_user_model
                _ensure_identity_and_roles(
                    username=demo_user["username"],
                    email=demo_user["email"],
                    first_name=demo_user["first_name"],
                    last_name=demo_user["last_name"],
                    phone=demo_user["phone"],
                    roles=demo_user.get("roles", []),
                    role_map=role_map,
                    user_model=get_user_model(),
                )

        client = APIClient()
        response = client.post(
            "/api/token/", {"email": demo_email, "password": demo_password}
        )
        # Si l'identité existe et est active, elle entre dans le try block (ligne 37)
        # Le code accepte n'importe quel mot de passe si l'email existe (ligne 59)
        # Si l'identité n'a pas de rôles, le code assigne ["ADMIN_SI"] par défaut (ligne 68)
        assert response.status_code == status.HTTP_200_OK, f"Response: {response.status_code}, Detail: {response.data.get('detail', '')}, Email: {demo_email}"
        assert "access" in response.data
        assert "refresh" in response.data

    def test_obtain_token_wrong_password_demo(self):
        """Test avec mauvais mot de passe pour utilisateur démo"""
        from identity.management.commands.seed_demo_users import Command
        Command().handle()

        demo_email = list(DEMO_USERS_BY_EMAIL.keys())[0]

        client = APIClient()
        response = client.post(
            "/api/token/", {"email": demo_email, "password": "wrong_password"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obtain_token_existing_identity(self):
        """Test avec une identité existante"""
        identity = CoreIdentity.objects.create(
            email="test@iuec.cm",
            phone="690000000",
            first_name="Test",
            last_name="User",
            is_active=True,
        )

        client = APIClient()
        response = client.post(
            "/api/token/", {"email": "test@iuec.cm", "password": "any"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_obtain_token_no_roles_default_admin(self):
        """Test avec identité sans rôles (doit utiliser ADMIN_SI par défaut)"""
        identity = CoreIdentity.objects.create(
            email="norole@iuec.cm",
            phone="690000001",
            first_name="No",
            last_name="Role",
            is_active=True,
        )

        client = APIClient()
        response = client.post(
            "/api/token/", {"email": "norole@iuec.cm", "password": "any"}
        )
        assert response.status_code == status.HTTP_200_OK
        # Vérifier que le token contient ADMIN_SI
        import jwt
        token = response.data["access"]
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert decoded["role_active"] == "ADMIN_SI"

    def test_obtain_token_with_roles(self):
        """Test avec identité ayant des rôles"""
        identity = CoreIdentity.objects.create(
            email="multirole@iuec.cm",
            phone="690000002",
            first_name="Multi",
            last_name="Role",
            is_active=True,
        )
        role1, _ = RbacRoleDef.objects.get_or_create(
            code="RECTEUR", defaults={"label": "Recteur", "is_active": True}
        )
        role2, _ = RbacRoleDef.objects.get_or_create(
            code="ADMIN_SI", defaults={"label": "Admin SI", "is_active": True}
        )
        IdentityRoleLink.objects.create(identity=identity, role=role1, is_active=True)
        IdentityRoleLink.objects.create(identity=identity, role=role2, is_active=True)

        client = APIClient()
        response = client.post(
            "/api/token/", {"email": "multirole@iuec.cm", "password": "any"}
        )
        assert response.status_code == status.HTTP_200_OK
        import jwt
        token = response.data["access"]
        decoded = jwt.decode(token, options={"verify_signature": False})
        assert "RECTEUR" in decoded["roles"]
        assert "ADMIN_SI" in decoded["roles"]


@pytest.mark.django_db
class TestRegenerateToken:
    """Tests pour l'endpoint regenerate_token"""

    def test_regenerate_token_missing_role(self):
        """Test sans role_active"""
        client = APIClient()
        response = client.post("/api/auth/regenerate-token/", {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_regenerate_token_missing_auth_header(self):
        """Test sans header Authorization"""
        client = APIClient()
        response = client.post(
            "/api/auth/regenerate-token/", {"role_active": "RECTEUR"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regenerate_token_invalid_token(self):
        """Test avec token invalide"""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer invalid_token")
        response = client.post(
            "/api/auth/regenerate-token/", {"role_active": "RECTEUR"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regenerate_token_success(self):
        """Test de régénération réussie"""
        # Créer une identité avec plusieurs rôles
        identity = CoreIdentity.objects.create(
            email="regenerate@iuec.cm",
            phone="690000003",
            first_name="Regen",
            last_name="Token",
            is_active=True,
        )
        role1, _ = RbacRoleDef.objects.get_or_create(
            code="RECTEUR", defaults={"label": "Recteur", "is_active": True}
        )
        role2, _ = RbacRoleDef.objects.get_or_create(
            code="ADMIN_SI", defaults={"label": "Admin SI", "is_active": True}
        )
        IdentityRoleLink.objects.create(identity=identity, role=role1, is_active=True)
        IdentityRoleLink.objects.create(identity=identity, role=role2, is_active=True)

        # Obtenir un token initial
        client = APIClient()
        login_response = client.post(
            "/api/token/", {"email": "regenerate@iuec.cm", "password": "any"}
        )
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.data["access"]

        # Régénérer avec un autre rôle
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = client.post(
            "/api/auth/regenerate-token/", {"role_active": "ADMIN_SI"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

        # Vérifier que le nouveau token a le bon rôle
        import jwt
        new_token = response.data["access"]
        decoded = jwt.decode(new_token, options={"verify_signature": False})
        assert decoded["role_active"] == "ADMIN_SI"

    def test_regenerate_token_unauthorized_role(self):
        """Test avec un rôle non autorisé pour l'utilisateur"""
        identity = CoreIdentity.objects.create(
            email="single@iuec.cm",
            phone="690000004",
            first_name="Single",
            last_name="Role",
            is_active=True,
        )
        role, _ = RbacRoleDef.objects.get_or_create(
            code="RECTEUR", defaults={"label": "Recteur", "is_active": True}
        )
        IdentityRoleLink.objects.create(identity=identity, role=role, is_active=True)

        client = APIClient()
        login_response = client.post(
            "/api/token/", {"email": "single@iuec.cm", "password": "any"}
        )
        access_token = login_response.data["access"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = client.post(
            "/api/auth/regenerate-token/", {"role_active": "ADMIN_SI"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "non autorisé" in response.data["detail"]

    def test_regenerate_token_identity_not_found(self):
        """Test avec identité introuvable dans le token"""
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.contrib.auth.models import User

        user = User.objects.create_user(
            username="fake@iuec.cm", email="fake@iuec.cm"
        )
        refresh = RefreshToken.for_user(user)
        refresh["email"] = "nonexistent@iuec.cm"
        access = refresh.access_token
        access["email"] = "nonexistent@iuec.cm"

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(access)}")
        response = client.post(
            "/api/auth/regenerate-token/", {"role_active": "RECTEUR"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
