"""Tests pour core/rbac/checker.py"""
import pytest

from core.rbac.checker import ActionDecision, RBACChecker


class TestRBACChecker:
    """Tests pour RBACChecker"""

    def test_can_read_core_identity(self):
        """Test permission de lecture pour CORE_IDENTITY"""
        checker = RBACChecker()
        assert checker.can(role="RECTEUR", action="read", resource="CORE_IDENTITY")
        assert checker.can(role="ADMIN_SI", action="read", resource="CORE_IDENTITY")
        assert not checker.can(role="USER_STUDENT", action="read", resource="CORE_IDENTITY")

    def test_can_create_core_identity(self):
        """Test permission de création pour CORE_IDENTITY"""
        checker = RBACChecker()
        assert checker.can(role="ADMIN_SI", action="create", resource="CORE_IDENTITY")
        assert not checker.can(role="RECTEUR", action="create", resource="CORE_IDENTITY")

    def test_can_update_core_identity(self):
        """Test permission de mise à jour pour CORE_IDENTITY"""
        checker = RBACChecker()
        assert checker.can(role="ADMIN_SI", action="update", resource="CORE_IDENTITY")
        assert not checker.can(role="RECTEUR", action="update", resource="CORE_IDENTITY")

    def test_can_delete_core_identity(self):
        """Test permission de suppression pour CORE_IDENTITY"""
        checker = RBACChecker()
        assert checker.can(role="ADMIN_SI", action="delete", resource="CORE_IDENTITY")
        assert not checker.can(role="RECTEUR", action="delete", resource="CORE_IDENTITY")

    def test_can_read_invoice(self):
        """Test permission de lecture pour INVOICE"""
        checker = RBACChecker()
        assert checker.can(role="OPERATOR_FINANCE", action="read", resource="INVOICE")
        assert checker.can(role="DAF", action="read", resource="INVOICE")
        assert not checker.can(role="USER_STUDENT", action="read", resource="INVOICE")

    def test_can_create_invoice(self):
        """Test permission de création pour INVOICE"""
        checker = RBACChecker()
        assert checker.can(role="OPERATOR_FINANCE", action="create", resource="INVOICE")
        assert not checker.can(role="DAF", action="create", resource="INVOICE")

    def test_can_validate_finance_salary(self):
        """Test permission de validation pour FINANCE_SALARY"""
        checker = RBACChecker()
        assert checker.can(role="DAF", action="validate", resource="FINANCE_SALARY")
        assert checker.can(role="SG", action="validate", resource="FINANCE_SALARY")
        assert not checker.can(role="RECTEUR", action="validate", resource="FINANCE_SALARY")

    def test_decision_allowed(self):
        """Test ActionDecision avec permission accordée"""
        checker = RBACChecker()
        decision = checker.decision(
            role="ADMIN_SI", action="read", resource="CORE_IDENTITY"
        )
        assert decision.allowed is True
        assert isinstance(decision.masked_fields, set)

    def test_decision_denied(self):
        """Test ActionDecision avec permission refusée"""
        checker = RBACChecker()
        decision = checker.decision(
            role="USER_STUDENT", action="create", resource="CORE_IDENTITY"
        )
        assert decision.allowed is False

    def test_masked_fields_finance_salary(self):
        """Test masquage des champs pour FINANCE_SALARY"""
        checker = RBACChecker()
        # RECTEUR peut voir salary et balance
        decision = checker.decision(
            role="RECTEUR", action="read", resource="FINANCE_SALARY"
        )
        assert "salary" not in decision.masked_fields
        assert "balance" not in decision.masked_fields

        # USER_STUDENT ne peut pas voir salary et balance
        decision = checker.decision(
            role="USER_STUDENT", action="read", resource="FINANCE_SALARY"
        )
        assert "salary" in decision.masked_fields
        assert "balance" in decision.masked_fields

    def test_custom_matrix(self):
        """Test avec une matrice personnalisée"""
        custom_matrix = {
            "CUSTOM_RESOURCE": {
                "read": ["CUSTOM_ROLE"],
                "create": ["CUSTOM_ROLE"],
            }
        }
        checker = RBACChecker(matrix=custom_matrix)
        assert checker.can(role="CUSTOM_ROLE", action="read", resource="CUSTOM_RESOURCE")
        assert checker.can(role="CUSTOM_ROLE", action="create", resource="CUSTOM_RESOURCE")
        assert not checker.can(role="ADMIN_SI", action="read", resource="CUSTOM_RESOURCE")

    def test_masked_fields_no_masking_rules(self):
        """Test masquage sans règles de masquage"""
        checker = RBACChecker()
        decision = checker.decision(
            role="ADMIN_SI", action="read", resource="CORE_IDENTITY"
        )
        assert len(decision.masked_fields) == 0

    def test_masked_fields_invalid_structure(self):
        """Test masquage avec structure invalide"""
        invalid_matrix = {
            "INVALID": {
                "masking": "not_a_dict",
            }
        }
        checker = RBACChecker(matrix=invalid_matrix)
        decision = checker.decision(role="ANY", action="read", resource="INVALID")
        assert len(decision.masked_fields) == 0

    def test_action_decision_dataclass(self):
        """Test que ActionDecision est un dataclass immuable"""
        decision = ActionDecision(allowed=True, masked_fields={"field1", "field2"})
        assert decision.allowed is True
        assert "field1" in decision.masked_fields
        assert "field2" in decision.masked_fields

        # Test immutabilité (frozen=True)
        with pytest.raises(Exception):  # TypeError pour frozen dataclass
            decision.allowed = False
