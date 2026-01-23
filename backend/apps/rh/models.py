from __future__ import annotations

from django.db import models


class Department(models.Model):
    code = models.CharField(max_length=32, unique=True)
    label = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.label
