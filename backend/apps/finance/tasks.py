"""
Moliya fon vazifalari (docs/02 §18).

Vazifalar **idempotent**: Celery kafolati "kamida bir marta", ya'ni qayta
ishga tushish normal holat. Ikki marta hisoblash esa mijozning ishonchini
yo'qotadi — shuning uchun takroriylik servis qatlamida, bazadagi qisman
indeks bilan bloklanadi (docs/03 §13.3).
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.core.tasks import reliable_task
from apps.core.tenancy import organization_context, platform_context
from apps.finance import services
from apps.organizations.models import Organization

logger = logging.getLogger(__name__)

__all__ = ["generate_monthly_invoices_task", "mark_overdue_invoices_task"]


@reliable_task(name="finance.generate_monthly_invoices")
def generate_monthly_invoices_task(
    period_year: int | None = None,
    period_month: int | None = None,
    organization_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Barcha (yoki bitta) tashkilot uchun oylik hisob-fakturalarni chiqaradi.

    Har bir tashkilot ALOHIDA ishlanadi va xatosi qolganlarini
    to'xtatmaydi: bitta mijozning nosozligi tufayli boshqa mijozlar oyni
    yo'qotmasligi kerak.
    """
    today = timezone.localdate()
    year = period_year or today.year
    month = period_month or today.month

    # Tashkilotlar bo'ylab aylanish — PLATFORMA tekisligidagi amal.
    # RLS ostida uni ochiq so'rash kerak, va bu to'g'ri: cross-tenant
    # sikl kodda ko'rinib tursin (docs/03 §6.3).
    with platform_context():
        organizations = list(Organization.objects.filter(is_active=True))
    if organization_id:
        organizations = [o for o in organizations if str(o.id) == str(organization_id)]

    results: list[dict[str, Any]] = []
    for organization in organizations:
        try:
            with organization_context(organization.id):
                result = services.generate_monthly_invoices(
                    organization=organization, period_year=year, period_month=month
                )
            results.append({"organization": organization.slug, **result.as_dict()})
        except Exception as exc:
            logger.exception("Hisob-faktura generatsiyasi muvaffaqiyatsiz: %s", organization.slug)
            # SABAB ham javobga tushadi: `error: True` ni o'qigan odam
            # nima bo'lganini bilish uchun log'ni qidirishga majbur edi.
            results.append(
                {"organization": organization.slug, "error": True, "reason": str(exc)[:200]}
            )

    return results


@reliable_task(name="finance.mark_overdue_invoices")
def mark_overdue_invoices_task() -> int:
    """Muddati o'tgan hisob-fakturalarni belgilaydi (har kuni)."""
    total = 0
    with platform_context():
        organizations = list(Organization.objects.filter(is_active=True))
    for organization in organizations:
        with organization_context(organization.id):
            total += services.mark_overdue_invoices(organization_id=organization.id)
    return total
