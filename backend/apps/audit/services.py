"""
Audit yozuvlari — **servis qatlamidan** yoziladi, trigger'dan emas.

Sabab: triggerda biznes konteksti yo'q (kim, qaysi IP, oldin/keyin qanday
edi). docs/02 §20.3.
"""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.audit.models import AuditLog

__all__ = ["record", "client_ip"]


def client_ip(request: HttpRequest | None) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record(
    *,
    action: str,
    request: HttpRequest | None = None,
    actor: Any = None,
    organization: Any = None,
    entity_type: str = "",
    entity_id: Any = None,
    changes: dict[str, Any] | None = None,
    actor_email: str = "",
) -> AuditLog:
    """Bitta audit yozuvini qo'shadi. Hech qachon istisno ko'tarmasligi kerak."""
    if actor is not None and getattr(actor, "is_authenticated", False):
        organization = organization or getattr(actor, "organization", None)
        actor_email = actor_email or actor.email
    else:
        actor = None

    return AuditLog.objects.create(
        organization=organization,
        actor=actor,
        actor_email=actor_email[:254],
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes or {},
        ip=client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:255] if request else ""),
    )
