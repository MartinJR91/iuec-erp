from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from django.contrib.auth.models import User
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.academic.models import AcademicYear, Program, RegistrationAdmin, StudentProfile
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, IdentityRoleLink, RbacRoleDef


class TestStudentsAPI(APITestCase):
    """Tests pour l'API /api/students/ avec blocage intelligent."""

    def setUp(self):
        """Configuration initiale pour les tests."""
        self.client = APIClient()

        # Création des rôles
        self.recteur_role = RbacRoleDef.objects.create(
            code="RECTEUR",
            label="Recteur",
            is_system=True,
            is_active=True,
        )
        self.doyen_role = RbacRoleDef.objects.create(
            code="DOYEN",
            label="Doyen",
            is_system=True,
            is_active=True,
        )
        self.student_role = RbacRoleDef.objects.create(
            code="USER_STUDENT",
            label="Étudiant",
            is_system=True,
            is_active=True,
        )
        self.operator_finance_role = RbacRoleDef.objects.create(
            code="OPERATOR_FINANCE",
            label="Opérateur Finance",
            is_system=True,
            is_active=True,
        )
        self.scolarite_role = RbacRoleDef.objects.create(
            code="SCOLARITE",
            label="Scolarité",
            is_system=True,
            is_active=True,
        )

        # Création des identités
        self.recteur_identity = CoreIdentity.objects.create(
            email="recteur@iuec.cm",
            phone="+237600000001",
            first_name="Recteur",
            last_name="Test",
            is_active=True,
        )
        self.doyen_identity = CoreIdentity.objects.create(
            email="doyen@iuec.cm",
            phone="+237600000002",
            first_name="Doyen",
            last_name="Test",
            is_active=True,
        )
        self.student_identity = CoreIdentity.objects.create(
            email="student@iuec.cm",
            phone="+237600000003",
            first_name="Étudiant",
            last_name="Test",
            is_active=True,
        )
        self.operator_finance_identity = CoreIdentity.objects.create(
            email="finance@iuec.cm",
            phone="+237600000004",
            first_name="Finance",
            last_name="Test",
            is_active=True,
        )
        self.scolarite_identity = CoreIdentity.objects.create(
            email="scolarite@iuec.cm",
            phone="+237600000005",
            first_name="Scolarité",
            last_name="Test",
            is_active=True,
        )

        # Création des utilisateurs Django
        self.recteur_user = User.objects.create_user(
            username="recteur@iuec.cm", email="recteur@iuec.cm", password="test123"
        )
        self.doyen_user = User.objects.create_user(
            username="doyen@iuec.cm", email="doyen@iuec.cm", password="test123"
        )
        self.student_user = User.objects.create_user(
            username="student@iuec.cm", email="student@iuec.cm", password="test123"
        )
        self.operator_finance_user = User.objects.create_user(
            username="finance@iuec.cm", email="finance@iuec.cm", password="test123"
        )
        self.scolarite_user = User.objects.create_user(
            username="scolarite@iuec.cm", email="scolarite@iuec.cm", password="test123"
        )

        # Lien des rôles (créés dans setUp, mais on peut les recréer si nécessaire)
        IdentityRoleLink.objects.get_or_create(
            identity=self.recteur_identity,
            role=self.recteur_role,
            defaults={"is_active": True},
        )
        IdentityRoleLink.objects.get_or_create(
            identity=self.doyen_identity,
            role=self.doyen_role,
            defaults={"is_active": True},
        )
        IdentityRoleLink.objects.create(
            identity=self.student_identity,
            role=self.student_role,
            is_active=True,
        )
        IdentityRoleLink.objects.create(
            identity=self.operator_finance_identity,
            role=self.operator_finance_role,
            is_active=True,
        )
        IdentityRoleLink.objects.create(
            identity=self.scolarite_identity,
            role=self.scolarite_role,
            is_active=True,
        )

        # Création d'une faculté et d'un programme
        from apps.academic.models import Faculty

        self.faculty = Faculty.objects.create(
            code="FASE",
            name="Faculté des Sciences Économiques",
            doyen_uuid=self.doyen_identity,
            is_active=True,
        )
        self.program = Program.objects.create(
            code="ECO",
            name="Économie",
            faculty=self.faculty,
            is_active=True,
        )

        # Création d'une année académique
        self.academic_year = AcademicYear.objects.create(
            code="2024-2025",
            label="Année académique 2024-2025",
            is_active=True,
        )

        # Création d'un profil étudiant
        self.student_profile = StudentProfile.objects.create(
            identity=self.student_identity,
            matricule_permanent="ST001",
            date_entree=timezone.now().date(),
            current_program=self.program,
            finance_status=StudentProfile.FinanceStatus.OK,
        )

    def test_student_list_recteur(self):
        """Test GET /api/students/ pour RECTEUR → 200 + tous les étudiants."""
        self.client.force_authenticate(user=self.recteur_user)
        response = self.client.get("/api/students/", HTTP_X_ROLE_ACTIVE="RECTEUR")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Le ViewSet retourne une liste directement
        self.assertIsInstance(response.data, list)
        self.assertGreaterEqual(len(response.data), 1)
        # Vérifie que l'étudiant créé est dans la liste
        student_ids = [str(s["id"]) for s in response.data]
        self.assertIn(str(self.student_profile.id), student_ids)

    def test_student_list_doyen(self):
        """Test GET /api/students/ pour DOYEN → 200 + étudiants de sa faculté."""
        # Le doyen doit avoir le rôle DOYEN lié à son identité (déjà créé dans setUp)
        self.client.force_authenticate(user=self.doyen_user)
        response = self.client.get("/api/students/", HTTP_X_ROLE_ACTIVE="DOYEN")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Le ViewSet retourne une liste directement
        self.assertIsInstance(response.data, list)
        # Le doyen doit voir l'étudiant de sa faculté
        student_ids = [str(s["id"]) for s in response.data]
        self.assertIn(str(self.student_profile.id), student_ids)

    def test_student_self_access(self):
        """Test GET /api/students/<uuid>/ pour étudiant connecté → 200."""
        self.client.force_authenticate(user=self.student_user)
        response = self.client.get(
            f"/api/students/{self.student_profile.id}/",
            HTTP_X_ROLE_ACTIVE="USER_STUDENT",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("student", response.data)
        self.assertIn("registrations", response.data)
        self.assertIn("finance", response.data)
        self.assertEqual(
            str(response.data["student"]["id"]), str(self.student_profile.id)
        )

    def test_student_inscription_blocked(self):
        """Test POST /api/students/ avec solde négatif → 400."""
        # Créer une facture non payée pour bloquer l'inscription
        from apps.finance.models import Invoice

        blocked_identity = CoreIdentity.objects.create(
            email="blocked@iuec.cm",
            phone="+237600000006",
            first_name="Bloqué",
            last_name="Test",
            is_active=True,
        )

        invoice = Invoice.objects.create(
            identity_uuid=blocked_identity.id,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            status=Invoice.STATUS_ISSUED,
            program_code="ECO",
            line_items=[{"item": "Frais de scolarité", "amount": 100000}],
        )
        # S'assurer que le total_amount est bien calculé
        invoice.save()

        self.client.force_authenticate(user=self.scolarite_user)
        payload = {
            "identity_uuid": str(blocked_identity.id),
            "matricule_permanent": "ST002",
            "date_entree": timezone.now().date().isoformat(),
            "program_id": str(self.program.id),
            "academic_year_id": str(self.academic_year.id),
            "level": "L1",
        }
        response = self.client.post(
            "/api/students/", payload, HTTP_X_ROLE_ACTIVE="SCOLARITE", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("solde négatif", response.data["detail"].lower())

    def test_student_inscription_success(self):
        """Test POST /api/students/ avec données valides → 201."""
        new_identity = CoreIdentity.objects.create(
            email="newstudent@iuec.cm",
            phone="+237600000007",
            first_name="Nouveau",
            last_name="Étudiant",
            is_active=True,
        )

        self.client.force_authenticate(user=self.scolarite_user)
        payload = {
            "identity_uuid": str(new_identity.id),
            "matricule_permanent": "ST003",
            "date_entree": timezone.now().date().isoformat(),
            "program_id": str(self.program.id),
            "academic_year_id": str(self.academic_year.id),
            "level": "L1",
        }
        response = self.client.post(
            "/api/students/", payload, HTTP_X_ROLE_ACTIVE="SCOLARITE", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("student_id", response.data)
        self.assertIn("registration_id", response.data)

    def test_student_update_finance_status(self):
        """Test PUT /api/students/<uuid>/finance-status/ pour OPERATOR_FINANCE → 200 + log audit."""
        self.client.force_authenticate(user=self.operator_finance_user)
        payload = {"finance_status": "Moratoire"}
        # Utiliser l'ID du profil étudiant
        student_id = self.student_profile.id
        response = self.client.put(
            f"/api/students/{student_id}/finance-status/",
            payload,
            HTTP_X_ROLE_ACTIVE="OPERATOR_FINANCE",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"Response: {response.data if hasattr(response, 'data') else response.content}")
        self.assertIn("old_status", response.data)
        self.assertIn("new_status", response.data)

        # Vérifie que le statut a été mis à jour
        self.student_profile.refresh_from_db()
        self.assertEqual(
            self.student_profile.finance_status,
            "Moratoire",
        )

        # Vérifie le log audit
        from identity.models import SysAuditLog

        audit_log = SysAuditLog.objects.filter(
            action="FINANCE_STATUS_UPDATED",
            entity_id=self.student_profile.id,
        ).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.active_role, "OPERATOR_FINANCE")
        self.assertIn("old_status", audit_log.payload)
        self.assertIn("new_status", audit_log.payload)

    def test_student_update_finance_status_unauthorized(self):
        """Test PUT /api/students/<uuid>/finance-status/ sans OPERATOR_FINANCE → 403."""
        self.client.force_authenticate(user=self.student_user)
        payload = {"finance_status": StudentProfile.FinanceStatus.MORATORIUM}
        response = self.client.put(
            f"/api/students/{self.student_profile.id}/finance-status/",
            payload,
            HTTP_X_ROLE_ACTIVE="USER_STUDENT",
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_list_unauthorized_role(self):
        """Test GET /api/students/ avec rôle non autorisé → 403."""
        unauthorized_user = User.objects.create_user(
            username="unauthorized@iuec.cm",
            email="unauthorized@iuec.cm",
            password="test123",
        )
        self.client.force_authenticate(user=unauthorized_user)
        response = self.client.get("/api/students/", HTTP_X_ROLE_ACTIVE="UNKNOWN_ROLE")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
