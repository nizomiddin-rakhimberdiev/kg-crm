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

from apps.notifications.models import Channel, Notification, NotificationStatus
from apps.notifications.providers import is_test_mode
from apps.notifications.segments import parts_for

__all__ = ["monthly_usage", "sms_status", "last_reminders", "telegram_reach"]


def monthly_usage(*, year: int, month: int, branch_id: Any = None) -> dict[str, Any]:
    """
    Bir oyning yuborish hisobi: soni, bo'laklari va taxminiy narxi.

    **Narx faqat SMS uchun.** Telegram bepul, shuning uchun uning
    xabarlari bo'laklarga ham sanalmaydi — aks holda ekran bog'chaga
    to'lamaydigan pulni ko'rsatardi (ADR-23).

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
        telegram=Count("id", filter=Q(channel=Channel.TELEGRAM)),
        sms=Count("id", filter=Q(channel=Channel.SMS)),
    )

    # Narx faqat HAQIQATAN ketgan SMS'lar uchun: test rejimidagi
    # xabar hech qayerga bormagan, Telegram esa bepul.
    billable = queryset.filter(status=NotificationStatus.SENT, channel=Channel.SMS).values_list(
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


def telegram_reach(*, branch_id: Any = None) -> dict[str, Any]:
    """
    Nechta ota-ona botga ulangan (PLAN 3.7).

    Bu asosiy kanalning qamrovi: ulanmagan ota-ona hech qanday xabar
    olmaydi va bog'cha buni RAQAM bilan ko'rishi kerak — "nega
    hech kim to'lamadi?" degan savolning javobi ko'pincha shu yerda.
    """
    from apps.children.models import Guardian

    queryset = Guardian.objects.filter(is_active=True)
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)
    total = queryset.count()
    linked = queryset.exclude(telegram_chat_id="").count()
    return {"linked": linked, "total": total}


def sms_status(*, branch: Any = None, today: date | None = None) -> dict[str, Any]:
    """
    Bildirishnomalar sahifasining bosh holati — banner shunga qaraydi.

    `test_mode` eng muhim maydon: **ishlatilayotgan kanalda** haqiqiy
    provayder ulanmaguncha hech bir xabar ota-onaga bormaydi, va ekran
    buni ochiq aytishi kerak (PLAN 3.2). Savol kanal bo'yicha: Telegram
    ulangan, SMS esa ulanmagan holat normal (ADR-23).
    """

    from apps.children.telegram import bot_username
    from apps.notifications.providers import provider_name
    from apps.settings_app.services import get_setting

    today = today or date.today()
    default_channel = str(
        get_setting(key="notifications.default_channel", branch=branch) or Channel.TELEGRAM
    )
    return {
        "default_channel": default_channel,
        "test_mode": is_test_mode(default_channel),
        "provider": provider_name(default_channel),
        "channels": {
            "telegram": {
                "configured": not is_test_mode(Channel.TELEGRAM),
                "bot_username": bot_username(),
                "reach": telegram_reach(branch_id=getattr(branch, "id", None)),
            },
            "sms": {
                "configured": not is_test_mode(Channel.SMS),
                "provider": provider_name(Channel.SMS),
            },
        },
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
            template_code="debt_reminder",
        )
        .values("guardian_id")
        .annotate(last_at=Max("created_at"))
    )
    return {row["guardian_id"]: row["last_at"] for row in rows}
