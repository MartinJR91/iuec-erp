from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db.models import Sum
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.academic.models import Grade, Moratoire, RegistrationAdmin, RegistrationPedagogical, StudentProfile
from apps.academic.services.note_calculator import NoteCalculatorService
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, IdentityRoleLink, SysAuditLog


def _get_recteur_email() -> Optional[str]:
    recteur_link = (
        IdentityRoleLink.objects.select_related("identity", "role")
        .filter(role__code="RECTEUR", is_active=True, identity__is_active=True)
        .first()
    )
    if recteur_link:
        return recteur_link.identity.email
    return "recteur@iuec.cm"


@receiver(post_save, sender=Grade)
def recalculate_ue_on_grade_save(sender, instance: Grade, created: bool, **kwargs) -> None:
    """
    Recalcule la moyenne UE et le statut après sauvegarde d'une note.
    Log également l'audit avec le rôle actif.
    """
    # Récupérer le rôle actif depuis le champ created_by_role ou utiliser une valeur par défaut
    active_role = instance.created_by_role or "USER_TEACHER"
    
    # Log audit
    actor_email = instance.teacher.email if instance.teacher else ""
    # entity_id doit être un UUID, on utilise un UUID généré
    # L'ID de Grade sera stocké dans le payload
    grade_id = getattr(instance, 'id', None)
    SysAuditLog.objects.create(
        action="JURY_GRADE_CAPTURED",
        entity_type="GRADE",
        entity_id=uuid4(),
        actor_email=actor_email,
        active_role=active_role,
        payload={
            "grade_id": str(grade_id) if grade_id else None,
            "evaluation_id": str(instance.evaluation_id),
            "student_id": str(instance.student_id),
            "value": str(instance.value) if instance.value is not None else "Absent",
            "is_absent": instance.is_absent,
        },
    )
    
    # Recalculer la moyenne et le statut pour toutes les inscriptions pédagogiques
    # de l'étudiant qui concernent l'UE de cette évaluation
    try:
        evaluation = instance.evaluation
        course_element = evaluation.course_element
        teaching_unit = course_element.teaching_unit
        
        if teaching_unit:
            student = instance.student
            # Récupérer toutes les inscriptions pédagogiques de l'étudiant pour cette UE
            registrations = RegistrationPedagogical.objects.filter(
                registration_admin__student=student,
                teaching_unit=teaching_unit,
            )
            
            for registration in registrations:
                # Calculer la nouvelle moyenne
                moyenne = NoteCalculatorService.calcule_moyenne_ue(registration)
                
                # Calculer le nouveau statut
                statut = NoteCalculatorService.calcule_statut_ue(registration)
                
                # Mapper le statut calculé vers les choix du modèle
                status_mapping = {
                    "Validée": "Validé",
                    "Ajourné": "Ajourné",
                    "Bloquée": "Ajourné",  # Bloquée est traité comme Ajourné
                }
                new_status = status_mapping.get(statut, "En cours")
                
                # Mettre à jour le statut de l'inscription pédagogique
                # Utiliser update pour éviter de déclencher le signal à nouveau
                RegistrationPedagogical.objects.filter(id=registration.id).update(
                    status=new_status
                )
    except Exception:
        # Ignorer les erreurs pour ne pas bloquer la sauvegarde de la note
        pass


@receiver(post_save, sender=RegistrationPedagogical)
def log_pv_result(sender, instance: RegistrationPedagogical, created: bool, **kwargs) -> None:
    SysAuditLog.objects.create(
        action="JURY_PV_RESULT",
        entity_type="REGISTRATION_PEDAGOGICAL",
        entity_id=uuid4(),
        actor_email="",
        active_role="VALIDATOR_ACAD",
        payload={
            "registration_admin_id": str(instance.registration_admin_id),
            "teaching_unit_id": str(instance.teaching_unit),
            "status": instance.status,
        },
    )


@receiver(post_save, sender=StudentProfile)
def sync_finance_status_to_registrations(
    sender, instance: StudentProfile, created: bool, **kwargs
) -> None:
    """Synchronise le finance_status du profil étudiant vers ses inscriptions administratives."""
    # Met à jour toutes les inscriptions administratives de l'étudiant
    # Utilise update_fields pour éviter de déclencher le signal à nouveau
    RegistrationAdmin.objects.filter(student=instance).update(
        finance_status=instance.finance_status
    )


@receiver(pre_save, sender=RegistrationAdmin)
def validate_registration_finance_status(
    sender, instance: RegistrationAdmin, **kwargs
) -> None:
    """Valide que l'inscription n'est pas bloquée par le statut financier."""
    if instance.finance_status == "Bloqué":
        raise ValidationError("Inscription impossible : étudiant bloqué")
    # Vérifie aussi le statut du profil étudiant
    if instance.student and instance.student.finance_status == "Bloqué":
        raise ValidationError("Inscription impossible : étudiant bloqué")
    
    # Vérifier si solde < 0 et tranche 1 due
    if instance.student:
        from apps.academic.services.frais_echeance_calculator import FraisEcheanceCalculator
        from django.utils import timezone
        
        calculator = FraisEcheanceCalculator()
        echeances = calculator.calculer_echeances(instance.student, date_reference=timezone.now().date())
        
        # Si solde négatif et tranche 1 due, bloquer l'inscription
        if echeances["montant_du"] > 0:
            # Trouver la tranche 1
            tranche1 = next((t for t in echeances["tranches"] if t.get("type") == "scolarite" and "Tranche 1" in t.get("label", "")), None)
            if tranche1 and tranche1.get("due") and not tranche1.get("payee"):
                raise ValidationError("Inscription bloquée : échéance non respectée (Tranche 1 due)")


def _calculate_student_balance(identity_uuid) -> Decimal:
    """Calcule le solde d'un étudiant (factures - paiements)."""
    total_invoices = (
        Invoice.objects.filter(identity_uuid=identity_uuid).aggregate(
            total=Sum("total_amount")
        )["total"]
        or Decimal("0")
    )
    total_payments = (
        Payment.objects.filter(invoice__identity_uuid=identity_uuid).aggregate(
            total=Sum("amount")
        )["total"]
        or Decimal("0")
    )
    return total_invoices - total_payments


@receiver(post_save, sender=Invoice)
def update_student_balance_on_invoice(sender, instance: Invoice, **kwargs) -> None:
    """Recalcule le solde de l'étudiant après création/modification d'une facture."""
    try:
        student_profile = StudentProfile.objects.get(identity_id=instance.identity_uuid)
        from apps.academic.services.frais_echeance_calculator import FraisEcheanceCalculator
        
        calculator = FraisEcheanceCalculator()
        calculator.update_solde_etudiant(student_profile)
    except StudentProfile.DoesNotExist:
        pass


@receiver(post_save, sender=Payment)
def update_student_balance_on_payment(sender, instance: Payment, **kwargs) -> None:
    """Recalcule le solde de l'étudiant après création/modification d'un paiement."""
    try:
        identity_uuid = instance.invoice.identity_uuid
        student_profile = StudentProfile.objects.get(identity_id=identity_uuid)
        from apps.academic.services.frais_echeance_calculator import FraisEcheanceCalculator
        
        calculator = FraisEcheanceCalculator()
        calculator.update_solde_etudiant(student_profile)
    except StudentProfile.DoesNotExist:
        pass


@receiver(post_save, sender=SysAuditLog)
def notify_sod_alert(sender, instance: SysAuditLog, created: bool, **kwargs) -> None:
    if not created:
        return
    if instance.action in {"SOD_ALERT", "KPI_ACCESS"}:
        return
    if "SOD" not in instance.action:
        return

    recteur_email = _get_recteur_email()
    subject = "Alerte SoD détectée"
    message = (
        f"Action: {instance.action}\n"
        f"Acteur: {instance.actor_email}\n"
        f"Rôle: {instance.active_role}\n"
        f"Détails: {instance.payload}\n"
    )
    if recteur_email:
        send_mail(
            subject,
            message,
            getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@iuec.cm"),
            [recteur_email],
            fail_silently=True,
        )

    SysAuditLog.objects.create(
        action="SOD_ALERT",
        entity_type=instance.entity_type,
        entity_id=instance.entity_id,
        actor_email=instance.actor_email,
        active_role=instance.active_role,
        payload={"source": "signal", "original_action": instance.action},
    )


@receiver(post_save, sender=Moratoire)
def handle_moratoire_status_change(sender, instance: Moratoire, created: bool, **kwargs) -> None:
    """
    Gère les changements de statut d'un moratoire.
    - Si créé → met finance_status = 'Moratoire' sur STUDENT_PROFILE
    - Si date_fin dépassée → statut = 'Dépassé', finance_status = 'Bloqué' (si solde <0)
    """
    from django.utils import timezone
    from apps.academic.services.frais_echeance_calculator import FraisEcheanceCalculator

    student = instance.student

    if created:
        # Nouveau moratoire : mettre le statut financier à 'Moratoire'
        student.finance_status = "Moratoire"
        student.save(update_fields=["finance_status"])

        # Log audit
        actor_email = getattr(instance.accorde_par, "email", "")
        SysAuditLog.objects.create(
            action="MORATOIRE_ACCORDE",
            entity_type="MORATOIRE",
            entity_id=instance.id,
            actor_email=actor_email,
            active_role=instance.created_by_role,
            payload={
                "student_id": str(student.id),
                "matricule": student.matricule_permanent,
                "montant_reporte": float(instance.montant_reporte),
                "duree_jours": instance.duree_jours,
                "date_fin": instance.date_fin.isoformat(),
                "motif": instance.motif,
            },
        )
    else:
        # Vérifier si la date de fin est dépassée (seulement si le statut est encore Actif)
        today = timezone.now().date()
        if instance.date_fin < today and instance.statut == Moratoire.StatutChoices.ACTIF:
            # Mettre à jour le statut sans déclencher à nouveau le signal
            Moratoire.objects.filter(id=instance.id).update(statut=Moratoire.StatutChoices.DEPASSE)
            instance.refresh_from_db()

            # Si solde < 0, mettre finance_status à 'Bloqué'
            calculator = FraisEcheanceCalculator()
            calculator.update_solde_etudiant(student)

            # Si le solde est toujours négatif après recalcul, bloquer
            student.refresh_from_db()
            if student.solde < 0:
                student.finance_status = "Bloqué"
                student.save(update_fields=["finance_status"])

            # Log audit
            actor_email = getattr(instance.accorde_par, "email", "")
            SysAuditLog.objects.create(
                action="MORATOIRE_DEPASSE",
                entity_type="MORATOIRE",
                entity_id=instance.id,
                actor_email=actor_email,
                active_role=instance.created_by_role,
                payload={
                    "student_id": str(student.id),
                    "matricule": student.matricule_permanent,
                    "date_fin": instance.date_fin.isoformat(),
                    "nouveau_statut": "Dépassé",
                },
            )
