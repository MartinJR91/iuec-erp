from __future__ import annotations

from typing import Iterable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from identity.models import CoreIdentity, IdentityRoleLink, RbacRoleDef


class Command(BaseCommand):
    help = "Crée des utilisateurs démo et leurs rôles."

    def handle(self, *args, **options) -> None:
        user_model = get_user_model()

        roles = [
            ("RECTEUR", "Recteur"),
            ("USER_TEACHER", "Enseignant"),
            ("VIEWER_STRATEGIC", "Viewer Strategic"),
            ("USER_STUDENT", "Etudiant"),
            ("OPERATOR_FINANCE", "Opérateur Finance"),
        ]
        role_map = {code: self._get_or_create_role(code, label) for code, label in roles}

        users = [
            ("admin", "admin@iuec.cm", "admin123!"),
            ("u.recteur", "recteur@iuec.cm", "recteur123!"),
            ("u.ens", "ens@iuec.cm", "enseignant123!"),
            ("u.etudiant", "etudiant@iuec.cm", "etudiant123!"),
            ("u.finance", "finance@iuec.cm", "finance123!"),
        ]

        with transaction.atomic():
            self._ensure_superuser(
                user_model, username="admin", email="admin@iuec.cm", password="admin123!"
            )

            self._ensure_identity_and_roles(
                username="u.recteur",
                email="recteur@iuec.cm",
                first_name="Recteur",
                last_name="IUEC",
                phone="690000001",
                roles=("RECTEUR", "USER_TEACHER", "VIEWER_STRATEGIC"),
                role_map=role_map,
                user_model=user_model,
            )
            self._ensure_identity_and_roles(
                username="u.ens",
                email="ens@iuec.cm",
                first_name="Enseignant",
                last_name="IUEC",
                phone="690000002",
                roles=("USER_TEACHER",),
                role_map=role_map,
                user_model=user_model,
            )
            self._ensure_identity_and_roles(
                username="u.etudiant",
                email="etudiant@iuec.cm",
                first_name="Etudiant",
                last_name="IUEC",
                phone="690000003",
                roles=("USER_STUDENT",),
                role_map=role_map,
                user_model=user_model,
            )
            self._ensure_identity_and_roles(
                username="u.finance",
                email="finance@iuec.cm",
                first_name="Finance",
                last_name="IUEC",
                phone="690000004",
                roles=("OPERATOR_FINANCE",),
                role_map=role_map,
                user_model=user_model,
            )

        self.stdout.write(self.style.SUCCESS("Utilisateurs démo créés."))
        self.stdout.write("Credentials:")
        for username, email, password in users:
            self.stdout.write(f"- {username} / {email} / {password}")

    def _get_or_create_role(self, code: str, label: str) -> RbacRoleDef:
        role, _ = RbacRoleDef.objects.get_or_create(
            code=code,
            defaults={"label": label, "description": label, "permissions": {}},
        )
        return role

    def _ensure_superuser(
        self, user_model, username: str, email: str, password: str
    ) -> None:
        if not user_model.objects.filter(username=username).exists():
            user_model.objects.create_superuser(
                username=username, email=email, password=password
            )

    def _ensure_identity_and_roles(
        self,
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
