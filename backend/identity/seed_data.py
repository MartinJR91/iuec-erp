"""Script de seed pour créer des données de test complètes (étudiants, factures, inscriptions)."""
from __future__ import annotations

from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.academic.models import (
    AcademicYear,
    Faculty,
    Program,
    RegistrationAdmin,
    StudentProfile,
)
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, IdentityRoleLink, RbacRoleDef
from identity.seed import seed_demo_users


def seed_test_data() -> None:
    """Crée des données de test complètes : facultés, programmes, étudiants, factures, inscriptions."""
    user_model = get_user_model()

    with transaction.atomic():
        # 1. S'assurer que les utilisateurs de base existent
        seed_demo_users()

        # 2. Créer ou récupérer les rôles
        doyen_role, _ = RbacRoleDef.objects.get_or_create(
            code="DOYEN", defaults={"label": "Doyen", "is_active": True}
        )

        # 3. Créer ou récupérer les facultés
        faculty_fase, _ = Faculty.objects.get_or_create(
            code="FASE",
            defaults={
                "name": "Faculté des Sciences Économiques",
                "tutelle": "MINESUP",
                "is_active": True,
            },
        )
        faculty_fst, _ = Faculty.objects.get_or_create(
            code="FST",
            defaults={
                "name": "Faculté des Sciences et Techniques",
                "tutelle": "MINESUP",
                "is_active": True,
            },
        )

        # Lier le doyen à FASE
        doyen_identity = CoreIdentity.objects.filter(email="doyen@iuec.cm").first()
        if doyen_identity:
            faculty_fase.doyen_uuid = doyen_identity
            faculty_fase.save()

        # 4. Créer ou récupérer les programmes
        program_eco, _ = Program.objects.get_or_create(
            code="ECO",
            defaults={
                "name": "Économie",
                "faculty": faculty_fase,
                "academic_rules_json": {
                    "grading_system": {"min_validate": 10, "compensation": True},
                    "financial_rules": {"tuition": 50000},
                },
                "is_active": True,
            },
        )
        program_info, _ = Program.objects.get_or_create(
            code="INFO",
            defaults={
                "name": "Informatique",
                "faculty": faculty_fst,
                "academic_rules_json": {
                    "grading_system": {"min_validate": 10, "compensation": True},
                    "financial_rules": {"tuition": 60000},
                },
                "is_active": True,
            },
        )

        # 5. Créer ou récupérer l'année académique
        academic_year, _ = AcademicYear.objects.get_or_create(
            code="2024-2025",
            defaults={
                "label": "Année académique 2024-2025",
                "is_active": True,
            },
        )

        # 6. Créer des étudiants de test
        students_data = [
            {
                "email": "etudiant1@iuec.cm",
                "first_name": "Jean",
                "last_name": "KAMGA",
                "phone": "690000010",
                "matricule": "ST2024001",
                "program": program_eco,
                "level": "L1",
                "finance_status": "OK",
                "academic_status": "Actif",
                "invoice_amount": Decimal("50000"),
                "paid_amount": Decimal("50000"),
            },
            {
                "email": "etudiant2@iuec.cm",
                "first_name": "Marie",
                "last_name": "DJOUMESSI",
                "phone": "690000011",
                "matricule": "ST2024002",
                "program": program_eco,
                "level": "L2",
                "finance_status": "OK",
                "academic_status": "Actif",
                "invoice_amount": Decimal("50000"),
                "paid_amount": Decimal("30000"),  # Solde positif = bloqué
            },
            {
                "email": "etudiant3@iuec.cm",
                "first_name": "Paul",
                "last_name": "MBALLA",
                "phone": "690000012",
                "matricule": "ST2024003",
                "program": program_info,
                "level": "L1",
                "finance_status": "Bloqué",
                "academic_status": "Actif",
                "invoice_amount": Decimal("60000"),
                "paid_amount": Decimal("0"),
            },
            {
                "email": "etudiant4@iuec.cm",
                "first_name": "Sophie",
                "last_name": "TCHOUA",
                "phone": "690000013",
                "matricule": "ST2024004",
                "program": program_eco,
                "level": "M1",
                "finance_status": "Moratoire",
                "academic_status": "Actif",
                "invoice_amount": Decimal("50000"),
                "paid_amount": Decimal("40000"),
            },
            {
                "email": "elise.ngono@iuec.cm",  # Étudiant existant
                "first_name": "Elise",
                "last_name": "NGONO",
                "phone": "690000003",
                "matricule": "ST2024005",
                "program": program_eco,
                "level": "L1",
                "finance_status": "OK",
                "academic_status": "Actif",
                "invoice_amount": Decimal("50000"),
                "paid_amount": Decimal("50000"),
            },
        ]

        for student_data in students_data:
            # Créer ou récupérer l'identité
            identity, _ = CoreIdentity.objects.get_or_create(
                email=student_data["email"],
                defaults={
                    "first_name": student_data["first_name"],
                    "last_name": student_data["last_name"],
                    "phone": student_data["phone"],
                    "is_active": True,
                },
            )

            # Créer ou récupérer le profil étudiant
            # IMPORTANT: Créer d'abord avec finance_status="OK" pour éviter la contrainte CHECK
            student_profile, created = StudentProfile.objects.get_or_create(
                identity=identity,
                defaults={
                    "matricule_permanent": student_data["matricule"],
                    "date_entree": date.today() - timedelta(days=180),
                    "current_program": student_data["program"],
                    "finance_status": "OK",  # Créer avec OK d'abord
                    "academic_status": student_data["academic_status"],
                },
            )
            if not created:
                # Mettre à jour si existe déjà
                student_profile.matricule_permanent = student_data["matricule"]
                student_profile.current_program = student_data["program"]
                student_profile.academic_status = student_data["academic_status"]
                student_profile.save()

            # Créer l'inscription administrative SEULEMENT si l'étudiant n'est pas bloqué
            # La contrainte CHECK empêche la création d'inscription avec finance_status="Bloqué"
            if student_data["finance_status"] != "Bloqué":
                registration, _ = RegistrationAdmin.objects.get_or_create(
                    student=student_profile,
                    academic_year=academic_year,
                    defaults={
                        "level": student_data["level"],
                        "finance_status": student_data["finance_status"],
                    },
                )
                # Mettre à jour le finance_status du profil
                if student_data["finance_status"] != student_profile.finance_status:
                    student_profile.finance_status = student_data["finance_status"]
                    student_profile.save()
            else:
                # Pour les étudiants bloqués, on ne crée pas d'inscription
                # On met juste à jour le finance_status du profil
                student_profile.finance_status = "Bloqué"
                student_profile.save()

            # Créer une facture
            invoice, _ = Invoice.objects.get_or_create(
                identity_uuid=identity.id,
                program_code=student_data["program"].code,
                defaults={
                    "total_amount": student_data["invoice_amount"],
                    "issue_date": date.today() - timedelta(days=30),
                    "due_date": date.today() + timedelta(days=30),
                    "status": Invoice.STATUS_ISSUED,
                },
            )

            # Créer un paiement si nécessaire
            if student_data["paid_amount"] > 0:
                Payment.objects.get_or_create(
                    invoice=invoice,
                    amount=student_data["paid_amount"],
                    defaults={
                        "method": Payment.METHOD_CASH,
                        "reference": f"PAY-{student_data['matricule']}",
                    },
                )

        print(f"Seed termine : {len(students_data)} etudiants crees avec factures et inscriptions")


if __name__ == "__main__":
    seed_test_data()
