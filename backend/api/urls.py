from __future__ import annotations

from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from .auth import obtain_token, regenerate_token
from .viewsets import (
    CoreIdentityViewSet,
    GradeEntryViewSet,
    IdentityRoleLinkViewSet,
    InvoiceViewSet,
)

router = DefaultRouter()
router.register(r"identities", CoreIdentityViewSet, basename="core-identity")
router.register(r"identity-role-links", IdentityRoleLinkViewSet, basename="identity-role")
router.register(r"grades", GradeEntryViewSet, basename="grades")
router.register(r"invoices", InvoiceViewSet, basename="invoices")

schema_view = get_schema_view(
    openapi.Info(
        title="IUEC ERP API",
        default_version="v1",
        description="API ERP universitaire (RBAC + Finance + Academic).",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("token/", obtain_token, name="obtain-token"),
    path("auth/regenerate-token/", regenerate_token, name="regenerate-token"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="redoc"),
    path("", include(router.urls)),
]
