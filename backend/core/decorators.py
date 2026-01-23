from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable, Optional, TypeVar

from django.http import HttpRequest, JsonResponse

F = TypeVar("F", bound=Callable[..., object])


def with_active_role(allowed_roles: Optional[Iterable[str]] = None) -> Callable[[F], F]:
    """Décorateur pour exiger un rôle actif sur les vues critiques."""

    def decorator(view_func: F) -> F:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            role_active = getattr(request, "role_active", None)
            if not role_active:
                return JsonResponse(
                    {"detail": "Rôle actif requis pour cette action."}, status=403
                )
            if allowed_roles and role_active not in allowed_roles:
                return JsonResponse(
                    {"detail": "Rôle actif non autorisé pour cette action."},
                    status=403,
                )
            return view_func(request, *args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
