from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

from api.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("health/", health),
]
