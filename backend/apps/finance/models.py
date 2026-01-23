from __future__ import annotations

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from django.db import models, transaction
from django.utils import timezone


class FeeCategory(models.Model):
    code = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.label


class FinancialLedger(models.Model):
    """FINANCIAL_LEDGER - Grand livre comptable."""

    code = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "FINANCIAL_LEDGER"

    def __str__(self) -> str:
        return f"{self.code} - {self.label}"


class Invoice(models.Model):
    """INVOICE - Facture et lignes associees."""

    STATUS_DRAFT = "DRAFT"
    STATUS_ISSUED = "ISSUED"
    STATUS_PAID = "PAID"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_ISSUED, "Issued"),
        (STATUS_PAID, "Paid"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    number = models.CharField(max_length=32, unique=True, blank=True)
    identity_uuid = models.UUIDField()
    program_code = models.CharField(max_length=32)
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    line_items = models.JSONField(default=list, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "INVOICE"

    def __str__(self) -> str:
        return self.number or "INVOICE"

    def is_paid(self) -> bool:
        total_paid = self.payments.aggregate(total=models.Sum("amount")).get("total")
        return (total_paid or Decimal("0")) >= self.total_amount

    def is_blocked(self) -> bool:
        return self.status in {self.STATUS_ISSUED, self.STATUS_DRAFT} and not self.is_paid()

    def save(self, *args, **kwargs) -> None:
        if not self.number:
            self.number = self._generate_invoice_number()
        self._ensure_mandatory_lines()
        self.total_amount = self._compute_total()
        super().save(*args, **kwargs)

    def _generate_invoice_number(self) -> str:
        year = self.issue_date.year if self.issue_date else timezone.now().year
        prefix = f"{year}_FACT_SCOL_"
        with transaction.atomic():
            count = (
                Invoice.objects.select_for_update()
                .filter(number__startswith=prefix)
                .count()
            )
            return f"{prefix}{count + 1:04d}"

    def _ensure_mandatory_lines(self) -> None:
        mandatory_products = [
            {"code": "KIT_AGRO", "label": "Kit Agro", "amount": "0.00"},
            {"code": "LABO", "label": "Labo", "amount": "0.00"},
        ]
        existing_codes = {item.get("code") for item in self.line_items}
        for product in mandatory_products:
            if product["code"] not in existing_codes:
                self.line_items.append(product)

    def _compute_total(self) -> Decimal:
        total = Decimal("0")
        for item in self.line_items:
            amount = Decimal(str(item.get("amount", "0")))
            total += amount
        return total


class Payment(models.Model):
    """PAYMENT - Paiement associe a une facture."""

    METHOD_CASH = "CASH"
    METHOD_BANK = "BANK"
    METHOD_MOBILE = "MOBILE"

    METHOD_CHOICES = (
        (METHOD_CASH, "Cash"),
        (METHOD_BANK, "Bank"),
        (METHOD_MOBILE, "Mobile"),
    )

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=16, choices=METHOD_CHOICES)
    reference = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "PAYMENT"

    def __str__(self) -> str:
        return f"{self.invoice.number} - {self.amount}"


class AccountingEntry(models.Model):
    """ACCOUNTING_ENTRY - Ecriture comptable en double (debit/credit)."""

    TYPE_DEBIT = "DEBIT"
    TYPE_CREDIT = "CREDIT"

    ENTRY_TYPE_CHOICES = (
        (TYPE_DEBIT, "Debit"),
        (TYPE_CREDIT, "Credit"),
    )

    ledger = models.ForeignKey(
        FinancialLedger, on_delete=models.PROTECT, related_name="entries"
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="entries"
    )
    entry_type = models.CharField(max_length=8, choices=ENTRY_TYPE_CHOICES)
    account_code = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ACCOUNTING_ENTRY"

    def __str__(self) -> str:
        return f"{self.entry_type} {self.amount}"

    @classmethod
    def create_double_entry(
        cls,
        ledger: FinancialLedger,
        invoice: Invoice,
        amount: Decimal,
        debit_account: str,
        credit_account: str,
        description: str = "",
    ) -> List["AccountingEntry"]:
        debit = cls.objects.create(
            ledger=ledger,
            invoice=invoice,
            entry_type=cls.TYPE_DEBIT,
            account_code=debit_account,
            amount=amount,
            description=description,
        )
        credit = cls.objects.create(
            ledger=ledger,
            invoice=invoice,
            entry_type=cls.TYPE_CREDIT,
            account_code=credit_account,
            amount=amount,
            description=description,
        )
        return [debit, credit]
