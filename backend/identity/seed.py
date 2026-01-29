from __future__ import annotations

from typing import Iterable

from django.contrib.auth import get_user_model
from django.db import transaction

from identity.models import CoreIdentity, IdentityRoleLink, RbacRoleDef


DEMO_USERS = [
    {
        "username": "admin",
        "email": "admin@iuec.cm",
        "password": "admin123!",
        "first_name": "Admin",
        "last_name": "IUEC",
        "phone": "690000000",
        "roles": ("RECTEUR", "USER_TEACHER", "VIEWER_STRATEGIC"),
    },
    {
        "username": "u.recteur",
        "email": "recteur@iuec.cm",
        "password": "recteur123!",
        "first_name": "Recteur",
        "last_name": "KAMGA",
        "phone": "690000001",
        "roles": ("RECTEUR", "USER_TEACHER", "VIEWER_STRATEGIC", "VALIDATOR_ACAD"),
        "scope_by_role": {"VALIDATOR_ACAD": "FASE"},
    },
    {
        "username": "enseignant.dupont",
        "email": "marie.dupont@iuec.cm",
        "password": "ens123!",
        "first_name": "Marie",
        "last_name": "Dupont",
        "phone": "690000002",
        "roles": ("USER_TEACHER",),
        "scope_by_role": {"USER_TEACHER": "FST"},
    },
    {
        "username": "etudiant.ngono",
        "email": "elise.ngono@iuec.cm",
        "password": "etu123!",
        "first_name": "Elise",
        "last_name": "Ngono",
        "phone": "690000003",
        "roles": ("USER_STUDENT",),
    },
    {
        "username": "finance.op",
        "email": "finance@iuec.cm",
        "password": "fin123!",
        "first_name": "Finance",
        "last_name": "Op",
        "phone": "690000004",
        "roles": ("OPERATOR_FINANCE",),
    },
    {
        "username": "doyen.fase",
        "email": "doyen@iuec.cm",
        "password": "doyen123!",
        "first_name": "Doyen",
        "last_name": "FASE",
        "phone": "690000006",
        "roles": ("DOYEN", "VALIDATOR_ACAD"),
        "scope_by_role": {"DOYEN": "FASE", "VALIDATOR_ACAD": "FASE"},
    },
    {
        "username": "scolarite.op",
        "email": "scolarite@iuec.cm",
        "password": "scol123!",
        "first_name": "Scolarité",
        "last_name": "Op",
        "phone": "690000007",
        "roles": ("SCOLARITE", "OPERATOR_SCOLA"),
    },
]

DEMO_USERS_BY_EMAIL = {user["email"]: user for user in DEMO_USERS}


def seed_demo_users() -> None:
    user_model = get_user_model()

    roles = [
        ("RECTEUR", "Recteur"),
        ("USER_TEACHER", "Enseignant"),
        ("VIEWER_STRATEGIC", "Viewer Strategic"),
        ("USER_STUDENT", "Etudiant"),
        ("OPERATOR_FINANCE", "Opérateur Finance"),
        ("OPERATOR_SCOLA", "Opérateur Scolarité"),
        ("DOYEN", "Doyen"),
        ("VALIDATOR_ACAD", "Validateur Académique"),
        ("ADMIN_SI", "Administrateur SI"),
        ("SCOLARITE", "Scolarité"),
    ]
    role_map = {code: _get_or_create_role(code, label) for code, label in roles}

    with transaction.atomic():
        _ensure_superuser(
            user_model,
            username=DEMO_USERS_BY_EMAIL["admin@iuec.cm"]["username"],
            email="admin@iuec.cm",
            password=DEMO_USERS_BY_EMAIL["admin@iuec.cm"]["password"],
        )

        for user in DEMO_USERS:
            if user["email"] == "admin@iuec.cm":
                continue
            scope_by_role = user.get("scope_by_role", None)
            _ensure_identity_and_roles(
                username=user["username"],
                email=user["email"],
                first_name=user["first_name"],
                last_name=user["last_name"],
                phone=user["phone"],
                roles=user["roles"],
                role_map=role_map,
                user_model=user_model,
                scope_by_role=scope_by_role,
            )


def _get_or_create_role(code: str, label: str) -> RbacRoleDef:
    role, _ = RbacRoleDef.objects.get_or_create(
        code=code,
        defaults={"label": label, "description": label, "permissions": {}},
    )
    return role


def _ensure_superuser(
    user_model, *, username: str, email: str, password: str
) -> None:
    if not user_model.objects.filter(username=username).exists():
        user_model.objects.create_superuser(
            username=username, email=email, password=password
        )


def _ensure_identity_and_roles(
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    phone: str,
    roles: Iterable[str],
    role_map: dict[str, RbacRoleDef],
    user_model,
    scope_by_role: dict | None = None,
) -> None:
    user, _ = user_model.objects.get_or_create(
        username=username, defaults={"email": email}
    )
    if not user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])

    metadata = {}
    if scope_by_role:
        metadata["scope_by_role"] = scope_by_role
    else:
        metadata["scope"] = "FASE"  # Par défaut

    identity, _ = CoreIdentity.objects.get_or_create(
        email=email,
        defaults={
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "metadata": metadata,
        },
    )
    # Mettre à jour le metadata si scope_by_role est fourni
    if scope_by_role and identity.metadata.get("scope_by_role") != scope_by_role:
        identity.metadata = metadata
        identity.save(update_fields=["metadata"])
    # Mettre à jour le téléphone seulement s'il est différent et disponible
    if identity.phone != phone:
        # Vérifier si le numéro est déjà utilisé par une autre identité
        existing = CoreIdentity.objects.filter(phone=phone).exclude(id=identity.id).first()
        if not existing:
            identity.phone = phone
            identity.save(update_fields=["phone"])

    for role_code in roles:
        role = role_map[role_code]
        IdentityRoleLink.objects.get_or_create(
            identity=identity, role=role, defaults={"assigned_by": "seed"}
        )
