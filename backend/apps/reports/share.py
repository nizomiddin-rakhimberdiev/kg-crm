"""
Faqat o'qish uchun, muddatli havola — bank, investor yoki buxgalterga
(Bosqich 13.6, brif §8).

Havola o'zgarmas nusxani suv belgili PDF sifatida ochadi. Token ichida
tashkilot bor (ADR-23 usuli): ochiq so'rovda tenant konteksti yo'q, RLS'ni
kengaytirish esa noto'g'ri javob bo'lardi. Bazada faqat token xeshi
saqlanadi — jadval o'qilsa ham havolani tiklab bo'lmaydi.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.reports.models import ReportReview, ReportShareLink

__all__ = ["create_link", "find_link", "token_hash", "url_for"]

DEFAULT_DAYS = 14
MAX_DAYS = 90


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def url_for(token: str) -> str:
    base = str(getattr(settings, "FRONTEND_URL", "")).rstrip("/")
    return f"{base}/api/v1/public/reports/{token}"


def create_link(
    *, review: ReportReview, user: Any, label: str, days: Any = None
) -> tuple[ReportShareLink, str]:
    """Topshirilgan yoki tasdiqlangan nusxaga havola; token faqat bir marta qaytadi."""
    from apps.children.telegram import build_code

    if review.snapshot_id is None:
        raise BusinessRuleViolation(
            gettext("Ulashish uchun avval hisobotni topshiring yoki tasdiqlang.")
        )
    name = str(label or "").strip()
    if not name:
        raise BusinessRuleViolation(gettext("Havola kim uchun ekanini yozing (bank, investor…)."))
    try:
        lifetime = int(days) if days not in (None, "") else DEFAULT_DAYS
    except (TypeError, ValueError):
        lifetime = DEFAULT_DAYS
    lifetime = min(max(lifetime, 1), MAX_DAYS)
    token = build_code(review.organization_id)
    link = ReportShareLink.objects.create(
        organization_id=review.organization_id,
        snapshot_id=review.snapshot_id,
        token_hash=token_hash(token),
        label=name[:120],
        expires_at=timezone.now() + timedelta(days=lifetime),
        created_by=user,
    )
    return link, token


def find_link(token: str) -> ReportShareLink | None:
    """Tashkilot kontekstida chaqiriladi; eskirgan yoki bekor — `None`."""
    link = (
        ReportShareLink.objects.select_related("snapshot", "snapshot__branch")
        .filter(token_hash=token_hash(token), revoked_at__isnull=True)
        .first()
    )
    if link is None or link.expires_at <= timezone.now():
        return None
    return link
