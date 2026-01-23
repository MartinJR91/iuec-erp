from __future__ import annotations

from typing import Any, Dict

from django.db import models


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
    label = models.CharField(max_length=150)
    academic_rules_json = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)

    objects = ProgramManager()

    class Meta:
        db_table = "PROGRAM"

    def __str__(self) -> str:
        return f"{self.code} - {self.label}"


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
