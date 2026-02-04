from __future__ import annotations

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import (
    AcademicYear,
    Bourse,
    DemandeAdministrative,
    Faculty,
    Frais,
    Program,
    RegistrationAdmin,
    RegistrationPedagogical,
    StudentProfile,
    TeachingUnit,
    validate_academic_rules,
)


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "is_active")
    search_fields = ("code", "name")


class ProgramInlineForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ("code", "name", "academic_rules_json", "is_active")

    def clean_academic_rules_json(self):  # type: ignore[override]
        value = self.cleaned_data.get("academic_rules_json", {})
        try:
            validate_academic_rules(value)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages) from exc
        return value


class ProgramInline(admin.TabularInline):
    model = Program
    form = ProgramInlineForm
    extra = 0


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "tutelle", "doyen_uuid", "is_active")
    search_fields = ("code", "name", "tutelle")
    list_filter = ("is_active",)
    inlines = (ProgramInline,)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "faculty", "is_active")
    search_fields = ("code", "name", "faculty__code", "faculty__name")
    list_filter = ("is_active", "faculty")


class RegistrationPedagogicalInline(admin.TabularInline):
    model = RegistrationPedagogical
    extra = 0
    fields = ("teaching_unit", "status")
    readonly_fields = ()


class RegistrationAdminInline(admin.TabularInline):
    model = RegistrationAdmin
    extra = 0
    fields = ("academic_year", "level", "finance_status", "registration_date")
    readonly_fields = ("registration_date",)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "matricule_permanent",
        "identity_display",
        "current_program",
        "finance_status",
        "academic_status",
        "date_entree",
    )
    list_filter = ("finance_status", "academic_status", "current_program")
    search_fields = (
        "identity__first_name",
        "identity__last_name",
        "matricule_permanent",
        "identity__email",
    )
    readonly_fields = ("identity", "matricule_permanent")
    inlines = (RegistrationAdminInline,)

    def identity_display(self, obj):
        """Affiche le nom complet de l'identité."""
        if obj.identity:
            return f"{obj.identity.last_name} {obj.identity.first_name}"
        return "-"

    identity_display.short_description = "Identité"


@admin.register(RegistrationAdmin)
class RegistrationAdminAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "academic_year",
        "level",
        "finance_status",
        "registration_date",
    )
    list_filter = ("academic_year", "level", "finance_status")
    search_fields = (
        "student__matricule_permanent",
        "student__identity__first_name",
        "student__identity__last_name",
    )
    readonly_fields = ("registration_date",)
    inlines = (RegistrationPedagogicalInline,)


@admin.register(TeachingUnit)
class TeachingUnitAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "program", "credits", "is_active")
    search_fields = ("code", "name", "program__code")
    list_filter = ("is_active", "program")


@admin.register(RegistrationPedagogical)
class RegistrationPedagogicalAdmin(admin.ModelAdmin):
    list_display = ("registration_admin", "teaching_unit", "status")
    list_filter = ("status",)
    search_fields = (
        "registration_admin__student__matricule_permanent",
        "teaching_unit__code",
        "teaching_unit__name",
    )


@admin.register(Frais)
class FraisAdmin(admin.ModelAdmin):
    list_display = (
        "program",
        "academic_year",
        "inscription_total",
        "scolarite_total",
        "created_at",
    )
    list_filter = ("academic_year", "program__faculty")
    search_fields = ("program__code", "program__name", "academic_year")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Programme", {"fields": ("program", "academic_year")}),
        (
            "Frais d'inscription",
            {
                "fields": (
                    "inscription_iuec",
                    "inscription_tutelle",
                    "inscription_total",
                    "echeance_inscription",
                )
            },
        ),
        (
            "Frais de scolarité",
            {
                "fields": (
                    "scolarite_tranche1",
                    "scolarite_tranche2",
                    "scolarite_tranche3",
                    "scolarite_total",
                    "echeances_scolarite",
                )
            },
        ),
        ("Autres frais", {"fields": ("autres_frais",)}),
        ("Métadonnées", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(Bourse)
class BourseAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "type_bourse",
        "montant",
        "pourcentage",
        "annee_academique",
        "statut",
        "date_attribution",
        "date_fin_validite",
    )
    list_filter = ("type_bourse", "statut", "annee_academique")
    search_fields = (
        "student__matricule_permanent",
        "student__identity__first_name",
        "student__identity__last_name",
        "student__identity__email",
    )
    readonly_fields = ("date_attribution", "created_at", "updated_at")
    fieldsets = (
        (
            "Étudiant",
            {
                "fields": (
                    "student",
                    "annee_academique",
                )
            },
        ),
        (
            "Bourse",
            {
                "fields": (
                    "type_bourse",
                    "montant",
                    "pourcentage",
                    "statut",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "date_attribution",
                    "date_fin_validite",
                )
            },
        ),
        (
            "Détails",
            {
                "fields": (
                    "motif",
                    "accorde_par",
                    "conditions",
                    "created_by_role",
                )
            },
        ),
        ("Métadonnées", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )
