from __future__ import annotations

from rest_framework import serializers

from apps.academic.models import (
    AcademicYear,
    Bourse,
    CourseElement,
    DemandeAdministrative,
    Evaluation,
    Faculty,
    Grade,
    GradeEntry,
    Moratoire,
    Program,
    RegistrationAdmin,
    RegistrationPedagogical,
    StudentProfile,
    StudentRequest,
    TeachingUnit,
    validate_academic_rules,
)
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, IdentityRoleLink


class CoreIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreIdentity
        fields = "__all__"


class IdentityRoleLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityRoleLink
        fields = "__all__"


class GradeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeEntry
        fields = "__all__"


class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ("id", "code", "name", "academic_rules_json", "is_active", "faculty")

    def validate_academic_rules_json(self, value):  # type: ignore[override]
        validate_academic_rules(value)
        return value


class FacultySerializer(serializers.ModelSerializer):
    programs = ProgramSerializer(many=True, read_only=True)
    doyen_uuid = serializers.PrimaryKeyRelatedField(
        queryset=CoreIdentity.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Faculty
        fields = (
            "id",
            "code",
            "name",
            "doyen_uuid",
            "tutelle",
            "is_active",
            "programs",
        )


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"


class RegistrationPedagogicalSerializer(serializers.ModelSerializer):
    """Serializer pour REGISTRATION_PEDAGOGICAL."""

    class Meta:
        model = RegistrationPedagogical
        fields = (
            "id",
            "registration_admin",
            "teaching_unit",
            "status",
        )
        read_only_fields = ("id",)


class RegistrationAdminSerializer(serializers.ModelSerializer):
    """Serializer pour REGISTRATION_ADMIN."""

    student = serializers.PrimaryKeyRelatedField(read_only=True)
    program_code = serializers.SerializerMethodField()
    program_name = serializers.SerializerMethodField()

    def get_program_code(self, obj):  # type: ignore[override]
        if obj.student and obj.student.current_program:
            return obj.student.current_program.code
        return None

    def get_program_name(self, obj):  # type: ignore[override]
        if obj.student and obj.student.current_program:
            return obj.student.current_program.name
        return None

    class Meta:
        model = RegistrationAdmin
        fields = (
            "id",
            "student",
            "academic_year",
            "level",
            "finance_status",
            "registration_date",
            "program_code",
            "program_name",
        )
        read_only_fields = ("id", "student", "registration_date")


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializer pour STUDENT_PROFILE avec identity nested et registrations."""

    email = serializers.EmailField(source="identity.email", read_only=True)
    identity_nested = CoreIdentitySerializer(source="identity", read_only=True)
    registrations_admin = RegistrationAdminSerializer(many=True, read_only=True)
    program_code = serializers.SerializerMethodField()
    program_name = serializers.SerializerMethodField()
    faculty_code = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    finance_status_effective = serializers.SerializerMethodField()

    def get_program_code(self, obj):  # type: ignore[override]
        return obj.current_program.code if obj.current_program else None

    def get_program_name(self, obj):  # type: ignore[override]
        return obj.current_program.name if obj.current_program else None

    def get_faculty_code(self, obj):  # type: ignore[override]
        return obj.current_program.faculty.code if obj.current_program and obj.current_program.faculty else None

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "identity",
            "identity_nested",
            "email",
            "matricule_permanent",
            "date_entree",
            "current_program",
            "program_code",
            "program_name",
            "faculty_code",
            "finance_status",
            "finance_status_effective",
            "academic_status",
            "balance",
            "registrations_admin",
        )
        read_only_fields = (
            "id",
            "identity",
            "identity_nested",
            "email",
            "matricule_permanent",
            "registrations_admin",
        )

    def get_balance(self, obj):  # type: ignore[override]
        """Récupère le solde depuis l'annotation calculée ou calcule à la volée."""
        # Utilise calculated_balance si disponible (depuis annotation Subquery)
        if hasattr(obj, "calculated_balance"):
            return float(obj.calculated_balance)
        # Sinon, utilise le contexte (pour compatibilité)
        balances = self.context.get("balances", {})
        if balances and obj.identity_id in balances:
            return float(balances[obj.identity_id])
        # En dernier recours, utilise le solde du modèle (calculé via signal)
        return float(obj.solde) if hasattr(obj, "solde") else 0.0

    def get_finance_status_effective(self, obj):  # type: ignore[override]
        balance = self.get_balance(obj)
        # Utilise les valeurs string directement (OK, Bloqué, Moratoire)
        if obj.finance_status == "Moratoire":
            return "Moratoire"
        if balance and balance > 0:
            return "Bloqué"
        return "OK"


class CourseElementSerializer(serializers.ModelSerializer):
    """Serializer pour CourseElement."""
    
    class Meta:
        model = CourseElement
        fields = ("id", "code", "name", "teaching_unit", "is_active")
        read_only_fields = ("id",)


class EvaluationSerializer(serializers.ModelSerializer):
    """Serializer pour Evaluation avec relations."""
    
    course_element_code = serializers.CharField(source="course_element.code", read_only=True)
    course_element_name = serializers.CharField(source="course_element.name", read_only=True)
    teaching_unit_code = serializers.SerializerMethodField()
    
    def get_teaching_unit_code(self, obj) -> str | None:
        """Récupère le code de l'UE depuis course_element."""
        if obj.course_element and obj.course_element.teaching_unit:
            return obj.course_element.teaching_unit.code
        return None
    
    class Meta:
        model = Evaluation
        fields = (
            "id",
            "course_element",
            "course_element_code",
            "course_element_name",
            "teaching_unit_code",
            "type",
            "weight",
            "max_score",
            "session_date",
            "is_closed",
        )
        read_only_fields = ("id", "course_element_code", "course_element_name", "teaching_unit_code")


class GradeSerializer(serializers.ModelSerializer):
    """Serializer pour Grade avec relations."""
    
    evaluation_type = serializers.CharField(source="evaluation.type", read_only=True)
    evaluation_course_element = serializers.CharField(
        source="evaluation.course_element.code", read_only=True
    )
    student_matricule = serializers.CharField(source="student.matricule_permanent", read_only=True)
    student_email = serializers.CharField(source="student.identity.email", read_only=True)
    teacher_email = serializers.CharField(source="teacher.email", read_only=True, allow_null=True)
    
    class Meta:
        model = Grade
        fields = (
            "id",
            "evaluation",
            "evaluation_type",
            "evaluation_course_element",
            "student",
            "student_matricule",
            "student_email",
            "value",
            "is_absent",
            "teacher",
            "teacher_email",
            "created_by_role",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class BulkGradeSerializer(serializers.Serializer):
    """Serializer pour la mise à jour en masse des notes."""
    
    evaluation_id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    value = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    is_absent = serializers.BooleanField(default=False)


class MoratoireSerializer(serializers.ModelSerializer):
    """Serializer pour Moratoire."""
    
    student_matricule = serializers.CharField(source="student.matricule_permanent", read_only=True)
    student_nom = serializers.SerializerMethodField()
    accorde_par_email = serializers.CharField(source="accorde_par.email", read_only=True)
    
    def get_student_nom(self, obj) -> str:
        """Retourne le nom complet de l'étudiant."""
        if obj.student and obj.student.identity:
            return f"{obj.student.identity.last_name} {obj.student.identity.first_name}"
        return ""
    
    class Meta:
        model = Moratoire
        fields = (
            "id",
            "student",
            "student_matricule",
            "student_nom",
            "montant_reporte",
            "date_accord",
            "date_fin",
            "duree_jours",
            "motif",
            "accorde_par",
            "accorde_par_email",
            "statut",
            "created_by_role",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "date_accord", "created_at", "updated_at", "student_matricule", "student_nom", "accorde_par_email")


class BourseSerializer(serializers.ModelSerializer):
    """Serializer pour Bourse."""
    
    student_matricule = serializers.CharField(source="student.matricule_permanent", read_only=True)
    student_nom = serializers.SerializerMethodField()
    accorde_par_email = serializers.CharField(source="accorde_par.email", read_only=True)
    annee_academique_code = serializers.CharField(source="annee_academique.code", read_only=True)
    annee_academique_label = serializers.CharField(source="annee_academique.label", read_only=True)
    
    def get_student_nom(self, obj) -> str:
        """Retourne le nom complet de l'étudiant."""
        if obj.student and obj.student.identity:
            return f"{obj.student.identity.last_name} {obj.student.identity.first_name}"
        return ""
    
    class Meta:
        model = Bourse
        fields = (
            "id",
            "student",
            "student_matricule",
            "student_nom",
            "type_bourse",
            "montant",
            "pourcentage",
            "annee_academique",
            "annee_academique_code",
            "annee_academique_label",
            "date_attribution",
            "date_fin_validite",
            "motif",
            "accorde_par",
            "accorde_par_email",
            "statut",
            "conditions",
            "created_by_role",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "date_attribution",
            "created_at",
            "updated_at",
            "student_matricule",
            "student_nom",
            "accorde_par_email",
            "annee_academique_code",
            "annee_academique_label",
        )


class BourseCreateSerializer(serializers.Serializer):
    """Serializer pour la création d'une bourse via POST /api/students/<uuid>/bourse/."""
    
    type_bourse = serializers.ChoiceField(choices=Bourse.TypeBourse.choices)
    montant = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    pourcentage = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    annee_academique = serializers.PrimaryKeyRelatedField(queryset=AcademicYear.objects.all())
    date_fin_validite = serializers.DateField(required=False, allow_null=True)
    motif = serializers.CharField(required=False, allow_blank=True)
    conditions = serializers.JSONField(required=False, default=dict)
    
    def validate(self, attrs):  # type: ignore[override]
        """Valide que montant ou pourcentage est fourni."""
        montant = attrs.get("montant")
        pourcentage = attrs.get("pourcentage")
        
        if not montant and not pourcentage:
            raise serializers.ValidationError("Il faut fournir soit 'montant' soit 'pourcentage'.")
        
        if montant and montant <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0.")
        
        if pourcentage and (pourcentage <= 0 or pourcentage > 100):
            raise serializers.ValidationError("Le pourcentage doit être entre 0 et 100.")
        
        return attrs


class StudentRequestSerializer(serializers.ModelSerializer):
    """Serializer pour StudentRequest."""

    student_matricule = serializers.CharField(source="student.matricule_permanent", read_only=True)
    student_nom = serializers.SerializerMethodField()
    traite_par_email = serializers.CharField(source="traite_par.email", read_only=True)

    def get_student_nom(self, obj) -> str:
        """Retourne le nom complet de l'étudiant."""
        if obj.student and obj.student.identity:
            return f"{obj.student.identity.last_name} {obj.student.identity.first_name}"
        return ""

    class Meta:
        model = StudentRequest
        fields = (
            "id",
            "student",
            "student_matricule",
            "student_nom",
            "type_demande",
            "motif",
            "piece_jointe",
            "statut",
            "reponse",
            "traite_par",
            "traite_par_email",
            "date_traitement",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "statut",
            "reponse",
            "traite_par",
            "traite_par_email",
            "date_traitement",
            "created_at",
            "updated_at",
            "student_matricule",
            "student_nom",
        )


class StudentRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de StudentRequest par l'étudiant."""

    class Meta:
        model = StudentRequest
        fields = (
            "type_demande",
            "motif",
            "piece_jointe",
        )


class DemandeAdministrativeSerializer(serializers.ModelSerializer):
    """Serializer pour DemandeAdministrative."""

    student_matricule = serializers.CharField(source="student.matricule_permanent", read_only=True)
    student_nom = serializers.SerializerMethodField()
    traite_par_email = serializers.CharField(source="traite_par.email", read_only=True)

    def get_student_nom(self, obj) -> str:
        """Retourne le nom complet de l'étudiant."""
        if obj.student and obj.student.identity:
            return f"{obj.student.identity.last_name} {obj.student.identity.first_name}"
        return ""

    class Meta:
        model = DemandeAdministrative
        fields = (
            "id",
            "student",
            "student_matricule",
            "student_nom",
            "type_demande",
            "motif",
            "statut",
            "date_soumission",
            "date_traitement",
            "traite_par",
            "traite_par_email",
            "piece_jointe",
            "commentaire",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "statut",
            "date_soumission",
            "date_traitement",
            "traite_par",
            "traite_par_email",
            "commentaire",
            "created_at",
            "updated_at",
            "student_matricule",
            "student_nom",
        )


class DemandeAdministrativeCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de DemandeAdministrative par l'étudiant."""

    class Meta:
        model = DemandeAdministrative
        fields = (
            "type_demande",
            "motif",
            "piece_jointe",
        )
