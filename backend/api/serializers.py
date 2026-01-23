from __future__ import annotations

from rest_framework import serializers

from apps.academic.models import GradeEntry
from apps.finance.models import Invoice, Payment
from identity.models import CoreIdentity, IdentityRoleLink


class CoreIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CoreIdentity
        fields = "__all__"


class IdentityRoleLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityRoleLink
        fields = "__all__"


class GradeEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = GradeEntry
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class InvoiceSerializer(serializers.ModelSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = "__all__"
