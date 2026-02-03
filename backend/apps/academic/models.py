
from __future__ import annotations

from typing import Any, Dict
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from identity.models import CoreIdentity


def validate_academic_rules(value: Dict[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ValidationError("academic_rules_json doit être un objet JSON.")

    required_keys = {"grading_system", "financial_rules"}
    missing = required_keys - set(value.keys())
    if missing:
        raise ValidationError(
            f"academic_rules_json doit contenir les clés: {', '.join(sorted(missing))}"
        )

    grading_system = value.get("grading_system")
    financial_rules = value.get("financial_rules")
    if not isinstance(grading_system, dict):
        raise ValidationError("grading_system doit être un objet JSON.")
    if not isinstance(financial_rules, dict):
        raise ValidationError("financial_rules doit être un objet JSON.")


class Faculty(models.Model):
    """FACULTY - Gestion des facultés et de leur tutelle."""

    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=150)
    doyen_uuid = models.ForeignKey(
        CoreIdentity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculties_led",
        db_column="doyen_uuid",
    )
    tutelle = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "FACULTY"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class AcademicYear(models.Model):
    code = models.CharField(max_length=16, unique=True)
    label = models.CharField(max_length=64)
    is_active = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.label


class ProgramManager(models.Manager["Program"]):
    def get_rules(self, filiere_code: str) -> Dict[str, Any]:
        program = self.get(code=filiere_code)
        return program.academic_rules_json


class Program(models.Model):
    """PROGRAM - Règles académiques et financières par filière."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.PROTECT,
        related_name="programs",
    )
    academic_rules_json = models.JSONField(
        default=dict, validators=[validate_academic_rules]
    )
    is_active = models.BooleanField(default=True)

    objects = ProgramManager()

    class Meta:
        db_table = "PROGRAM"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class TeachingUnit(models.Model):
    """TEACHING_UNIT - Unité d'enseignement (UE)."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="teaching_units",
        null=True,
        blank=True,
    )
    credits = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    teachers = models.ManyToManyField(
        CoreIdentity,
        related_name="taught_teaching_units",
        blank=True,
    )

    class Meta:
        db_table = "TEACHING_UNIT"
        verbose_name = "Unité d'enseignement"
        verbose_name_plural = "Unités d'enseignement"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class StudentProfile(models.Model):
    """STUDENT_PROFILE - Profil étudiant lié à l'identité."""

    class FinanceStatus(models.TextChoices):
        OK = "OK", "OK"
        BLOCKED = "BLOQUE", "Bloqué"
        MORATORIUM = "MORATOIRE", "Moratoire"

    class AcademicStatus(models.TextChoices):
        ACTIVE = "ACTIF", "Actif"
        FAILED = "AJOURE", "Ajourné"
        EXCLUDED = "EXCLU", "Exclu"

    identity = models.OneToOneField(
        CoreIdentity,
        on_delete=models.CASCADE,
        related_name="student_profile",
        unique=True,
        db_column="identity_uuid",
    )
    matricule_permanent = models.CharField(max_length=20, unique=True, db_column="matricule_permanent")
    date_entree = models.DateField()
    current_program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        related_name="students",
        null=True,
        blank=True,
        db_column="current_program_id",
    )
    finance_status = models.CharField(
        max_length=20,
        choices=[("OK", "OK"), ("Bloqué", "Bloqué"), ("Moratoire", "Moratoire")],
        default="OK",
        db_index=True,
    )
    academic_status = models.CharField(
        max_length=20,
        choices=[("Actif", "Actif"), ("Ajourné", "Ajourné"), ("Exclu", "Exclu")],
        default="Actif",
    )
    solde = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, help_text="Calculé via signal"
    )

    class Meta:
        db_table = "STUDENT_PROFILE"
        verbose_name = "Profil étudiant"
        verbose_name_plural = "Profils étudiants"
        ordering = ["-date_entree", "matricule_permanent"]
        indexes = [
            models.Index(fields=["matricule_permanent"]),
            models.Index(fields=["finance_status"]),
            models.Index(fields=["academic_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.matricule_permanent} - {self.identity.email}"

    @staticmethod
    def generate_matricule() -> str:
        """
        Génère un matricule unique au format 25B00001, 25B00002, etc.
        Cherche le dernier matricule existant et incrémente.
        Si aucun matricule n'existe, commence à 25B00001.
        """
        # Récupérer tous les matricules existants qui commencent par "25B"
        existing_matricules = StudentProfile.objects.filter(
            matricule_permanent__startswith="25B"
        ).values_list("matricule_permanent", flat=True)
        
        # Extraire les numéros et trouver le max
        max_num = 0
        for matricule in existing_matricules:
            try:
                # Extraire les 5 derniers chiffres (ex: "25B00001" -> "00001" -> 1)
                if len(matricule) >= 8:  # Au moins "25B00001" (8 caractères)
                    num_str = matricule[3:]  # Skip "25B"
                    num = int(num_str)
                    if num > max_num:
                        max_num = num
            except (ValueError, IndexError):
                continue
        
        # Générer le prochain matricule (commence à 1 si aucun n'existe)
        next_num = max_num + 1
        return f"25B{next_num:05d}"


class RegistrationAdmin(models.Model):
    """REGISTRATION_ADMIN - Inscription administrative annuelle."""

    LEVEL_CHOICES = [
        ("L1", "L1"),
        ("L2", "L2"),
        ("L3", "L3"),
        ("M1", "M1"),
        ("M2", "M2"),
    ]

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="registrations_admin",
        db_column="student_uuid",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="registrations",
        db_column="academic_year_id",
    )
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    finance_status = models.CharField(
        max_length=20,
        choices=[("OK", "OK"), ("Bloqué", "Bloqué"), ("Moratoire", "Moratoire")],
        help_text="Synchronisé avec student.finance_status",
    )
    registration_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "REGISTRATION_ADMIN"
        verbose_name = "Inscription administrative"
        verbose_name_plural = "Inscriptions administratives"
        ordering = ["-registration_date", "student"]
        indexes = [
            models.Index(fields=["student", "academic_year"]),
            models.Index(fields=["finance_status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(finance_status="Bloqué"),
                name="no_registration_if_blocked",
            ),
        ]

    def clean(self) -> None:
        """Vérifie que l'inscription n'est pas bloquée par le statut financier."""
        if self.finance_status == "Bloqué":
            raise ValidationError("Inscription impossible : étudiant bloqué")
        # Vérifie aussi le statut du profil étudiant
        if hasattr(self, "student") and self.student:
            if self.student.finance_status == "Bloqué":
                raise ValidationError("Inscription impossible : étudiant bloqué")

    def __str__(self) -> str:
        return f"{self.student.matricule_permanent} - {self.academic_year.code} - {self.level}"


class RegistrationPedagogical(models.Model):
    """REGISTRATION_PEDAGOGICAL - Inscription pédagogique par UE."""

    class Status(models.TextChoices):
        IN_PROGRESS = "En cours", "En cours"
        VALIDATED = "Validé", "Validé"
        FAILED = "Ajourné", "Ajourné"
        DEBT = "Dette", "Dette"

    registration_admin = models.ForeignKey(
        RegistrationAdmin,
        on_delete=models.CASCADE,
        related_name="pedagogical",
        db_column="registration_admin_id",
    )
    teaching_unit = models.ForeignKey(
        TeachingUnit,
        on_delete=models.CASCADE,
        related_name="registrations",
        db_column="teaching_unit_id",
    )
    status = models.CharField(
        max_length=20,
        choices=[("En cours", "En cours"), ("Validé", "Validé"), ("Ajourné", "Ajourné"), ("Dette", "Dette")],
        default="En cours",
    )

    class Meta:
        db_table = "REGISTRATION_PEDAGOGICAL"
        verbose_name = "Inscription pédagogique"
        verbose_name_plural = "Inscriptions pédagogiques"
        ordering = ["registration_admin", "teaching_unit"]
        indexes = [
            models.Index(fields=["registration_admin", "teaching_unit"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.registration_admin} - {self.teaching_unit.code}"


class CourseElement(models.Model):
    """COURSE_ELEMENT - Élément de cours (matière/cours)."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=150)
    teaching_unit = models.ForeignKey(
        TeachingUnit,
        on_delete=models.CASCADE,
        related_name="course_elements",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "COURSE_ELEMENT"
        verbose_name = "Élément de cours"
        verbose_name_plural = "Éléments de cours"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Evaluation(models.Model):
    """EVALUATION - Composantes d'évaluation par cours."""

    class EvaluationType(models.TextChoices):
        CC = "CC", "CC"
        TP = "TP", "TP"
        EXAM = "Exam", "Exam"
        STAGE = "Stage", "Stage"
        AUTRE = "Autre", "Autre"

    course_element = models.ForeignKey(
        CourseElement,
        on_delete=models.CASCADE,
        related_name="evaluations",
        db_column="course_element_id",
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=16, choices=EvaluationType.choices)
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    session_date = models.DateField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "EVALUATION"
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"

    def __str__(self) -> str:
        return f"{self.course_element.code} - {self.type}"


class Grade(models.Model):
    """GRADE - Note individuelle pour une évaluation."""

    evaluation = models.ForeignKey(
        Evaluation, on_delete=models.CASCADE, related_name="grades"
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="grades"
    )
    value = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    is_absent = models.BooleanField(default=False)
    teacher = models.ForeignKey(
        CoreIdentity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grades_given",
        db_column="teacher_uuid",
    )
    created_by_role = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "GRADE"
        verbose_name = "Note"
        verbose_name_plural = "Notes"
        constraints = [
            models.UniqueConstraint(
                fields=["evaluation", "student"], name="unique_grade_per_evaluation_student"
            )
        ]

    def __str__(self) -> str:
        return f"{self.student_id} - {self.evaluation_id}"
class GradeEntry(models.Model):
    """Saisie des notes par UE et composant."""

    identity_uuid = models.UUIDField()
    ue_code = models.CharField(max_length=32)
    component = models.CharField(max_length=16)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    created_by = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "GRADE_ENTRY"

    def __str__(self) -> str:
        return f"{self.identity_uuid} {self.ue_code} {self.component}"


class Frais(models.Model):
    """FRAIS - Frais d'inscription et de scolarité par programme."""

    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="frais",
        db_column="program_id",
    )
    academic_year = models.CharField(
        max_length=16,
        help_text="Année académique (ex: 2024-2025)",
    )
    # Frais d'inscription
    inscription_iuec = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    inscription_tutelle = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    inscription_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    echeance_inscription = models.DateField(null=True, blank=True)
    # Frais de scolarité
    scolarite_tranche1 = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    scolarite_tranche2 = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    scolarite_tranche3 = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=None
    )
    scolarite_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    echeances_scolarite = models.JSONField(
        default=list,
        help_text="Liste des dates d'échéances de scolarité",
    )
    # Autres frais (kits, blouses, etc.)
    autres_frais = models.JSONField(
        default=dict,
        help_text="Autres frais spécifiques (kits, blouses, matières d'œuvre, etc.)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "FRAIS"
        verbose_name = "Frais"
        verbose_name_plural = "Frais"
        unique_together = [["program", "academic_year"]]
        indexes = [
            models.Index(fields=["program", "academic_year"]),
        ]

    def __str__(self) -> str:
        return f"{self.program.code} - {self.academic_year}"


@receiver(post_save, sender=Program)
def recalculate_student_balance_on_fees_change(sender, instance: Program, created, **kwargs):
    """
    Recalcule le solde des étudiants si les frais du programme changent.
    Ne s'exécute que si academic_rules_json a été modifié (frais ajoutés).
    """
    # Ne recalculer que si les frais ont été modifiés (pas à la création)
    if created:
        return
    
    # Vérifier si les frais ont été ajoutés/modifiés dans academic_rules_json
    if "frais" not in instance.academic_rules_json:
        return
    
    from apps.finance.models import Invoice
    
    # Récupérer tous les étudiants de ce programme
    students = instance.students.all()
    
    from apps.finance.models import Payment
    
    for student in students:
        # Recalculer le solde basé sur les factures existantes
        # Le signal sur Invoice devrait déjà gérer cela, mais on force un refresh
        total_invoices = Invoice.objects.filter(
            identity_uuid=student.identity.id
        ).aggregate(
            total=models.Sum("total_amount")
        )["total"] or Decimal("0")
        
        # Récupérer les paiements via les factures
        total_payments = Payment.objects.filter(
            invoice__identity_uuid=student.identity.id
        ).aggregate(
            total=models.Sum("amount")
        )["total"] or Decimal("0")
        
        new_solde = total_invoices - total_payments
        
        if student.solde != new_solde:
            new_finance_status = "Bloqué" if new_solde > 0 else "OK"
            # Utiliser update pour éviter de déclencher à nouveau le signal
            StudentProfile.objects.filter(id=student.id).update(
                solde=new_solde,
                finance_status=new_finance_status
            )
