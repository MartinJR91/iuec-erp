#!/usr/bin/env python
from __future__ import annotations

import os
import sys
from typing import NoReturn


def main() -> NoReturn:
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
