from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set


@dataclass(frozen=True)
class ActionDecision:
    allowed: bool
    masked_fields: Set[str]


class RBACChecker:
    """Vérifie les permissions RBAC et applique le masquage de données."""

    def __init__(self, matrix: Optional[Dict[str, Dict[str, Iterable[str]]]] = None):
        self._matrix = matrix or self._default_matrix()

    def can(self, *, role: str, action: str, resource: str) -> bool:
        allowed_roles = self._matrix.get(resource, {}).get(action, [])
        return role in set(allowed_roles)

    def decision(self, *, role: str, action: str, resource: str) -> ActionDecision:
        allowed = self.can(role=role, action=action, resource=resource)
        masked_fields = self._masked_fields(role=role, resource=resource)
        return ActionDecision(allowed=allowed, masked_fields=masked_fields)

    def _masked_fields(self, *, role: str, resource: str) -> Set[str]:
        masking_rules = self._matrix.get(resource, {}).get("masking", {})
        if not isinstance(masking_rules, dict):
            return set()
        field_roles = masking_rules.get("fields", {})
        if not isinstance(field_roles, dict):
            return set()
        masked: Set[str] = set()
        for field, roles in field_roles.items():
            roles_set = set(roles) if isinstance(roles, Iterable) else set()
            if role not in roles_set:
                masked.add(str(field))
        return masked

    @staticmethod
    def _default_matrix() -> Dict[str, Dict[str, Iterable[str]]]:
        return {
            "CORE_IDENTITY": {
                "read": ["ADMIN_SI", "RECTEUR", "DAF", "SG"],
                "create": ["ADMIN_SI"],
                "update": ["ADMIN_SI"],
                "delete": ["ADMIN_SI"],
            },
            "INVOICE": {
                "read": ["OPERATOR_FINANCE", "DAF", "SG"],
                "create": ["OPERATOR_FINANCE"],
                "update": ["OPERATOR_FINANCE"],
                "delete": ["ADMIN_SI"],
            },
            "FINANCE_SALARY": {
                "read": ["RECTEUR", "DAF", "SG"],
                "validate": ["DAF", "SG"],
                "masking": {
                    "fields": {
                        "salary": ["RECTEUR", "DAF", "SG"],
                        "balance": ["RECTEUR", "DAF", "SG"],
                    }
                },
            },
        }
