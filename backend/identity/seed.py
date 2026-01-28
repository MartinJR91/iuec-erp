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
        "last_name": "IUEC",
        "phone": "690000001",
        "roles": ("RECTEUR", "USER_TEACHER", "VIEWER_STRATEGIC"),
    },
    {
        "username": "u.ens",
        "email": "ens@iuec.cm",
        "password": "enseignant123!",
        "first_name": "Enseignant",
        "last_name": "IUEC",
        "phone": "690000002",
        "roles": ("USER_TEACHER",),
    },
    {
        "username": "u.etudiant",
        "email": "etudiant@iuec.cm",
        "password": "etudiant123!",
        "first_name": "Etudiant",
        "last_name": "IUEC",
        "phone": "690000003",
        "roles": ("USER_STUDENT",),
    },
    {
        "username": "u.finance",
        "email": "finance@iuec.cm",
        "password": "finance123!",
        "first_name": "Finance",
        "last_name": "IUEC",
        "phone": "690000004",
        "roles": ("OPERATOR_FINANCE",),
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
            _ensure_identity_and_roles(
                username=user["username"],
                email=user["email"],
                first_name=user["first_name"],
                last_name=user["last_name"],
                phone=user["phone"],
                roles=user["roles"],
                role_map=role_map,
                user_model=user_model,
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
) -> None:
    user, _ = user_model.objects.get_or_create(
        username=username, defaults={"email": email}
    )
    if not user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])

    identity, _ = CoreIdentity.objects.get_or_create(
        email=email,
        defaults={
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "metadata": {"scope": "FASE"},
        },
    )
    if identity.phone != phone:
        identity.phone = phone
        identity.save(update_fields=["phone"])

    for role_code in roles:
        role = role_map[role_code]
        IdentityRoleLink.objects.get_or_create(
            identity=identity, role=role, defaults={"assigned_by": "seed"}
        )
