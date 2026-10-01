"""
Bildirishnoma o'qishlari (docs/02 §5 — o'qish `selectors.py` da).

Asosiy savol, mudira so'raydigan: "bu oy nechta SMS ketdi va u menga
qanchaga tushdi?" Javob jurnaldan hisoblanadi — alohida hisoblagich
yuritilmaydi, chunki hisoblagich jurnaldan ajralib ketadi va qaysi biri
to'g'ri ekanini aniqlash imkonsiz bo'lib qoladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Count, Max, Q

from apps.notifications.models import Notification, NotificationStatus
from apps.notifications.providers import is_test_mode
from apps.notifications.segments import parts_for

__all__ = ["monthly_usage", "sms_status", "last_reminders"]


def monthly_usage(*, year: int, month: int, branch_id: Any = None) -> dict[str, Any]:
    """
    Bir oyning yuborish hisobi: soni, bo'laklari va taxminiy narxi.

    Bo'laklar Python'da sanaladi, SQL'da emas: hisob alifboga bog'liq
    (lotin 160, kirill 70) va uni SQL'da takrorlash ikkita haqiqat
    manbai yaratardi. Bir oyda bir bog'cha uchun bu bir necha ming
    qator — sikl arzon.
    """
    from apps.settings_app.services import get_setting

    queryset = Notification.objects.filter(created_at__year=year, created_at__month=month)
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    counts = queryset.aggregate(
        total=Count("id"),
        sent=Count("id", filter=Q(status=NotificationStatus.SENT)),
        failed=Count("id", filter=Q(status=NotificationStatus.FAILED)),
        queued=Count("id", filter=Q(status=NotificationStatus.QUEUED)),
        test_mode=Count("id", filter=Q(status=NotificationStatus.TEST_MODE)),
    )

    # Narx faqat HAQIQATAN ketgan xabarlar uchun: test rejimidagi
    # xabar hech qayerga bormagan va hech narsa turmaydi.
    billable = queryset.filter(status=NotificationStatus.SENT).values_list(
        "rendered_body", flat=True
    )
    parts = sum(parts_for(body) for body in billable)

    price = Decimal(str(get_setting(key="notifications.sms_price") or "0"))
    return {
        "year": year,
        "month": month,
        **counts,
        "parts": parts,
        "price_per_part": price,
        # Narx kiritilmagan bo'lsa `None` — nol emas. "0 so'm" deb
        # ko'rsatish SMS bepul degan ma'noni berardi.
        "estimated_cost": (price * parts) if price > 0 else None,
    }


def sms_status(*, branch: Any = None, today: date | None = None) -> dict[str, Any]:
    """
    Bildirishnomalar sahifasining bosh holati — banner shunga qaraydi.

    `test_mode` eng muhim maydon: haqiqiy provayder ulanmaguncha hech
    bir xabar ota-onaga bormaydi, va ekran buni ochiq aytishi kerak
    (PLAN 3.2).
    """
    from django.conf import settings

    from apps.settings_app.services import get_setting

    today = today or date.today()
    return {
        "test_mode": is_test_mode(),
        "provider": getattr(settings, "NOTIFICATION_PROVIDER", "console"),
        "sms_enabled": bool(get_setting(key="notifications.sms_enabled", branch=branch)),
        "send_from_hour": int(get_setting(key="notifications.send_from_hour", branch=branch) or 0),
        "send_to_hour": int(get_setting(key="notifications.send_to_hour", branch=branch) or 24),
        "reminders_per_day": int(
            get_setting(key="notifications.debt_reminders_per_day", branch=branch) or 0
        ),
        "max_retries": int(get_setting(key="notifications.max_retries", branch=branch) or 0),
        "usage": monthly_usage(
            year=today.year, month=today.month, branch_id=getattr(branch, "id", None)
        ),
    }


def last_reminders(*, guardian_ids: list[Any]) -> dict[Any, Any]:
    """
    Har bir vasiyga OXIRGI qarz eslatmasi qachon ketgan.

    Qarzdorlar ro'yxatidagi "oxirgi eslatma" ustuni shu yerdan keladi.
    Bitta so'rovda: 200 qarzdor uchun qator-qator so'rash 200 ta
    so'rovga aylanardi.

    Nega `notifications` tomonida: `finance` boshqa modulning modelini
    import qilmaydi (CLAUDE.md, invariant 1) — u shu selektorni
    chaqiradi.
    """
    if not guardian_ids:
        return {}

    rows = (
        Notification.objects.filter(
            guardian_id__in=guardian_ids,
            template__code="debt_reminder",
        )
        .values("guardian_id")
        .annotate(last_at=Max("created_at"))
    )
    return {row["guardian_id"]: row["last_at"] for row in rows}
