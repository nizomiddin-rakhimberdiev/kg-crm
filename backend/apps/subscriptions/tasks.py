"""
Obuna fon vazifalari (docs/02 §18, docs/06 Sprint 10).

Hammasi **idempotent**: Celery kafolati "kamida bir marta", ya'ni qayta
ishga tushish normal holat. Ikki marta hisob yozish esa mijozni
yo'qotadigan turdagi xato — shuning uchun takroriylik bazadagi qisman
indeks bilan bloklanadi, kodda "shekilli yozgan edim" degan taxmin bilan
emas.

Har bir vazifa tashkilotlar bo'ylab aylanadi va HAR BIRI uchun tenant
kontekstini alohida o'rnatadi.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.core.tenancy import organization_context, platform_context
from apps.subscriptions import services

logger = logging.getLogger(__name__)

__all__ = [
    "record_daily_peak",
    "close_periods_and_invoice",
    "expire_trials_task",
    "dunning_task",
]


def _live_subscriptions() -> Any:
    from apps.subscriptions.models import Subscription, SubscriptionStatus

    # Barcha tenantlar bo'ylab — platforma tekisligi. `subscription`
    # metama'lumot jadvali, shuning uchun bu ruxsat etilgan; bolalar
    # yoki to'lovlar bu rejimda baribir ko'rinmaydi.
    with platform_context():
        return list(
            Subscription.all_objects.exclude(status=SubscriptionStatus.CANCELLED)
            .select_related("plan", "organization")
            .order_by("created_at")
        )


@shared_task(name="subscriptions.record_daily_peak")
def record_daily_peak() -> dict[str, int]:
    """
    Har kuni: har bir obuna uchun eng yuqori bolalar sonini yozadi.

    Bu vazifa **o'tkazib yuborilsa hisob kamayadi**, shuning uchun u
    kuniga bir marta va ertalab ishlaydi. O'tkazib yuborilgan kun
    qaytarib bo'lmaydi — o'tmishdagi bolalar sonini qayta tiklab
    bo'lmaydi — va aynan shuning uchun oy oxiridagi bitta o'lchovga
    tayanish xavfli edi.
    """
    measured = 0
    for subscription in _live_subscriptions():
        try:
            with organization_context(subscription.organization_id):
                services.record_daily_usage(subscription=subscription)
            measured += 1
        except Exception:
            logger.exception("Kunlik o'lchov muvaffaqiyatsiz: obuna=%s", subscription.id)
    return {"measured": measured}


@shared_task(name="subscriptions.close_periods_and_invoice")
def close_periods_and_invoice() -> dict[str, int]:
    """
    Davri tugagan obunalarni yopadi va keyingi hisobni yozadi.

    Oldindan to'langan muddat ichida baza qayta olinmaydi — faqat
    kelishilgan sondan oshgan o'sish hisoblanadi (docs/01 §4.3).
    """
    from apps.subscriptions.models import PaymentTerm, SubscriptionStatus

    today = timezone.localdate()
    closed = 0
    invoiced = 0

    for subscription in _live_subscriptions():
        if subscription.status in (
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.SUSPENDED,
        ):
            continue
        if subscription.current_period_end >= today:
            continue

        try:
            with organization_context(subscription.organization_id):
                snapshot = services.record_daily_usage(subscription=subscription)
                services.close_period(snapshot=snapshot)
                closed += 1

                prepaid_term = subscription.payment_term != PaymentTerm.MONTHLY
                committed = subscription.committed_children or 0
                grew = snapshot.billable_children > committed

                # Oldindan to'langan muddatda baza allaqachon olingan;
                # o'sish bo'lmasa yozadigan narsa yo'q.
                if prepaid_term and not grew:
                    _roll_period(subscription)
                    continue

                services.issue_invoice(
                    subscription=subscription,
                    snapshot=snapshot,
                    period_start=subscription.current_period_start,
                    period_end=subscription.current_period_end,
                    months=1,
                    include_base=not prepaid_term,
                )
                invoiced += 1
                _roll_period(subscription)
        except Exception:
            logger.exception("Davrni yopib bo'lmadi: obuna=%s", subscription.id)

    return {"closed": closed, "invoiced": invoiced}


def _roll_period(subscription: Any) -> None:
    """Keyingi davrga o'tkazadi."""
    from datetime import timedelta

    start = subscription.current_period_end + timedelta(days=1)
    end = services.add_months(start, 1) - timedelta(days=1)
    subscription.current_period_start = start
    subscription.current_period_end = end
    subscription.save(update_fields=["current_period_start", "current_period_end", "updated_at"])


@shared_task(name="subscriptions.expire_trials")
def expire_trials_task() -> int:
    """Qabul qilinmagan sinovlarni yopadi."""
    return services.expire_trials()


@shared_task(name="subscriptions.dunning")
def dunning_task() -> dict[str, int]:
    """
    Muddati o'tganlarni belgilaydi, keyin kutish muddati tugaganlarni
    faqat o'qishga o'tkazadi.

    Tartib muhim: avval `past_due`, keyin `suspended`. Teskarisi bo'lsa,
    hozirgina muddati o'tgan hisob darrov to'xtatishga olib kelardi va
    bank o'tkazmasi yo'lda bo'lgan mijoz ishdan chiqib qolardi.
    """
    return {"past_due": services.mark_past_due(), "suspended": services.suspend_unpaid()}
