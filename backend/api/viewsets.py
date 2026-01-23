from __future__ import annotations

from rest_framework import viewsets

from apps.academic.models import GradeEntry
from apps.finance.models import Invoice
from identity.models import CoreIdentity, IdentityRoleLink

from .permissions import (
    AdminSIPermission,
    CoreIdentityPermission,
    GradePermission,
    OperatorFinancePermission,
    SoDPermission,
)
from .serializers import (
    CoreIdentitySerializer,
    GradeEntrySerializer,
    IdentityRoleLinkSerializer,
    InvoiceSerializer,
)


class CoreIdentityViewSet(viewsets.ModelViewSet):
    queryset = CoreIdentity.objects.all()
    serializer_class = CoreIdentitySerializer
    permission_classes = (CoreIdentityPermission, SoDPermission)


class IdentityRoleLinkViewSet(viewsets.ModelViewSet):
    queryset = IdentityRoleLink.objects.all()
    serializer_class = IdentityRoleLinkSerializer
    permission_classes = (AdminSIPermission, SoDPermission)


class GradeEntryViewSet(viewsets.ModelViewSet):
    queryset = GradeEntry.objects.all()
    serializer_class = GradeEntrySerializer
    permission_classes = (GradePermission, SoDPermission)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = (OperatorFinancePermission, SoDPermission)
