from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, Protocol


class RegistrationPedagogical(Protocol):
    """Interface minimale attendue pour calculer les notes."""

    identity_uuid: str
    items: Iterable["EvaluationItem"]


@dataclass(frozen=True)
class EvaluationItem:
    ue_code: str
    component: str  # ex: TD, EXAM, TP
    score: Decimal
    weight: Decimal


@dataclass(frozen=True)
class CalculatedUE:
    ue_code: str
    weighted_average: Decimal
    validated: bool


@dataclass(frozen=True)
class CalculationResult:
    ue_results: Dict[str, CalculatedUE]
    semester_average: Decimal
    year_average: Decimal
    semester_validated: bool
    year_validated: bool


class NoteCalculator:
    """Calcule les notes selon les règles JSON d’une filière."""

    def __init__(self, registration: RegistrationPedagogical, rules: Dict[str, object]):
        self._registration = registration
        self._rules = rules

    def calculate(self) -> CalculationResult:
        grading = self._rules.get("grading_system", {})
        min_validate = Decimal(str(grading.get("min_validate", 10)))
        compensation = bool(grading.get("compensation", True))
        elimination_mark = grading.get("elimination_mark")
        elimination_value = (
            Decimal(str(elimination_mark)) if elimination_mark is not None else None
        )

        ue_results: Dict[str, CalculatedUE] = {}
        total_weighted = Decimal("0")
        total_weights = Decimal("0")

        for ue_code, items in self._group_by_ue(self._registration.items).items():
            ue_avg = self._weighted_average(items, ue_code)
            ue_valid = ue_avg >= min_validate
            if elimination_value is not None:
                if self._has_blocking_note(items, elimination_value):
                    ue_valid = False
            ue_results[ue_code] = CalculatedUE(
                ue_code=ue_code, weighted_average=ue_avg, validated=ue_valid
            )
            total_weighted += ue_avg
            total_weights += Decimal("1")

        semester_average = (
            (total_weighted / total_weights).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if total_weights > 0
            else Decimal("0")
        )
        year_average = semester_average

        semester_validated = (
            semester_average >= min_validate if compensation else self._all_ue_validated(ue_results)
        )
        year_validated = semester_validated

        return CalculationResult(
            ue_results=ue_results,
            semester_average=semester_average,
            year_average=year_average,
            semester_validated=semester_validated,
            year_validated=year_validated,
        )

    def _group_by_ue(self, items: Iterable[EvaluationItem]) -> Dict[str, list[EvaluationItem]]:
        grouped: Dict[str, list[EvaluationItem]] = {}
        for item in items:
            grouped.setdefault(item.ue_code, []).append(item)
        return grouped

    def _weighted_average(self, items: Iterable[EvaluationItem], ue_code: str) -> Decimal:
        component_weights = self._component_weights_for_ue(ue_code)
        total = Decimal("0")
        weights = Decimal("0")
        for item in items:
            weight = self._resolve_weight(item, component_weights)
            total += item.score * weight
            weights += weight
        if weights == 0:
            return Decimal("0")
        return (total / weights).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _has_blocking_note(
        self, items: Iterable[EvaluationItem], elimination_mark: Decimal
    ) -> bool:
        for item in items:
            if item.component.upper() == "TP" and item.score < elimination_mark:
                return True
        return False

    def _all_ue_validated(self, ue_results: Dict[str, CalculatedUE]) -> bool:
        return all(result.validated for result in ue_results.values())

    def _component_weights_for_ue(self, ue_code: str) -> Dict[str, Decimal]:
        grading = self._rules.get("grading_system", {})
        default_weights = grading.get("default_component_weights", {})
        per_ue = grading.get("component_weights", {})
        raw = per_ue.get(ue_code, default_weights)
        if not isinstance(raw, dict):
            return {}
        return {str(key).upper(): Decimal(str(value)) for key, value in raw.items()}

    def _resolve_weight(
        self, item: EvaluationItem, component_weights: Dict[str, Decimal]
    ) -> Decimal:
        if component_weights:
            return component_weights.get(item.component.upper(), Decimal("0"))
        return item.weight
