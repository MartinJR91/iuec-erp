from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

import pytest

from apps.academic.services.note_calculator import (
    EvaluationItem,
    NoteCalculator,
    RegistrationPedagogical,
)


@dataclass(frozen=True)
class RegistrationStub(RegistrationPedagogical):
    identity_uuid: str
    items: Iterable[EvaluationItem]


def test_note_calculation_lmd_compensation_30_70() -> None:
    rules = {
        "grading_system": {
            "min_validate": 10,
            "compensation": True,
            "default_component_weights": {"TD": 0.3, "EXAM": 0.7},
        }
    }
    items = [
        EvaluationItem(ue_code="LMD_UE1", component="TD", score=Decimal("8"), weight=Decimal("0.3")),
        EvaluationItem(ue_code="LMD_UE1", component="EXAM", score=Decimal("12"), weight=Decimal("0.7")),
        EvaluationItem(ue_code="LMD_UE2", component="TD", score=Decimal("14"), weight=Decimal("0.3")),
        EvaluationItem(ue_code="LMD_UE2", component="EXAM", score=Decimal("15"), weight=Decimal("0.7")),
    ]
    registration = RegistrationStub(identity_uuid="abc", items=items)

    result = NoteCalculator(registration, rules).calculate()
    assert result.ue_results["LMD_UE1"].weighted_average == Decimal("10.80")
    assert result.ue_results["LMD_UE1"].validated is True
    assert result.semester_validated is True


def test_note_calculation_bts_without_compensation() -> None:
    rules = {
        "grading_system": {
            "min_validate": 12,
            "compensation": False,
            "default_component_weights": {"TD": 0.5, "EXAM": 0.5},
        }
    }
    items = [
        EvaluationItem(ue_code="BTS_UE1", component="TD", score=Decimal("10"), weight=Decimal("0.5")),
        EvaluationItem(ue_code="BTS_UE1", component="EXAM", score=Decimal("11"), weight=Decimal("0.5")),
        EvaluationItem(ue_code="BTS_UE2", component="TD", score=Decimal("14"), weight=Decimal("0.5")),
        EvaluationItem(ue_code="BTS_UE2", component="EXAM", score=Decimal("13"), weight=Decimal("0.5")),
    ]
    registration = RegistrationStub(identity_uuid="abc", items=items)

    result = NoteCalculator(registration, rules).calculate()
    assert result.ue_results["BTS_UE1"].validated is False
    assert result.semester_validated is False
