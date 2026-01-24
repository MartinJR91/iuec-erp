from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.academic.models import GradeEntry, Program
from apps.finance.models import Invoice
from identity.models import CoreIdentity, IdentityRoleLink, RbacRoleDef


@dataclass(frozen=True)
class RoleAssignment:
    code: str
    scope: Optional[str] = None


@dataclass(frozen=True)
class DemoUserSpec:
    username: str
    email: str
    phone: str
    password: str
    first_name: str
    last_name: str
    roles: Tuple[RoleAssignment, ...]
    metadata: Dict[str, object]


class Command(BaseCommand):
    help = "Seed dataset complet pour la démo IUEC ERP."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--keep-data",
            action="store_true",
            help="Ne supprime pas les données existantes avant seed.",
        )

    def handle(self, *args, **options) -> None:
        keep_data: bool = bool(options.get("keep_data"))
        self._ensure_admin()

        if not keep_data:
            self._reset_data()

        role_map = self._ensure_roles(
            [
                "ADMIN_SI",
                "RECTEUR",
                "USER_TEACHER",
                "VIEWER_STRATEGIC",
                "USER_STUDENT",
                "OPERATOR_FINANCE",
                "VALIDATOR_ACAD",
            ]
        )

        users = self._demo_users()
        for spec in users:
            self._create_user_with_roles(spec, role_map)

        self._seed_programs()
        self._seed_invoice_and_grade()
        self._print_credentials(users)

        self.stdout.write(self.style.SUCCESS("Seed demo terminé."))

    def _reset_data(self) -> None:
        User = get_user_model()
        self.stdout.write("==> Suppression des users non-admin")
        User.objects.exclude(username="admin").delete()
        self.stdout.write("==> Suppression des liens de rôles et identités")
        IdentityRoleLink.objects.all().delete()
        CoreIdentity.objects.exclude(email="admin@iuec.cm").delete()
        self.stdout.write("==> Nettoyage terminé")

    def _ensure_admin(self) -> None:
        User = get_user_model()
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@iuec.cm", "is_superuser": True, "is_staff": True},
        )
        if created:
            admin.password = make_password("admin123!")
            admin.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS("Superuser admin créé."))
        elif admin.email != "admin@iuec.cm":
            admin.email = "admin@iuec.cm"
            admin.save(update_fields=["email"])

    def _ensure_roles(self, roles: Iterable[str]) -> Dict[str, RbacRoleDef]:
        role_map: Dict[str, RbacRoleDef] = {}
        for code in roles:
            role, _ = RbacRoleDef.objects.get_or_create(
                code=code,
                defaults={
                    "label": code,
                    "description": f"Role {code}",
                    "permissions": {},
                    "is_system": True,
                    "is_active": True,
                },
            )
            role_map[code] = role
        return role_map

    def _demo_users(self) -> List[DemoUserSpec]:
        return [
            DemoUserSpec(
                username="admin",
                email="admin@iuec.cm",
                phone="+237690000000",
                password="admin123!",
                first_name="Admin",
                last_name="IUEC",
                roles=(RoleAssignment("ADMIN_SI", None),),
                metadata={"scope_by_role": {"ADMIN_SI": None}},
            ),
            DemoUserSpec(
                username="recteur.kamga",
                email="recteur@iuec.cm",
                phone="+237691234567",
                password="recteur123!",
                first_name="Paul",
                last_name="KAMGA",
                roles=(
                    RoleAssignment("RECTEUR", None),
                    RoleAssignment("USER_TEACHER", "FASE"),
                    RoleAssignment("VIEWER_STRATEGIC", None),
                ),
                metadata={"scope_by_role": {"USER_TEACHER": "FASE"}},
            ),
            DemoUserSpec(
                username="enseignant.dupont",
                email="marie.dupont@iuec.cm",
                phone="+237692345678",
                password="ens123!",
                first_name="Marie",
                last_name="Dupont",
                roles=(RoleAssignment("USER_TEACHER", "FST"),),
                metadata={"scope_by_role": {"USER_TEACHER": "FST"}},
            ),
            DemoUserSpec(
                username="etudiant.ngono",
                email="elise.ngono@iuec.cm",
                phone="+237693456789",
                password="etu123!",
                first_name="Elise",
                last_name="Ngono",
                roles=(RoleAssignment("USER_STUDENT", "FASE_ING"),),
                metadata={
                    "matricule": "25B001UE",
                    "program": "FASE_ING",
                    "niveau": "L3",
                },
            ),
            DemoUserSpec(
                username="finance.op",
                email="finance@iuec.cm",
                phone="+237694567890",
                password="fin123!",
                first_name="Finance",
                last_name="Op",
                roles=(RoleAssignment("OPERATOR_FINANCE", None),),
                metadata={"scope_by_role": {"OPERATOR_FINANCE": None}},
            ),
            DemoUserSpec(
                username="doyen.fst",
                email="doyen.fst@iuec.cm",
                phone="+237695678901",
                password="doyen123!",
                first_name="Mballa",
                last_name="PR",
                roles=(
                    RoleAssignment("VALIDATOR_ACAD", "FST"),
                    RoleAssignment("USER_TEACHER", "FST"),
                ),
                metadata={"scope_by_role": {"VALIDATOR_ACAD": "FST", "USER_TEACHER": "FST"}},
            ),
        ]

    def _create_user_with_roles(
        self, spec: DemoUserSpec, role_map: Dict[str, RbacRoleDef]
    ) -> None:
        User = get_user_model()
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username=spec.username,
                defaults={
                    "email": spec.email,
                    "is_active": True,
                    "is_staff": spec.username == "admin",
                    "is_superuser": spec.username == "admin",
                },
            )
            if created:
                user.password = make_password(spec.password)
                user.save(update_fields=["password"])
            elif user.email != spec.email:
                user.email = spec.email
                user.save(update_fields=["email"])

            identity, _ = CoreIdentity.objects.get_or_create(
                email=spec.email,
                defaults={
                    "phone": spec.phone,
                    "first_name": spec.first_name,
                    "last_name": spec.last_name,
                    "is_active": True,
                    "metadata": spec.metadata,
                },
            )

            now = timezone.now()
            for assignment in spec.roles:
                role = role_map[assignment.code]
                IdentityRoleLink.objects.get_or_create(
                    identity=identity,
                    role=role,
                    defaults={
                        "is_active": True,
                        "starts_at": now,
                        "assigned_by": "seed_demo",
                    },
                )

    def _seed_programs(self) -> None:
        Program.objects.get_or_create(
            code="FASE_ING",
            defaults={
                "label": "FASE Ingénierie",
                "academic_rules_json": {
                    "cycle_type": "LMD",
                    "grading_system": {"min_validate": 10, "compensation": True},
                    "financial_rules": {
                        "mandatory_products": ["KIT_AGRO"],
                        "concours_required": False,
                    },
                    "tutelle_export_format": "CSV",
                },
                "is_active": True,
            },
        )
        Program.objects.get_or_create(
            code="FSG",
            defaults={
                "label": "FSG Sciences de Gestion",
                "academic_rules_json": {
                    "cycle_type": "LMD",
                    "grading_system": {
                        "min_validate": 10,
                        "compensation": True,
                        "default_component_weights": {"TD": 0.3, "EXAM": 0.7},
                    },
                    "financial_rules": {"mandatory_products": [], "concours_required": False},
                    "tutelle_export_format": "CSV",
                },
                "is_active": True,
            },
        )

    def _seed_invoice_and_grade(self) -> None:
        student = CoreIdentity.objects.filter(email="elise.ngono@iuec.cm").first()
        teacher = CoreIdentity.objects.filter(email="marie.dupont@iuec.cm").first()
        if not student or not teacher:
            self.stdout.write(self.style.WARNING("Identités manquantes pour invoice/grade."))
            return

        Invoice.objects.get_or_create(
            identity_uuid=student.id,
            program_code="FASE_ING",
            defaults={
                "line_items": [
                    {"code": "SCOLARITE", "label": "Frais scolarité", "amount": "500000"},
                    {"code": "KIT_AGRO", "label": "Kit Agro", "amount": "0.00"},
                ],
                "status": Invoice.STATUS_ISSUED,
                "due_date": timezone.now().date(),
            },
        )

        GradeEntry.objects.get_or_create(
            identity_uuid=student.id,
            ue_code="FST_UE_DEMO",
            component="CC",
            defaults={"score": "12.00", "created_by": teacher.email},
        )
        GradeEntry.objects.get_or_create(
            identity_uuid=student.id,
            ue_code="FST_UE_DEMO",
            component="EXAM",
            defaults={"score": "14.00", "created_by": teacher.email},
        )

    def _print_credentials(self, users: List[DemoUserSpec]) -> None:
        self.stdout.write("\n==> Comptes démo créés")
        for spec in users:
            roles = ", ".join(role.code for role in spec.roles) or "Aucun"
            self.stdout.write(
                f"- {spec.username} / {spec.password} ({spec.email}) roles: {roles}"
            )
