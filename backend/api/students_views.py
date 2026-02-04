from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db.models import DecimalField, F, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.academic.models import AcademicYear, Bourse, Moratoire, Program, RegistrationAdmin, StudentProfile
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, SysAuditLog

from .mixins import ScopeFilterMixin, _get_identity_from_request
from .permissions import BoursePermission, SoDPermission, StudentPermission, UserStudentPermission
from .serializers import BourseCreateSerializer, BourseSerializer, MoratoireSerializer, RegistrationAdminSerializer, StudentProfileSerializer


class StudentsViewSet(ScopeFilterMixin, ModelViewSet):
    """
    ViewSet complet pour la gestion des étudiants avec permissions et logique métier.

    GET /api/students/ : Liste avec solde annoté, filtrée par rôle actif
    GET /api/students/<uuid>/ : Détail avec profil + inscriptions + statut finance
    POST /api/students/ : Inscription annuelle (vérifie finance_status)
    PUT /api/students/<uuid>/finance-status/ : Mise à jour statut finance (OPERATOR_FINANCE only)
    POST /api/students/<uuid>/validate-registration/ : Valider inscription (VALIDATOR_ACAD only)
    """

    queryset = StudentProfile.objects.all()
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, UserStudentPermission, StudentPermission, SoDPermission]

    def get_queryset(self):  # type: ignore[override]
        """
        Filtre le queryset selon le rôle actif et le scope.
        Annote le solde calculé via Subquery.
        """
        queryset = super().get_queryset()
        role_active = getattr(self.request, "role_active", None)

        if not role_active:
            return queryset.none()

        # Annotation du solde calculé via Subquery
        # Subquery pour calculer le total des factures par identité
        invoices_subquery = (
            Invoice.objects.filter(identity_uuid=OuterRef("identity_id"))
            .values("identity_uuid")
            .annotate(total=Sum("total_amount"))
            .values("total")[:1]
        )

        # Subquery pour calculer le total des paiements par identité
        payments_subquery = (
            Payment.objects.filter(invoice__identity_uuid=OuterRef("identity_id"))
            .values("invoice__identity_uuid")
            .annotate(total=Sum("amount"))
            .values("total")[:1]
        )

        queryset = queryset.select_related(
            "identity", "current_program", "current_program__faculty"
        ).prefetch_related("registrations_admin", "registrations_admin__pedagogical").annotate(
            total_invoices=Coalesce(
                Subquery(invoices_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            ),
            total_payments=Coalesce(
                Subquery(payments_subquery, output_field=DecimalField(max_digits=12, decimal_places=2)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        ).annotate(
            calculated_balance=F("total_invoices") - F("total_payments")
        )

        # USER_STUDENT : seulement son propre profil
        if role_active == "USER_STUDENT":
            identity = _get_identity_from_request(self.request)
            if identity:
                queryset = queryset.filter(identity=identity)
            else:
                queryset = queryset.none()
            return queryset

        # Utilise le mixin pour filtrer par scope
        queryset = self.filter_by_scope(queryset)

        # Filtre supplémentaire pour OPERATOR_FINANCE (seulement bloqués/moratoires)
        # Note: Ce filtre est appliqué uniquement pour la liste, pas pour le détail
        if role_active == "OPERATOR_FINANCE" and self.action == "list":
            queryset = queryset.filter(
                finance_status__in=["Bloqué", "Moratoire"]
            )

        return queryset

    def list(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """GET list : retourne la liste avec solde annoté."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """GET detail : profil + inscriptions + statut finance."""
        instance = self.get_object()
        # Utilise le solde annoté si disponible, sinon calcule
        balance = getattr(instance, "calculated_balance", None)
        if balance is None:
            balance = self._calculate_balance_for_identity(instance.identity_id)

        serializer = self.get_serializer(instance)
        registrations = RegistrationAdmin.objects.filter(student=instance).select_related(
            "academic_year"
        ).prefetch_related("pedagogical")
        registrations_serializer = RegistrationAdminSerializer(registrations, many=True)

        return Response(
            {
                "student": serializer.data,
                "registrations": registrations_serializer.data,
                "finance": {
                    "balance": float(balance),
                    "status": instance.finance_status,
                    "status_effective": self._get_effective_finance_status(
                        instance, balance
                    ),
                },
            },
            status=status.HTTP_200_OK,
        )

    def update(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """PUT : bloqué pour USER_STUDENT."""
        role_active = getattr(request, "role_active", None)
        if role_active == "USER_STUDENT":
            return Response(
                {"detail": "Accès réservé aux rôles administratifs. Vous ne pouvez pas modifier votre profil."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """PATCH : bloqué pour USER_STUDENT."""
        role_active = getattr(request, "role_active", None)
        if role_active == "USER_STUDENT":
            return Response(
                {"detail": "Accès réservé aux rôles administratifs. Vous ne pouvez pas modifier votre profil."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """DELETE : bloqué pour USER_STUDENT."""
        role_active = getattr(request, "role_active", None)
        if role_active == "USER_STUDENT":
            return Response(
                {"detail": "Accès réservé aux rôles administratifs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    def create(self, request: HttpRequest, *args, **kwargs):  # type: ignore[override]
        """
        POST inscription annuelle : crée automatiquement l'identité si nécessaire et génère le matricule.

        Payload requis:
        - first_name, last_name, email, phone (champs identité)
        - date_naissance (optionnel, stocké dans metadata)
        - sexe (optionnel, stocké dans metadata)
        - program_id
        - academic_year_id
        - level
        - finance_status (optionnel, défaut "OK")
        """
        from datetime import date

        role_active = getattr(request, "role_active", None)
        if role_active not in {"SCOLARITE", "OPERATOR_SCOLA", "ADMIN_SI", "RECTEUR"}:
            return Response(
                {"detail": "Création d'inscription réservée à SCOLARITE, OPERATOR_SCOLA, ADMIN_SI ou RECTEUR."},
                status=status.HTTP_403_FORBIDDEN,
            )

        payload = request.data
        
        # Champs identité requis
        first_name = payload.get("first_name", "").strip()
        last_name = payload.get("last_name", "").strip()
        email = payload.get("email", "").strip().lower()
        phone = payload.get("phone", "").strip()
        date_naissance = payload.get("date_naissance")  # Optionnel
        sexe = payload.get("sexe")  # Optionnel
        
        # Champs académiques requis
        program_id = payload.get("program_id")
        academic_year_id = payload.get("academic_year_id")
        level = payload.get("level")
        finance_status = payload.get("finance_status", "OK")

        # Vérification des champs requis
        missing_fields = []
        if not first_name:
            missing_fields.append("first_name")
        if not last_name:
            missing_fields.append("last_name")
        if not email:
            missing_fields.append("email")
        if not phone:
            missing_fields.append("phone")
        if not program_id:
            missing_fields.append("program_id")
        if not academic_year_id:
            missing_fields.append("academic_year_id")
        if not level:
            missing_fields.append("level")
        
        if missing_fields:
            return Response(
                {"detail": f"Champs requis manquants: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérification format email
        if "@" not in email:
            return Response(
                {"detail": "Format d'email invalide."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Chercher ou créer l'identité (par email ou téléphone)
        identity = None
        if email:
            identity = CoreIdentity.objects.filter(email__iexact=email, is_active=True).first()
        if not identity and phone:
            identity = CoreIdentity.objects.filter(phone=phone, is_active=True).first()
        
        # Créer l'identité si elle n'existe pas
        if not identity:
            # Vérifier que l'email n'existe pas (même inactif)
            if CoreIdentity.objects.filter(email__iexact=email).exists():
                return Response(
                    {"detail": "Un compte avec cet email existe déjà (inactif)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Vérifier que le téléphone n'existe pas (même inactif)
            if phone and CoreIdentity.objects.filter(phone=phone).exists():
                return Response(
                    {"detail": "Un compte avec ce téléphone existe déjà (inactif)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Créer la nouvelle identité
            metadata = {}
            if date_naissance:
                metadata["date_naissance"] = date_naissance
            if sexe:
                metadata["sexe"] = sexe
            
            identity = CoreIdentity.objects.create(
                email=email,
                phone=phone,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                metadata=metadata,
            )
        else:
            # Mettre à jour l'identité existante si nécessaire
            updated = False
            if identity.first_name != first_name:
                identity.first_name = first_name
                updated = True
            if identity.last_name != last_name:
                identity.last_name = last_name
                updated = True
            if identity.phone != phone:
                identity.phone = phone
                updated = True
            if date_naissance or sexe:
                if not identity.metadata:
                    identity.metadata = {}
                if date_naissance:
                    identity.metadata["date_naissance"] = date_naissance
                if sexe:
                    identity.metadata["sexe"] = sexe
                updated = True
            if updated:
                identity.save()

        # Vérifier si un profil étudiant existe déjà pour cette identité
        existing_profile = StudentProfile.objects.filter(identity=identity).first()
        if existing_profile:
            # Si le profil existe déjà, on peut créer une nouvelle inscription pour une nouvelle année
            student_profile = existing_profile
            # Vérifier le statut financier
            if student_profile.finance_status == "Bloqué":
                return Response(
                    {
                        "detail": "Inscription impossible : statut financier 'Bloqué'.",
                        "student_id": str(existing_profile.id),
                        "matricule": existing_profile.matricule_permanent,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            # Vérification du solde financier (seulement si nouveau profil)
            balance = self._calculate_balance_for_identity(identity.id)
            if balance > 0:
                return Response(
                    {
                        "detail": "Inscription bloquée: solde négatif.",
                        "balance": float(balance),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Récupération du programme
        try:
            program = Program.objects.get(id=program_id, is_active=True)
        except Program.DoesNotExist:
            return Response(
                {"detail": "Programme introuvable."}, status=status.HTTP_404_NOT_FOUND
            )

        # Récupération de l'année académique
        try:
            academic_year = AcademicYear.objects.get(id=academic_year_id)
        except AcademicYear.DoesNotExist:
            return Response(
                {"detail": "Année académique introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Générer le matricule si nouveau profil
        if not existing_profile:
            matricule_permanent = StudentProfile.generate_matricule()
            # Vérifier l'unicité (au cas où deux requêtes simultanées génèrent le même)
            while StudentProfile.objects.filter(matricule_permanent=matricule_permanent).exists():
                matricule_permanent = StudentProfile.generate_matricule()
            
            # Créer le profil étudiant
            student_profile = StudentProfile.objects.create(
                identity=identity,
                matricule_permanent=matricule_permanent,
                date_entree=date.today(),
                current_program=program,
                finance_status=finance_status,
            )
        else:
            # Mettre à jour le programme si nécessaire
            if student_profile.current_program != program:
                student_profile.current_program = program
            if finance_status != "Bloqué" and student_profile.finance_status != finance_status:
                student_profile.finance_status = finance_status
            student_profile.save()
            matricule_permanent = student_profile.matricule_permanent

        # Vérifier si une inscription existe déjà pour cette année
        existing_registration = RegistrationAdmin.objects.filter(
            student=student_profile,
            academic_year=academic_year,
        ).first()
        
        if existing_registration:
            return Response(
                {
                    "detail": "Une inscription existe déjà pour cette année académique.",
                    "student_id": str(student_profile.id),
                    "matricule": matricule_permanent,
                    "registration_id": str(existing_registration.id),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Création de l'inscription administrative
        try:
            registration = RegistrationAdmin.objects.create(
                student=student_profile,
                academic_year=academic_year,
                level=level,
                finance_status=student_profile.finance_status,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

        # Log audit
        actor_email = getattr(request.user, "email", "")
        SysAuditLog.objects.create(
            action="STUDENT_ENROLLED",
            entity_type="STUDENT_PROFILE",
            entity_id=student_profile.id,
            actor_email=actor_email,
            active_role=role_active,
            payload={
                "student_id": str(student_profile.id),
                "matricule": matricule_permanent,
                "program": program.code,
                "academic_year": academic_year.code,
                "level": level,
            },
        )

        return Response(
            {
                "detail": f"Étudiant créé avec matricule {matricule_permanent}",
                "matricule": matricule_permanent,
                "student_id": str(student_profile.id),
                "registration_id": str(registration.id),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["PUT", "PATCH"],
        url_path="finance-status",
    )
    def update_finance_status(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        PUT /api/students/<uuid>/finance-status/ : Mise à jour statut finance.

        Réservé à OPERATOR_FINANCE. Log audit avec rôle actif.
        """
        role_active = getattr(request, "role_active", None)
        if role_active != "OPERATOR_FINANCE":
            return Response(
                {"detail": "Accès réservé à OPERATOR_FINANCE."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student = self.get_object()
        new_status = request.data.get("finance_status")

        if not new_status:
            return Response(
                {"detail": "Champ 'finance_status' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_statuses = ["OK", "Bloqué", "Moratoire"]
        if new_status not in valid_statuses:
            return Response(
                {"detail": f"Statut invalide. Choix: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = student.finance_status
        student.finance_status = new_status
        student.save()

        # Log audit avec rôle actif
        actor_email = getattr(request.user, "email", "")
        SysAuditLog.objects.create(
            action="FINANCE_STATUS_UPDATED",
            entity_type="STUDENT_PROFILE",
            entity_id=student.id,
            actor_email=actor_email,
            active_role=role_active,
            payload={
                "student_id": str(student.id),
                "old_status": old_status,
                "new_status": new_status,
                "matricule": student.matricule_permanent,
            },
        )

        return Response(
            {
                "detail": "Statut financier mis à jour.",
                "student_id": str(student.id),
                "old_status": old_status,
                "new_status": new_status,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["POST"],
        url_path="validate-registration",
    )
    def validate_registration(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        POST /api/students/<uuid>/validate-registration/ : Valider inscription administrative.

        Réservé à VALIDATOR_ACAD. Valide la REGISTRATION_ADMIN pour l'année académique active.
        """
        role_active = getattr(request, "role_active", None)
        if role_active not in {"VALIDATOR_ACAD", "DOYEN", "RECTEUR", "ADMIN_SI"}:
            return Response(
                {"detail": "Accès réservé à VALIDATOR_ACAD, DOYEN, RECTEUR ou ADMIN_SI."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student = self.get_object()
        academic_year_id = request.data.get("academic_year_id")
        registration_id = request.data.get("registration_id")

        # Si registration_id est fourni, valider cette inscription spécifique
        if registration_id:
            try:
                registration = RegistrationAdmin.objects.get(
                    id=registration_id, student=student
                )
            except RegistrationAdmin.DoesNotExist:
                return Response(
                    {"detail": "Inscription introuvable."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        # Sinon, valider l'inscription pour l'année académique active
        elif academic_year_id:
            try:
                registration = RegistrationAdmin.objects.get(
                    student=student, academic_year_id=academic_year_id
                )
            except RegistrationAdmin.DoesNotExist:
                return Response(
                    {"detail": "Inscription introuvable pour cette année académique."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Prendre la dernière inscription
            registration = RegistrationAdmin.objects.filter(
                student=student
            ).order_by("-registration_date").first()
            if not registration:
                return Response(
                    {"detail": "Aucune inscription trouvée."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Vérification du scope (DOYEN/VALIDATOR_ACAD doivent valider leur faculté)
        if role_active in {"DOYEN", "VALIDATOR_ACAD"}:
            identity = _get_identity_from_request(request)
            if identity and student.current_program and student.current_program.faculty:
                if student.current_program.faculty.doyen_uuid_id != identity.id:
                    return Response(
                        {"detail": "Faculté non autorisée."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

        # Validation : mettre à jour le finance_status à OK
        old_status = registration.finance_status
        registration.finance_status = "OK"
        registration.save()

        # Synchroniser avec le profil étudiant si nécessaire
        if student.finance_status == "Bloqué" and old_status == "Bloqué":
            student.finance_status = "OK"
            student.save()

        # Log audit
        actor_email = getattr(request.user, "email", "")
        SysAuditLog.objects.create(
            action="REGISTRATION_VALIDATED",
            entity_type="REGISTRATION_ADMIN",
            entity_id=registration.id,
            actor_email=actor_email,
            active_role=role_active,
            payload={
                "student_id": str(student.id),
                "registration_id": str(registration.id),
                "academic_year": registration.academic_year.code,
                "level": registration.level,
                "old_status": old_status,
                "new_status": "OK",
            },
        )

        return Response(
            {
                "detail": "Inscription validée.",
                "student_id": str(student.id),
                "registration_id": str(registration.id),
                "academic_year": registration.academic_year.code,
                "level": registration.level,
            },
            status=status.HTTP_200_OK,
        )

    def _calculate_balance_for_identity(self, identity_id) -> Decimal:
        """Calcule le solde d'une identité (somme des factures - paiements)."""
        if not identity_id:
            return Decimal("0")
        total_invoices = (
            Invoice.objects.filter(identity_uuid=identity_id).aggregate(
                total=Sum("total_amount")
            )["total"]
            or Decimal("0")
        )
        total_payments = (
            Payment.objects.filter(invoice__identity_uuid=identity_id).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0")
        )
        return total_invoices - total_payments

    def _get_effective_finance_status(
        self, student: StudentProfile, balance: Decimal
    ) -> str:
        """Calcule le statut financier effectif basé sur le solde."""
        if student.finance_status == "Moratoire":
            return "Moratoire"
        if balance > 0:
            return "Bloqué"
        return "OK"

    @action(
        detail=True,
        methods=["GET"],
        url_path="echeances",
    )
    def get_echeances(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        GET /api/students/<uuid>/echeances/ : Récupère les échéances de frais d'un étudiant.
        
        Retourne les tranches, montant dû, prochaine échéance, statut et jours de retard.
        """
        student = self.get_object()
        
        from apps.academic.services.frais_echeance_calculator import FraisEcheanceCalculator
        from django.utils import timezone
        
        calculator = FraisEcheanceCalculator()
        date_reference = request.GET.get("date_reference")
        if date_reference:
            try:
                from datetime import datetime
                date_reference = datetime.fromisoformat(date_reference).date()
            except (ValueError, TypeError):
                date_reference = timezone.now().date()
        else:
            date_reference = timezone.now().date()
        
        echeances = calculator.calculer_echeances(student, date_reference=date_reference)
        
        return Response(echeances, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST"],
        url_path="moratoire",
    )
    def create_moratoire(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        POST /api/students/<uuid>/moratoire/ : Crée un moratoire pour un étudiant.
        
        Réservé à OPERATOR_FINANCE, SCOLARITE, OPERATOR_SCOLA.
        Input: montant_reporte, duree_jours, motif (optionnel)
        """
        role_active = getattr(request, "role_active", None)
        if role_active not in {"OPERATOR_FINANCE", "SCOLARITE", "OPERATOR_SCOLA", "ADMIN_SI"}:
            return Response(
                {"detail": "Accès réservé à OPERATOR_FINANCE, SCOLARITE, OPERATOR_SCOLA ou ADMIN_SI."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student = self.get_object()
        identity = _get_identity_from_request(request)

        if not identity:
            return Response(
                {"detail": "Identité introuvable."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # SoD : OPERATOR_FINANCE ne peut pas s'accorder moratoire à soi-même
        if role_active == "OPERATOR_FINANCE" and student.identity_id == identity.id:
            return Response(
                {"detail": "SoD: impossible de s'accorder un moratoire à soi-même."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validation des champs
        montant_reporte = request.data.get("montant_reporte")
        duree_jours = request.data.get("duree_jours", 30)
        motif = request.data.get("motif", "")

        if not montant_reporte:
            return Response(
                {"detail": "Champ 'montant_reporte' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            montant_reporte = Decimal(str(montant_reporte))
            duree_jours = int(duree_jours)
        except (ValueError, TypeError):
            return Response(
                {"detail": "Format invalide pour montant_reporte ou duree_jours."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérifier que le montant ne dépasse pas le solde
        if montant_reporte > abs(student.solde):
            return Response(
                {
                    "detail": f"Le montant reporté ({montant_reporte}) ne peut pas dépasser le solde de l'étudiant ({abs(student.solde)})."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Calculer date_fin
        date_fin = timezone.now().date() + timedelta(days=duree_jours)

        # Créer le moratoire
        from apps.academic.models import Moratoire

        try:
            moratoire = Moratoire.objects.create(
                student=student,
                montant_reporte=montant_reporte,
                duree_jours=duree_jours,
                date_fin=date_fin,
                motif=motif,
                accorde_par=identity,
                created_by_role=role_active or "",
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MoratoireSerializer(moratoire)
        return Response(
            {
                "detail": "Moratoire créé avec succès.",
                "moratoire": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["GET"],
        url_path="moratoires-actifs",
    )
    def get_moratoires_actifs(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        GET /api/students/<uuid>/moratoires-actifs/ : Retourne les moratoires actifs d'un étudiant.
        
        Retourne uniquement les moratoires non dépassés (statut = 'Actif' ou 'Respecté').
        """
        student = self.get_object()
        
        from apps.academic.models import Moratoire
        
        moratoires = Moratoire.objects.filter(
            student=student,
            statut__in=["Actif", "Respecté"],
        ).select_related("accorde_par").order_by("-date_accord")
        
        serializer = MoratoireSerializer(moratoires, many=True)
        return Response(
            {
                "student_id": str(student.id),
                "matricule": student.matricule_permanent,
                "moratoires": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["POST"],
        url_path="bourse",
    )
    def create_bourse(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        POST /api/students/<uuid>/bourse/ : Crée une bourse pour un étudiant.
        
        Réservé à SCOLARITE/RECTEUR.
        Input : type_bourse, montant (ou pourcentage), motif, annee_academique, date_fin_validite
        """
        student = self.get_object()
        role_active = getattr(request, "role_active", None)
        identity = _get_identity_from_request(request)

        if not identity:
            return Response(
                {"detail": "Identité introuvable."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Vérifier les permissions
        if role_active not in {"SCOLARITE", "RECTEUR", "ADMIN_SI"}:
            return Response(
                {"detail": "Accès réservé à SCOLARITE, RECTEUR ou ADMIN_SI."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # SoD : SCOLARITE ne peut pas s'accorder bourse à soi-même
        if role_active == "SCOLARITE" and student.identity_id == identity.id:
            return Response(
                {"detail": "SoD: impossible de s'accorder une bourse à soi-même."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Valider les données
        serializer = BourseCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = serializer.validated_data

        # Calculer le montant si pourcentage fourni
        montant = validated_data.get("montant")
        pourcentage = validated_data.get("pourcentage")
        
        if pourcentage and not montant:
            # Si pourcentage fourni sans montant, calculer depuis les frais du programme
            from apps.finance.models import Invoice
            total_factures = (
                Invoice.objects.filter(identity_uuid=student.identity_id)
                .aggregate(total=Sum("total_amount"))["total"]
                or Decimal("0")
            )
            montant = total_factures * (pourcentage / Decimal("100"))

        if not montant:
            return Response(
                {"detail": "Impossible de calculer le montant. Fournissez 'montant' ou 'pourcentage' avec des factures existantes."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Créer la bourse
        try:
            bourse = Bourse.objects.create(
                student=student,
                type_bourse=validated_data["type_bourse"],
                montant=montant,
                pourcentage=pourcentage,
                annee_academique=validated_data["annee_academique"],
                date_fin_validite=validated_data.get("date_fin_validite"),
                motif=validated_data.get("motif", ""),
                conditions=validated_data.get("conditions", {}),
                accorde_par=identity,
                created_by_role=role_active or "",
                statut=Bourse.StatutChoices.ACTIVE,
            )
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Le signal post_save va recalculer le solde automatiquement

        serializer_response = BourseSerializer(bourse)
        return Response(
            {
                "detail": "Bourse créée avec succès.",
                "bourse": serializer_response.data,
                "student_solde_apres": str(student.solde),
                "student_finance_status": student.finance_status,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["GET"],
        url_path="bourses-actives",
    )
    def get_bourses_actives(self, request: HttpRequest, pk=None, *args, **kwargs):  # type: ignore[override]
        """
        GET /api/students/<uuid>/bourses-actives/ : Retourne les bourses actives d'un étudiant.
        
        Retourne uniquement les bourses non terminées (statut = 'Active' ou 'Suspendue').
        """
        student = self.get_object()
        
        bourses = Bourse.objects.filter(
            student=student,
            statut__in=[Bourse.StatutChoices.ACTIVE, Bourse.StatutChoices.SUSPENDUE],
        ).select_related("accorde_par", "annee_academique").order_by("-date_attribution")
        
        serializer = BourseSerializer(bourses, many=True)
        return Response(
            {
                "student_id": str(student.id),
                "matricule": student.matricule_permanent,
                "bourses": serializer.data,
                "total_bourses_actives": bourses.aggregate(total=Sum("montant"))["total"] or Decimal("0"),
            },
            status=status.HTTP_200_OK,
        )
