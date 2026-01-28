from __future__ import annotations

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from identity.models import CoreIdentity, IdentityRoleLink


@api_view(["POST"])
@permission_classes([AllowAny])
def obtain_token(request: Request) -> Response:
    """
    Endpoint de login : POST /api/token/
    Accepte {email, password} et retourne {access, refresh}
    
    Pour la démo, on vérifie juste l'existence de l'email.
    En production, il faudrait vérifier password_hash ou utiliser Keycloak.
    """
    email = request.data.get("email", "").strip().lower()
    password = request.data.get("password", "")

    if not email or not password:
        return Response(
            {"detail": "Email et mot de passe requis."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Chercher l'identité par email
    try:
        identity = CoreIdentity.objects.get(email__iexact=email, is_active=True)
    except CoreIdentity.DoesNotExist:
        return Response(
            {"detail": "Identifiants incorrects."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # TODO: Vérifier password_hash si implémenté
    # Pour la démo, on accepte n'importe quel mot de passe si l'email existe
    # En production, utiliser: check_password(password, identity.password_hash)

    # Récupérer les rôles de l'identité
    role_links = IdentityRoleLink.objects.filter(identity=identity, is_active=True).select_related("role")
    roles = [link.role.code for link in role_links if link.role.is_active]

    if not roles:
        # Pas de rôles actifs, utiliser ADMIN_SI par défaut pour la démo
        roles = ["ADMIN_SI"]

    # Créer ou récupérer un User Django pour SimpleJWT
    user, created = User.objects.get_or_create(
        username=identity.email,
        defaults={"email": identity.email, "is_active": True},
    )
    if not created:
        # Mettre à jour l'email si l'utilisateur existe déjà
        user.email = identity.email
        user.is_active = True
        user.save()

    # Créer les tokens JWT avec claims personnalisés
    refresh = RefreshToken.for_user(user)
    refresh["email"] = identity.email
    refresh["roles"] = roles
    refresh["role_active"] = roles[0] if roles else "ADMIN_SI"

    access = refresh.access_token
    access["email"] = identity.email
    access["roles"] = roles
    access["role_active"] = roles[0] if roles else "ADMIN_SI"

    return Response(
        {
            "access": str(access),
            "refresh": str(refresh),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def regenerate_token(request: Request) -> Response:
    """
    Endpoint pour régénérer un token avec un nouveau rôle actif.
    POST /api/auth/regenerate-token/ avec {role_active: "RECTEUR"}
    """
    role_active = request.data.get("role_active", "").strip()
    
    if not role_active:
        return Response(
            {"detail": "role_active requis."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Récupérer l'utilisateur depuis le token actuel
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return Response(
            {"detail": "Token manquant."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token = auth_header.replace("Bearer ", "", 1).strip()
    
    try:
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken
        
        # Valider le token
        UntypedToken(token)
        
        # Décoder le token pour obtenir l'email
        import jwt
        from django.conf import settings
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        email = decoded.get("email", "")
        
        if not email:
            return Response(
                {"detail": "Token invalide."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Récupérer l'identité et ses rôles
        try:
            identity = CoreIdentity.objects.get(email__iexact=email, is_active=True)
        except CoreIdentity.DoesNotExist:
            return Response(
                {"detail": "Identité introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Vérifier que le rôle demandé est valide pour cet utilisateur
        role_links = IdentityRoleLink.objects.filter(identity=identity, is_active=True).select_related("role")
        user_roles = [link.role.code for link in role_links if link.role.is_active]
        
        if role_active not in user_roles:
            return Response(
                {"detail": f"Rôle '{role_active}' non autorisé pour cet utilisateur."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        # Récupérer ou créer le User Django
        user, _ = User.objects.get_or_create(
            username=identity.email,
            defaults={"email": identity.email, "is_active": True},
        )
        
        # Créer un nouveau token avec le rôle actif mis à jour
        refresh = RefreshToken.for_user(user)
        refresh["email"] = identity.email
        refresh["roles"] = user_roles
        refresh["role_active"] = role_active
        
        access = refresh.access_token
        access["email"] = identity.email
        access["roles"] = user_roles
        access["role_active"] = role_active
        
        return Response(
            {
                "token": str(access),
                "access": str(access),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )
    except (InvalidToken, jwt.InvalidTokenError, Exception) as e:
        return Response(
            {"detail": f"Token invalide: {str(e)}"},
            status=status.HTTP_401_UNAUTHORIZED,
        )
