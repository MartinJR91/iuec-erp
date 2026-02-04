
from __future__ import annotations

from typing import Any, Dict
from decimal import Decimal
from datetime import date
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from identity.models import CoreIdentity, SysAuditLog


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


class Moratoire(models.Model):
    """MORATOIRE - Moratoire accordé à un étudiant pour reporter le paiement."""

    class DureeChoices(models.IntegerChoices):
        JOURS_30 = 30, "30 jours"
        JOURS_60 = 60, "60 jours"
        JOURS_90 = 90, "90 jours"

    class StatutChoices(models.TextChoices):
        ACTIF = "Actif", "Actif"
        RESPECTE = "Respecté", "Respecté"
        DEPASSE = "Dépassé", "Dépassé"

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="moratoires",
        db_column="student_id",
    )
    montant_reporte = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Montant du solde reporté par le moratoire",
    )
    date_accord = models.DateTimeField(
        auto_now_add=True,
        help_text="Date et heure d'accord du moratoire",
    )
    date_fin = models.DateField(
        help_text="Date de fin du moratoire (date_accord + duree_jours)",
    )
    duree_jours = models.PositiveIntegerField(
        choices=DureeChoices.choices,
        default=DureeChoices.JOURS_30,
        help_text="Durée du moratoire en jours",
    )
    motif = models.TextField(
        blank=True,
        help_text="Motif du moratoire (ex: Difficultés financières, Raison familiale)",
    )
    accorde_par = models.ForeignKey(
        CoreIdentity,
        on_delete=models.PROTECT,
        related_name="moratoires_accordes",
        db_column="accorde_par_id",
        help_text="Identité de la personne ayant accordé le moratoire",
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutChoices.choices,
        default=StatutChoices.ACTIF,
        db_index=True,
    )
    created_by_role = models.CharField(
        max_length=50,
        help_text="Rôle actif lors de la création (pour audit)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "MORATOIRE"
        verbose_name = "Moratoire"
        verbose_name_plural = "Moratoires"
        ordering = ["-date_accord"]
        indexes = [
            models.Index(fields=["student", "statut"]),
            models.Index(fields=["date_fin"]),
        ]

    def __str__(self) -> str:
        return f"Moratoire {self.student.matricule_permanent} - {self.montant_reporte} FCFA - {self.statut}"

    def clean(self) -> None:
        """Valide les contraintes du moratoire."""
        from django.utils import timezone

        errors = {}

        # Vérifier que montant_reporte > 0
        if self.montant_reporte <= 0:
            errors["montant_reporte"] = "Le montant reporté doit être supérieur à 0."

        # Vérifier que date_fin > date_accord
        date_accord_date = None
        if self.date_accord:
            if isinstance(self.date_accord, str):
                from datetime import datetime
                try:
                    date_accord_date = datetime.fromisoformat(self.date_accord.replace("Z", "+00:00")).date()
                except (ValueError, AttributeError):
                    pass
            else:
                date_accord_date = self.date_accord.date() if hasattr(self.date_accord, "date") else None

        if self.date_fin and date_accord_date:
            if self.date_fin <= date_accord_date:
                errors["date_fin"] = "La date de fin doit être postérieure à la date d'accord."

        # Vérifier que montant_reporte <= solde de l'étudiant
        if self.student_id:
            try:
                student = StudentProfile.objects.get(id=self.student_id)
                if self.montant_reporte > abs(student.solde):
                    errors["montant_reporte"] = (
                        f"Le montant reporté ({self.montant_reporte}) ne peut pas dépasser "
                        f"le solde de l'étudiant ({abs(student.solde)})."
                    )
            except StudentProfile.DoesNotExist:
                errors["student"] = "Étudiant introuvable."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs) -> None:
        """Surcharge save pour appeler clean() et calculer date_fin si nécessaire."""
        from datetime import timedelta
        from django.utils import timezone

        # Calculer date_fin si non fournie
        if not self.date_fin and self.date_accord:
            self.date_fin = (self.date_accord + timedelta(days=self.duree_jours)).date()
        elif not self.date_fin:
            self.date_fin = (timezone.now() + timedelta(days=self.duree_jours)).date()

        # Valider avant sauvegarde
        self.full_clean()
        super().save(*args, **kwargs)


class Bourse(models.Model):
    """BOURSE - Bourse accordée à un étudiant."""

    class TypeBourse(models.TextChoices):
        MERITE = "Merite", "Mérite académique"
        BESOIN = "Besoin", "Besoins sociaux"
        TUTELLE = "Tutelle", "Bourse tutelle/université partenaire"
        EXTERNE = "Externe", "Bourse externe (ONG, État, etc.)"
        INTERNE = "Interne", "Bourse IUEC interne"

    class StatutChoices(models.TextChoices):
        ACTIVE = "Active", "Active"
        SUSPENDUE = "Suspendue", "Suspendue"
        TERMINEE = "Terminee", "Terminée"

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="bourses",
        db_column="student_id",
    )
    type_bourse = models.CharField(
        max_length=50,
        choices=TypeBourse.choices,
        help_text="Type de bourse accordée",
    )
    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Montant total de la bourse",
    )
    pourcentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Pourcentage de réduction (ex: 50.00 pour 50%)",
    )
    annee_academique = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="bourses",
        db_column="academic_year_id",
    )
    date_attribution = models.DateTimeField(
        auto_now_add=True,
        help_text="Date et heure d'attribution de la bourse",
    )
    date_fin_validite = models.DateField(
        null=True,
        blank=True,
        help_text="Date de fin de validité (ex: fin d'année ou semestre)",
    )
    motif = models.TextField(
        blank=True,
        help_text="Motif d'attribution de la bourse",
    )
    accorde_par = models.ForeignKey(
        CoreIdentity,
        on_delete=models.PROTECT,
        related_name="bourses_accordees",
        db_column="accorde_par_id",
        help_text="Identité de la personne ayant accordé la bourse",
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutChoices.choices,
        default=StatutChoices.ACTIVE,
        db_index=True,
        help_text="Statut de la bourse",
    )
    conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Conditions de maintien (ex: {'moyenne_min': 12, 'assiduite_min': 80})",
    )
    created_by_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Rôle actif lors de la création (pour audit)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "BOURSE"
        verbose_name = "Bourse"
        verbose_name_plural = "Bourses"
        ordering = ["-date_attribution"]
        indexes = [
            models.Index(fields=["student", "statut"]),
            models.Index(fields=["annee_academique", "statut"]),
            models.Index(fields=["date_fin_validite"]),
        ]

    def __str__(self) -> str:
        return f"Bourse {self.type_bourse} - {self.student.matricule_permanent} - {self.montant} FCFA - {self.statut}"

    def clean(self) -> None:
        """Valide les contraintes de la bourse."""
        from django.utils import timezone

        errors = {}

        # Vérifier que montant > 0
        if self.montant <= 0:
            errors["montant"] = "Le montant de la bourse doit être supérieur à 0."

        # Vérifier que date_fin_validite > date_attribution
        date_attribution_date = None
        if self.date_attribution:
            if isinstance(self.date_attribution, str):
                from datetime import datetime
                try:
                    date_attribution_date = datetime.fromisoformat(
                        self.date_attribution.replace("Z", "+00:00")
                    ).date()
                except (ValueError, AttributeError):
                    pass
            else:
                date_attribution_date = (
                    self.date_attribution.date()
                    if hasattr(self.date_attribution, "date")
                    else None
                )

        if self.date_fin_validite and date_attribution_date:
            if self.date_fin_validite <= date_attribution_date:
                errors["date_fin_validite"] = (
                    "La date de fin de validité doit être postérieure à la date d'attribution."
                )

        # Vérifier que pourcentage <= 100 si fourni
        if self.pourcentage is not None:
            if self.pourcentage > 100:
                errors["pourcentage"] = "Le pourcentage ne peut pas dépasser 100%."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs) -> None:
        """Surcharge save pour appeler clean()."""
        self.full_clean()
        super().save(*args, **kwargs)


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


@receiver(post_save, sender=Bourse)
def recalculate_student_balance_on_bourse_change(sender, instance: Bourse, created, **kwargs):
    """
    Recalcule le solde de l'étudiant après création/modification d'une bourse.
    - Si Active → recalcule solde = total_frais - montant_bourses_actives - paiements
    - Si solde <= 0 → finance_status = 'OK'
    - Si date_fin_validite dépassée → statut = 'Terminee' → recalcule solde sans bourse
    """
    from apps.finance.models import Invoice, Payment
    from apps.academic.services.frais_echeance_calculator import FraisEcheanceCalculator

    # Vérifier si la date de fin de validité est dépassée
    if instance.date_fin_validite and instance.date_fin_validite < date.today():
        if instance.statut != Bourse.StatutChoices.TERMINEE:
            # Mettre à jour le statut à Terminée
            Bourse.objects.filter(id=instance.id).update(
                statut=Bourse.StatutChoices.TERMINEE
            )
            instance.statut = Bourse.StatutChoices.TERMINEE

    # Si la bourse est active, recalculer le solde en tenant compte des bourses actives
    if instance.statut == Bourse.StatutChoices.ACTIVE:
        try:
            student = instance.student
            
            # Calculer le total des factures
            total_invoices = Invoice.objects.filter(
                identity_uuid=student.identity.id
            ).aggregate(
                total=models.Sum("total_amount")
            )["total"] or Decimal("0")
            
            # Calculer le total des paiements
            total_payments = Payment.objects.filter(
                invoice__identity_uuid=student.identity.id
            ).aggregate(
                total=models.Sum("amount")
            )["total"] or Decimal("0")
            
            # Calculer le total des bourses actives pour cet étudiant
            total_bourses_actives = Bourse.objects.filter(
                student=student,
                statut=Bourse.StatutChoices.ACTIVE
            ).aggregate(
                total=models.Sum("montant")
            )["total"] or Decimal("0")
            
            # Solde = factures - paiements - bourses actives
            new_solde = total_invoices - total_payments - total_bourses_actives
            
            # Mettre à jour le solde et le statut financier
            new_finance_status = "OK" if new_solde <= 0 else "Bloqué"
            
            # Utiliser update pour éviter de déclencher à nouveau le signal
            StudentProfile.objects.filter(id=student.id).update(
                solde=new_solde,
                finance_status=new_finance_status
            )
        except StudentProfile.DoesNotExist:
            pass
    else:
        # Si la bourse n'est plus active, recalculer sans cette bourse
        try:
            student = instance.student
            calculator = FraisEcheanceCalculator()
            calculator.update_solde_etudiant(student)
        except StudentProfile.DoesNotExist:
            pass

    # Audit trail : log attribution bourse avec rôle actif
    try:
        actor_email = instance.accorde_par.email if instance.accorde_par else ""
        active_role = instance.created_by_role or "ADMIN_SI"
        
        SysAuditLog.objects.create(
            action="BOURSE_ATTRIBUTED" if created else "BOURSE_UPDATED",
            entity_type="BOURSE",
            entity_id=uuid4(),
            actor_email=actor_email,
            active_role=active_role,
            payload={
                "bourse_id": str(instance.id),
                "student_id": str(instance.student.id),
                "student_matricule": instance.student.matricule_permanent,
                "type_bourse": instance.type_bourse,
                "montant": str(instance.montant),
                "pourcentage": str(instance.pourcentage) if instance.pourcentage else None,
                "statut": instance.statut,
                "annee_academique": instance.annee_academique.code if instance.annee_academique else None,
            },
        )
    except Exception as e:
        # Ne pas bloquer si l'audit log échoue
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Erreur création audit log pour bourse: {str(e)}")


class StudentRequest(models.Model):
    """STUDENT_REQUEST - Demandes administratives des étudiants."""

    class TypeDemande(models.TextChoices):
        RELEVE = "Releve", "Relevé de notes"
        CERTIFICAT = "Certificat", "Certificat de scolarité"
        MORATOIRE = "Moratoire", "Demande de moratoire"
        BOURSE = "Bourse", "Demande de bourse"
        AUTRE = "Autre", "Autre demande"

    class StatutChoices(models.TextChoices):
        EN_ATTENTE = "En_attente", "En attente"
        EN_COURS = "En_cours", "En cours de traitement"
        TRAITEE = "Traitee", "Traitée"
        REJETEE = "Rejetee", "Rejetée"

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="requests",
        db_column="student_id",
    )
    type_demande = models.CharField(
        max_length=50,
        choices=TypeDemande.choices,
        help_text="Type de demande",
    )
    motif = models.TextField(
        help_text="Motif de la demande",
    )
    piece_jointe = models.FileField(
        upload_to="student_requests/",
        null=True,
        blank=True,
        help_text="Pièce jointe optionnelle",
    )
    statut = models.CharField(
        max_length=20,
        choices=StatutChoices.choices,
        default=StatutChoices.EN_ATTENTE,
        db_index=True,
    )
    reponse = models.TextField(
        blank=True,
        help_text="Réponse de l'administration",
    )
    traite_par = models.ForeignKey(
        CoreIdentity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests_traitees",
        db_column="traite_par_id",
    )
    date_traitement = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date de traitement",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "STUDENT_REQUEST"
        verbose_name = "Demande étudiante"
        verbose_name_plural = "Demandes étudiantes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "statut"]),
            models.Index(fields=["type_demande", "statut"]),
        ]

    def __str__(self) -> str:
        return f"Demande {self.type_demande} - {self.student.matricule_permanent} ({self.statut})"
