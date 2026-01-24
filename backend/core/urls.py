from __future__ import annotations

from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from api.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("health/", health),
    re_path(
        r"^(?!static|media|admin|api|health).+$",
        TemplateView.as_view(template_name="index.html"),
    ),
    path("", TemplateView.as_view(template_name="index.html")),
]
