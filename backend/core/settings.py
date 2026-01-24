from __future__ import annotations

import os
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
DEBUG = os.getenv("DEBUG", "0") == "1"
ALLOWED_HOSTS: List[str] = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_yasg",
    "guardian",
    "auditlog",
    "identity.apps.IdentityConfig",
    "apps.identity",
    "apps.rbac",
    "apps.academic",
    "apps.finance",
    "apps.rh",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.KeycloakJWTMiddleware",
    "core.middleware.ActiveRoleMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "iuec_erp"),
        "USER": os.getenv("DB_USER", "erp"),
        "PASSWORD": os.getenv("DB_PASSWORD", "erp_dev_password"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {"options": "-c client_encoding=UTF8"},
    }
}

USE_SQLITE = os.getenv("USE_SQLITE", "0") == "1"
DATABASE_URL = os.getenv("DATABASE_URL")
LOCAL_DB_ONLY = os.getenv("LOCAL_DB_ONLY", "0") == "1"
if USE_SQLITE:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
elif DATABASE_URL and not LOCAL_DB_ONLY:
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL, conn_max_age=600, ssl_require=True
    )

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_DIRS = [BASE_DIR / "static" / "react"]

CORS_ALLOWED_ORIGINS = [
    "https://iuec-frontend.onrender.com",
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]
CORS_ALLOW_HEADERS = [
    "Authorization",
    "Content-Type",
    "X-Role-Active",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
]

AUDITLOG_INCLUDE_ALL_MODELS = True

KEYCLOAK_CONFIG = {
    "server_url": os.getenv("KEYCLOAK_SERVER_URL", "https://ton-keycloak.onrender.com"),
    "realm": os.getenv("KEYCLOAK_REALM", "iuec"),
    "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "backend-api"),
    "audience": os.getenv("KEYCLOAK_AUDIENCE", "backend-api"),
    "issuer_url": os.getenv(
        "KEYCLOAK_ISSUER_URL",
        f"{os.getenv('KEYCLOAK_SERVER_URL', 'https://ton-keycloak.onrender.com')}/realms/{os.getenv('KEYCLOAK_REALM', 'iuec')}",
    ),
    "jwks_url": os.getenv(
        "KEYCLOAK_JWKS_URL",
        f"{os.getenv('KEYCLOAK_SERVER_URL', 'https://ton-keycloak.onrender.com')}/realms/{os.getenv('KEYCLOAK_REALM', 'iuec')}/protocol/openid-connect/certs",
    ),
    "jwks_cache_seconds": int(os.getenv("KEYCLOAK_JWKS_CACHE_SECONDS", "300")),
    "jwt_algorithms": ["RS256"],
}

KEYCLOAK_JWKS_ENABLED = os.getenv("KEYCLOAK_JWKS_ENABLED", "1")
