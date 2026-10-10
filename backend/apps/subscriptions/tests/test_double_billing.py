"""
Bitta davr uchun ikkita hisob yozilmasin (PLAN 11.7).

`CELERY_TASK_ACKS_LATE = True` va `REJECT_ON_WORKER_LOST = True` —
yaʼni ishchi yiqilsa vazifa QAYTA yetkaziladi. Bu ataylab: yarim
bajarilgan ish yoʻqolmasligi kerak. Lekin shuning uchun har bir
vazifa ikki marta ishlashga chidashi shart.

`close_periods_and_invoice` ichida ketma-ketlik bor: oʻlchovni yop →
hisob yoz → davrni keyingisiga surish. Ular bitta tranzaksiyada emas
edi, yaʼni ishchi hisob yozilgandan KEYIN, davr surilishidan OLDIN
yiqilsa — qayta yetkazishda `current_period_end` hali oʻtmishda
boʻlardi, qoʻriqchi oʻtkazib yuborardi va mijoz **ikkinchi marta**
hisob olardi.

Bazada ham tutqich yoʻq edi: tuition `invoice` da
`uq_invoice_child_period` bor, obuna hisob-fakturasida esa hech narsa.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.db.utils import IntegrityError
from django.utils import timezone

from apps.core.tenancy import organization_context
from apps.subscriptions import services
from apps.subscriptions.models import (
    MeasurementMethod,
    Subscription,
    SubscriptionInvoice,
    SubscriptionStatus,
)

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _ready_subscription(tenant: Any) -> Subscription:
    """Davri tugagan faol obuna — yopilishi kerak boʻlgan holat."""
    with organization_context(tenant.organization.id):
        subscription = Subscription.objects.get(organization=tenant.organization)
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_start = timezone.localdate() - timedelta(days=31)
        subscription.current_period_end = timezone.localdate() - timedelta(days=1)
        subscription.save(update_fields=["status", "current_period_start", "current_period_end"])
        return subscription


def test_the_database_refuses_a_second_invoice_for_one_period(tenant_a: Any):
    """Oxirgi tutqich — bazada. Kod xatosi ham undan oʻtmasin."""
    subscription = _ready_subscription(tenant_a)
    with organization_context(tenant_a.organization.id):
        snapshot = services.record_daily_usage(subscription=subscription)
        services.close_period(snapshot=snapshot)
        first = services.issue_invoice(
            subscription=subscription,
            snapshot=snapshot,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        assert first.pk is not None

        with pytest.raises(IntegrityError):
            services.issue_invoice(
                subscription=subscription,
                snapshot=snapshot,
                period_start=subscription.current_period_start,
                period_end=subscription.current_period_end,
            )


def test_a_cancelled_invoice_does_not_block_reissuing(tenant_a: Any):
    """
    Bekor qilingan hisob yoʻlni toʻsmasligi kerak — aks holda xato
    yozilgan hisobni bekor qilib, toʻgʻrisini yozib boʻlmasdi.
    """
    subscription = _ready_subscription(tenant_a)
    with organization_context(tenant_a.organization.id):
        snapshot = services.record_daily_usage(subscription=subscription)
        services.close_period(snapshot=snapshot)
        first = services.issue_invoice(
            subscription=subscription,
            snapshot=snapshot,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        first.status = "cancelled"
        first.save(update_fields=["status"])

        second = services.issue_invoice(
            subscription=subscription,
            snapshot=snapshot,
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
        )
        assert second.pk != first.pk


def test_running_the_task_twice_bills_once(tenant_a: Any):
    """
    Vazifaning oʻzi: ikki marta chaqirilsa ham bitta hisob.

    Birinchi chaqiruvdan keyin davr surilgan boʻlishi kerak — shunda
    ikkinchisi qoʻriqchida toʻxtaydi.
    """
    from apps.subscriptions.tasks import close_periods_and_invoice

    _ready_subscription(tenant_a)
    first = close_periods_and_invoice()
    second = close_periods_and_invoice()

    with organization_context(tenant_a.organization.id):
        issued = SubscriptionInvoice.objects.filter(
            usage_snapshot__measurement_method=MeasurementMethod.DAILY_PEAK
        ).count()

    assert first["invoiced"] == 1
    assert second["invoiced"] == 0
    assert issued == 1
