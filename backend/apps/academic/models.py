
from __future__ import annotations

from typing import Any, Dict
from django.core.exceptions import ValidationError
from django.db import models

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


class Evaluation(models.Model):
    """EVALUATION - Composantes d'évaluation par cours."""

    class EvaluationType(models.TextChoices):
        CC = "CC", "CC"
        TP = "TP", "TP"
        EXAM = "EXAM", "Exam"

    course_id = models.UUIDField()
    type = models.CharField(max_length=16, choices=EvaluationType.choices)
    weight = models.DecimalField(max_digits=6, decimal_places=3, default=1)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=20)
    is_closed = models.BooleanField(default=False)

    class Meta:
        db_table = "EVALUATION"

    def __str__(self) -> str:
        return f"{self.course_id} - {self.type}"


class Grade(models.Model):
    """GRADE - Note individuelle pour une évaluation."""

    evaluation = models.ForeignKey(
        Evaluation, on_delete=models.CASCADE, related_name="grades"
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="grades"
    )
    value = models.DecimalField(max_digits=6, decimal_places=2)
    teacher = models.ForeignKey(
        CoreIdentity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="grades_given",
        db_column="teacher_uuid",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "GRADE"
        unique_together = ("evaluation", "student")

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
