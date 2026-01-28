#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn

from dotenv import load_dotenv

# Charger .env depuis le répertoire backend avant tout
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)


def main() -> NoReturn:
    # S'assurer que USE_SQLITE est défini pour le développement local
    if not os.getenv("USE_SQLITE"):
        os.environ["USE_SQLITE"] = "1"
        os.environ["LOCAL_DB_ONLY"] = "1"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django n'est pas installé. Activez le venv puis installez les dépendances."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
