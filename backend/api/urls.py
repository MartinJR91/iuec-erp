from __future__ import annotations

from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.routers import DefaultRouter

from .auth import obtain_token, regenerate_token
from .views import (
    bulk_update_grades,
    courses_endpoint,
    dashboard_data,
    grades_endpoint,
    students_endpoint,
    validate_grades,
    validate_registration,
    workflows_validate,
)
from .students_views import StudentsViewSet
from .viewsets import (
    CoreIdentityViewSet,
    FacultyViewSet,
    IdentityRoleLinkViewSet,
    InvoiceViewSet,
    ProgramViewSet,
    StudentProfileViewSet,
)

router = DefaultRouter()
router.register(r"identities", CoreIdentityViewSet, basename="core-identity")
router.register(r"identity-role-links", IdentityRoleLinkViewSet, basename="identity-role")
router.register(r"invoices", InvoiceViewSet, basename="invoices")
router.register(r"faculties", FacultyViewSet, basename="faculties")
router.register(r"programs", ProgramViewSet, basename="programs")
router.register(r"student-profiles", StudentProfileViewSet, basename="student-profiles")
router.register(r"students", StudentsViewSet, basename="students")

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
    path("dashboard/", dashboard_data, name="dashboard-data"),
    path("grades/", grades_endpoint, name="grades"),
    path("grades/bulk-update/", bulk_update_grades, name="grades-bulk-update"),
    path("grades/validate/", validate_grades, name="grades-validate"),
    path("jury/close/", validate_grades, name="jury-close"),  # Alias pour clôture jury
    path("courses/", courses_endpoint, name="courses"),
    # path("students/", students_endpoint, name="students"),  # Remplacé par StudentsViewSet
    path("registrations/validate/", validate_registration, name="registrations-validate"),
    path("workflows/", workflows_validate, name="workflows-validate"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="redoc"),
    path("", include(router.urls)),
]
