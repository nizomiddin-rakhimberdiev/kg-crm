"""
Radix Intelligence fon vazifasi (docs/07 §11).

Har kecha 03:30 — `finance.mark_overdue_invoices` (03:00) dan KEYIN, ular
bir-biriga zid bo'lmasligi uchun; garchi qoida `status` ga tayanmasa ham.

Tashkilotlar bo'ylab aylanadi va HAR BIRI uchun kontekstni alohida
o'rnatadi (`reports.send_debt_reminders` naqshi): bitta tsiklda ham
tenant chegarasi saqlanadi. Bitta tashkilotdagi xato boshqalarini
to'xtatmaydi — log'ga yoziladi va davom etadi.
"""

from __future__ import annotations

import logging
from typing import Any

from apps.core.tasks import reliable_task
from apps.core.tenancy import organization_context, platform_context
from apps.intelligence import selectors, services

logger = logging.getLogger(__name__)

__all__ = ["generate_insights", "send_daily_digests"]


@reliable_task(name="intelligence.generate_insights")
def generate_insights(organization_id: Any = None) -> dict[str, int]:
    from apps.organizations.models import Organization

    with platform_context():
        queryset = Organization.objects.filter(is_active=True)
        if organization_id is not None:
            queryset = queryset.filter(id=organization_id)
        organizations = list(queryset)

    totals: dict[str, int] = {
        "organizations": 0,
        "branches": 0,
        "created": 0,
        "refreshed": 0,
        "auto_resolved": 0,
        "suppressed": 0,
        "episodes_ended": 0,
        "failed": 0,
    }
    for organization in organizations:
        try:
            with organization_context(organization.id):
                totals["organizations"] += 1
                for branch_id in selectors.branch_ids_for(organization.id):
                    result = services.generate_for_branch(
                        organization=organization, branch_id=branch_id
                    )
                    totals["branches"] += 1
                    for key, value in result.as_dict().items():
                        totals[key] += value
        except Exception:  # noqa: BLE001 — bitta tashkilot boshqalarini to'xtatmasin
            totals["failed"] += 1
            logger.exception("Insight generatsiyasi yiqildi: organization=%s", organization.id)

    logger.info("Insight generatsiyasi: %s", totals)
    return totals


@reliable_task(name="intelligence.send_daily_digests")
def send_daily_digests() -> dict[str, int]:
    """
    Har soat ishga tushadi; xulosa faqat `alerts.digest_hour` (sukut 20,
    Toshkent) soati kelgan tashkilotlarga ketadi (Bosqich 13.4). Soat
    sozlama bo'lgani uchun jadval soatlik — har bog'cha o'z vaqtini tanlaydi.
    """
    from django.utils import timezone

    from apps.intelligence import alerts
    from apps.organizations.models import Organization
    from apps.settings_app.services import get_setting

    now = timezone.localtime()
    with platform_context():
        organizations = list(Organization.objects.filter(is_active=True))
    totals = {"organizations": 0, "delivered": 0, "failed": 0}
    for organization in organizations:
        try:
            with organization_context(organization.id):
                hour = int(get_setting(key="alerts.digest_hour") or 20)
                if hour != now.hour:
                    continue
                totals["organizations"] += 1
                totals["delivered"] += alerts.send_digest(organization=organization, day=now.date())
        except Exception:  # noqa: BLE001 — bitta tashkilot boshqalarini to'xtatmasin
            totals["failed"] += 1
            logger.exception("Kunlik xulosa yiqildi: organization=%s", organization.id)
    return totals
