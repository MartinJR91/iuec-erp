from __future__ import annotations

from .settings import *  # type: ignore

USE_SQLITE = True
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
    }
}
