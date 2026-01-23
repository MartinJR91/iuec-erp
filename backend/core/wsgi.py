from __future__ import annotations

import os
from typing import Any

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

application: Any = get_wsgi_application()
