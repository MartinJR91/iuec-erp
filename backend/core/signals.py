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

from apps.academic.models import Grade, RegistrationAdmin, RegistrationPedagogical, StudentProfile
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
def log_grade_capture(sender, instance: Grade, created: bool, **kwargs) -> None:
    if not created:
        return
    SysAuditLog.objects.create(
        action="JURY_GRADE_CAPTURED",
        entity_type="GRADE",
        entity_id=uuid4(),
        actor_email=instance.teacher.email if instance.teacher else "",
        active_role="USER_TEACHER",
        payload={
            "evaluation_id": str(instance.evaluation_id),
            "student_id": str(instance.student_id),
            "value": str(instance.value),
        },
    )


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
        balance = _calculate_student_balance(instance.identity_uuid)
        new_finance_status = student_profile.finance_status
        # Met à jour finance_status si solde < 0
        if balance < 0:
            new_finance_status = "Bloqué"
        elif balance == 0 and student_profile.finance_status == "Bloqué":
            new_finance_status = "OK"
        # Utilise update_fields pour éviter de déclencher le signal à nouveau
        StudentProfile.objects.filter(id=student_profile.id).update(
            solde=balance, finance_status=new_finance_status
        )
    except StudentProfile.DoesNotExist:
        pass


@receiver(post_save, sender=Payment)
def update_student_balance_on_payment(sender, instance: Payment, **kwargs) -> None:
    """Recalcule le solde de l'étudiant après création/modification d'un paiement."""
    try:
        identity_uuid = instance.invoice.identity_uuid
        student_profile = StudentProfile.objects.get(identity_id=identity_uuid)
        balance = _calculate_student_balance(identity_uuid)
        new_finance_status = student_profile.finance_status
        # Met à jour finance_status si solde < 0
        if balance < 0:
            new_finance_status = "Bloqué"
        elif balance == 0 and student_profile.finance_status == "Bloqué":
            new_finance_status = "OK"
        # Utilise update_fields pour éviter de déclencher le signal à nouveau
        StudentProfile.objects.filter(id=student_profile.id).update(
            solde=balance, finance_status=new_finance_status
        )
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
