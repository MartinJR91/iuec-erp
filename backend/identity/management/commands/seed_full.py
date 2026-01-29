"""Commande Django pour créer un seed complet avec facultés, programmes, étudiants, factures et notes."""
from __future__ import annotations

from decimal import Decimal
from datetime import date, timedelta
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.academic.models import (
    AcademicYear,
    Evaluation,
    Faculty,
    Grade,
    Program,
    RegistrationAdmin,
    StudentProfile,
    TeachingUnit,
)
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity
from identity.seed import seed_demo_users


class Command(BaseCommand):
    help = "Crée un seed complet avec facultés, programmes, étudiants, factures et notes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep-data",
            action="store_true",
            help="Ne supprime pas les données existantes (ajoute seulement)",
        )

    def handle(self, *args, **options):
        keep_data = options.get("keep_data", False)

        try:
            with transaction.atomic():
                self.stdout.write("Demarrage du seed complet...")

                # 1. Créer les utilisateurs de base
                self.stdout.write("  - Creation des utilisateurs de base...")
                seed_demo_users()

                # 2. Créer les facultés
                self.stdout.write("  - Creation des facultes...")
                faculties = self._create_faculties()

                # 3. Créer les programmes
                self.stdout.write("  - Creation des programmes...")
                programs = self._create_programs(faculties)

                # 4. Créer l'année académique
                self.stdout.write("  - Creation de l'annee academique...")
                academic_year = self._create_academic_year()

                # 5. Créer les étudiants
                self.stdout.write("  - Creation des etudiants...")
                students = self._create_students(programs, academic_year)

                # 6. Créer les factures
                self.stdout.write("  - Creation des factures...")
                self._create_invoices(students)

                # 7. Créer les unités d'enseignement et notes
                self.stdout.write("  - Creation des UE et notes...")
                self._create_grades(programs, students)

                self.stdout.write(self.style.SUCCESS("Seed complet termine avec succes !"))
                self.stdout.write(f"   - {len(faculties)} facultes creees")
                self.stdout.write(f"   - {len(programs)} programmes crees")
                self.stdout.write(f"   - {len(students)} etudiants crees")
                self.stdout.write(f"   - {academic_year.code} annee academique creee")

        except Exception as e:
            raise CommandError(f"Erreur lors du seed : {str(e)}")

    def _create_faculties(self):
        """Crée 3 facultés : FASE, FST, FSG."""
        faculties_data = [
            {"code": "FASE", "name": "Faculté des Sciences Économiques", "tutelle": "MINESUP"},
            {"code": "FST", "name": "Faculté des Sciences et Techniques", "tutelle": "MINESUP"},
            {"code": "FSG", "name": "Faculté des Sciences de Gestion", "tutelle": "MINESUP"},
        ]

        faculties = []
        doyen_identity = CoreIdentity.objects.filter(email="doyen@iuec.cm").first()

        for fac_data in faculties_data:
            faculty, created = Faculty.objects.get_or_create(
                code=fac_data["code"],
                defaults={
                    "name": fac_data["name"],
                    "tutelle": fac_data["tutelle"],
                    "is_active": True,
                    "doyen_uuid": doyen_identity if fac_data["code"] == "FASE" else None,
                },
            )
            faculties.append(faculty)

        return faculties

    def _create_programs(self, faculties):
        """Crée 2 programmes par faculté."""
        programs_data = [
            {"code": "FASE_ING", "name": "Ingénierie Économique", "faculty": "FASE"},
            {"code": "FASE_AGRO", "name": "Agroéconomie", "faculty": "FASE"},
            {"code": "FST_INFO", "name": "Informatique", "faculty": "FST"},
            {"code": "FST_MATH", "name": "Mathématiques", "faculty": "FST"},
            {"code": "FSG_COMPTA", "name": "Comptabilité", "faculty": "FSG"},
            {"code": "FSG_MARKET", "name": "Marketing", "faculty": "FSG"},
        ]

        programs = []
        faculty_map = {fac.code: fac for fac in faculties}

        for prog_data in programs_data:
            faculty = faculty_map.get(prog_data["faculty"])
            if not faculty:
                continue

            program, created = Program.objects.get_or_create(
                code=prog_data["code"],
                defaults={
                    "name": prog_data["name"],
                    "faculty": faculty,
                    "academic_rules_json": {
                        "grading_system": {"min_validate": 10, "compensation": True},
                        "financial_rules": {"tuition": 50000},
                    },
                    "is_active": True,
                },
            )
            programs.append(program)

        return programs

    def _create_academic_year(self):
        """Crée l'année académique 2025-2026."""
        academic_year, _ = AcademicYear.objects.get_or_create(
            code="2025-2026",
            defaults={
                "label": "Année académique 2025-2026",
                "is_active": True,
            },
        )
        return academic_year

    def _create_students(self, programs, academic_year):
        """Crée 10 étudiants avec matricules 25B001UE à 25B010UE."""
        students_data = []
        fase_programs = [p for p in programs if p.faculty.code == "FASE"]
        fst_programs = [p for p in programs if p.faculty.code == "FST"]

        # 5 étudiants FASE
        for i in range(1, 6):
            students_data.append(
                {
                    "matricule": f"25B00{i}UE",
                    "first_name": f"Etudiant{i}",
                    "last_name": f"FASE{i}",
                    "email": f"etudiant.fase{i}@iuec.cm",
                    "phone": f"690000{20+i:02d}",
                    "program": fase_programs[i % len(fase_programs)],
                    "level": ["L1", "L2", "L3", "L1", "L2"][i - 1],
                    "finance_status": ["OK", "OK", "OK", "Bloqué", "Moratoire"][i - 1],
                }
            )

        # 5 étudiants FST
        for i in range(6, 11):
            students_data.append(
                {
                    "matricule": f"25B00{i}UE",
                    "first_name": f"Etudiant{i}",
                    "last_name": f"FST{i}",
                    "email": f"etudiant.fst{i}@iuec.cm",
                    "phone": f"690000{30+i:02d}",
                    "program": fst_programs[(i - 6) % len(fst_programs)],
                    "level": ["L1", "L2", "L3", "M1", "M2"][i - 6],
                    "finance_status": ["OK", "OK", "OK", "OK", "OK"][i - 6],
                }
            )

        students = []
        for student_data in students_data:
            # Créer l'identité
            identity, _ = CoreIdentity.objects.get_or_create(
                email=student_data["email"],
                defaults={
                    "first_name": student_data["first_name"],
                    "last_name": student_data["last_name"],
                    "phone": student_data["phone"],
                    "is_active": True,
                },
            )

            # Créer le profil étudiant
            student_profile, created = StudentProfile.objects.get_or_create(
                identity=identity,
                defaults={
                    "matricule_permanent": student_data["matricule"],
                    "date_entree": date.today() - timedelta(days=180),
                    "current_program": student_data["program"],
                    "finance_status": "OK",  # Créer avec OK d'abord
                    "academic_status": "Actif",
                },
            )
            if not created:
                student_profile.matricule_permanent = student_data["matricule"]
                student_profile.current_program = student_data["program"]
                student_profile.save()

            # Créer l'inscription si pas bloqué
            if student_data["finance_status"] != "Bloqué":
                RegistrationAdmin.objects.get_or_create(
                    student=student_profile,
                    academic_year=academic_year,
                    defaults={
                        "level": student_data["level"],
                        "finance_status": student_data["finance_status"],
                    },
                )
                if student_data["finance_status"] != student_profile.finance_status:
                    student_profile.finance_status = student_data["finance_status"]
                    student_profile.save()
            else:
                student_profile.finance_status = "Bloqué"
                student_profile.save()

            students.append(student_profile)

        return students

    def _create_invoices(self, students):
        """Crée des factures pour les étudiants, avec 3 factures impayées (solde négatif)."""
        # 3 étudiants avec factures impayées (bloqués)
        blocked_students = [s for s in students if s.finance_status == "Bloqué"][:3]
        other_students = [s for s in students if s not in blocked_students]

        # Factures impayées (bloqués)
        for student in blocked_students:
            if not student.current_program:
                continue
            invoice, _ = Invoice.objects.get_or_create(
                identity_uuid=student.identity.id,
                program_code=student.current_program.code,
                defaults={
                    "number": f"INV-{student.matricule_permanent}",
                    "total_amount": Decimal("60000"),
                    "issue_date": date.today() - timedelta(days=60),
                    "due_date": date.today() - timedelta(days=30),  # Échue
                    "status": Invoice.STATUS_ISSUED,
                },
            )
            # Pas de paiement = solde négatif

        # Factures payées partiellement ou totalement
        for i, student in enumerate(other_students[:5]):
            if not student.current_program:
                continue
            invoice, _ = Invoice.objects.get_or_create(
                identity_uuid=student.identity.id,
                program_code=student.current_program.code,
                defaults={
                    "number": f"INV-{student.matricule_permanent}",
                    "total_amount": Decimal("50000"),
                    "issue_date": date.today() - timedelta(days=30),
                    "due_date": date.today() + timedelta(days=30),
                    "status": Invoice.STATUS_ISSUED,
                },
            )
            # Paiement partiel ou total
            paid_amount = Decimal("50000") if i < 3 else Decimal("30000")
            Payment.objects.get_or_create(
                invoice=invoice,
                amount=paid_amount,
                defaults={
                    "method": Payment.METHOD_CASH,
                    "reference": f"PAY-{student.matricule_permanent}",
                },
            )

    def _create_grades(self, programs, students):
        """Crée 10 notes (CC/Exam) pour 3 étudiants."""
        # Sélectionner 3 étudiants avec inscriptions
        students_with_reg = [
            s
            for s in students
            if s.registrations_admin.exists() and s.finance_status != "Bloqué"
        ][:3]

        if not students_with_reg:
            self.stdout.write(self.style.WARNING("  Aucun etudiant avec inscription trouve pour les notes."))
            return

        # Créer des unités d'enseignement pour chaque programme
        teacher_identity = CoreIdentity.objects.filter(email="marie.dupont@iuec.cm").first()
        if not teacher_identity:
            self.stdout.write(self.style.WARNING("  Enseignant marie.dupont@iuec.cm non trouve."))
            return

        ues_created = []
        for program in programs[:3]:  # Limiter à 3 programmes
            for ue_code, ue_name in [("UE_MATH", "Mathématiques"), ("UE_INFO", "Informatique")]:
                ue, _ = TeachingUnit.objects.get_or_create(
                    code=f"{program.code}_{ue_code}",
                    defaults={
                        "name": f"{ue_name} - {program.name}",
                        "program": program,
                        "credits": 6,
                        "is_active": True,
                    },
                )
                ues_created.append(ue)

        # Créer des évaluations (CC et Exam) pour chaque UE
        evaluations = []
        for ue in ues_created[:4]:  # Limiter à 4 UE
            course_id = uuid4()
            for eval_type, weight in [("CC", 0.4), ("EXAM", 0.6)]:
                eval_obj, _ = Evaluation.objects.get_or_create(
                    course_id=course_id,
                    type=eval_type,
                    defaults={
                        "weight": Decimal(str(weight)),
                        "max_score": Decimal("20"),
                    },
                )
                evaluations.append((eval_obj, ue))

        # Créer des notes pour 3 étudiants (10 notes au total)
        note_count = 0
        for i, student in enumerate(students_with_reg):
            for j, (eval_obj, ue) in enumerate(evaluations[:4]):  # 4 notes par étudiant max
                if note_count >= 10:
                    break
                # Note aléatoire entre 8 et 18
                note_value = Decimal(str(8 + (i * 2) + (j % 5)))
                Grade.objects.get_or_create(
                    evaluation=eval_obj,
                    student=student,
                    defaults={
                        "value": note_value,
                        "teacher": teacher_identity,
                    },
                )
                note_count += 1
