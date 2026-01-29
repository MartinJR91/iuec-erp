from __future__ import annotations

from rest_framework import serializers

from apps.academic.models import (
    Evaluation,
    Faculty,
    Grade,
    GradeEntry,
    Program,
    RegistrationAdmin,
    RegistrationPedagogical,
    StudentProfile,
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


class EvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evaluation
        fields = "__all__"


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = "__all__"
