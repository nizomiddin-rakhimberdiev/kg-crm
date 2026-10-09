"""
Hisob-kitob vazifasi JIM yiqilmasligi kerak.

`record_daily_peak` kuniga bir marta har bir obuna uchun eng yuqori
bolalar sonini yozadi. Oʻz hujjatida yozilganidek: **oʻtkazib
yuborilgan kun qaytarib boʻlmaydi** — oʻtmishdagi bolalar sonini
qayta tiklab boʻlmaydi, va oʻlchov tushib qolsa hisob KAMAYADI.

Shunday boʻlsa ham vazifa faqat muvaffaqiyatlarni sanardi: beshta
obunadan ikkitasi yiqilsa, javob `{"measured": 3}` boʻlardi va uni
oʻqigan odam buni "uchta obuna bor ekan" deb tushunardi. Xato faqat
log'da qolardi — yaʼni hech kim koʻrmaydigan joyda, chunki hech kim
muvaffaqiyatli kechaning log'ini oʻqimaydi.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from apps.subscriptions import tasks

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def test_a_failed_measurement_is_reported_not_just_logged(tenant_a: Any, tenant_b: Any):
    """Ikkita obuna, bittasi yiqiladi — javob buni AYTISHI kerak."""
    calls = {"n": 0}

    def _boom(**kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("baza javob bermadi")
        return None

    with patch.object(tasks.services, "record_daily_usage", side_effect=_boom):
        result = tasks.record_daily_peak()

    assert result["measured"] == 1
    assert result["failed"] == 1


def test_a_clean_run_reports_no_failures(tenant_a: Any):
    with patch.object(tasks.services, "record_daily_usage", return_value=None):
        result = tasks.record_daily_peak()

    assert result["failed"] == 0
    assert result["measured"] >= 1


def test_a_failed_period_close_is_reported(tenant_a: Any):
    """
    Davrni yopish ham xuddi shunday: yiqilgan obuna hisob OLMAYDI,
    va javobda bu koʻrinishi kerak.
    """
    with (
        patch.object(tasks, "_live_subscriptions", return_value=[_broken_subscription(tenant_a)]),
        patch.object(tasks.services, "record_daily_usage", side_effect=RuntimeError("xato")),
    ):
        result = tasks.close_periods_and_invoice()

    assert result["failed"] == 1


def _broken_subscription(tenant: Any) -> Any:
    """Davri tugagan, faol obuna — yopilishi kerak boʻlgan holat."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.core.tenancy import organization_context
    from apps.subscriptions.models import Subscription, SubscriptionStatus

    with organization_context(tenant.organization.id):
        subscription = Subscription.objects.get(organization=tenant.organization)
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = timezone.localdate() - timedelta(days=31)
        subscription.current_period_end = timezone.localdate() - timedelta(days=1)
        subscription.save(update_fields=["status", "current_period_start", "current_period_end"])
        return subscription
