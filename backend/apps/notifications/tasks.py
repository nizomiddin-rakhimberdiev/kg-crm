"""
Bildirishnomalarni yuborish (docs/02 §17).

Nega alohida vazifa kerak: `queue_notification()` faqat QATOR yozadi,
yuborish esa alohida qadam. Qarz eslatmalari o'z vazifasida darhol
uzatilardi, lekin TO'LOV KVITANSIYASI hech kim tomonidan uzatilmasdi —
u `queued` holatda abadiy qolardi. Ya'ni ota-ona to'lov qilgani haqida
xabar hech qachon olmasdi, va bu xatosiz, jimgina sodir bo'lardi.

Yuborish so'rov ichida emas, shu yerda: to'lovni qabul qilish SMS
shlyuzining tezligiga yoki tirikligiga bog'liq bo'lmasligi kerak (P8).
"""

from __future__ import annotations

import logging

from django.db.models import Q
from django.utils import timezone

from apps.core.tasks import reliable_task
from apps.core.tenancy import organization_context, platform_context

logger = logging.getLogger(__name__)

__all__ = ["dispatch_queued_notifications"]

# Necha marta qayta urinamiz. Undan keyin xabar `failed` holatida
# qoladi va uni odam ko'radi — cheksiz urinish shlyuzdagi doimiy
# nosozlikni log'ga ko'mib yuborardi.
#
# Sukut qiymat; bog'cha uni `notifications.max_retries` sozlamasidan
# o'zgartira oladi (PLAN 3.3).
MAX_ATTEMPTS = 3


@reliable_task(name="notifications.dispatch_queued")
def dispatch_queued_notifications(batch_size: int = 200) -> dict[str, int]:
    """
    Navbatdagi xabarlarni uzatadi — barcha tashkilotlar bo'ylab.

    Har bir tashkilot O'Z kontekstida ishlanadi, ya'ni bitta tsiklda ham
    tenant chegarasi saqlanadi.

    Qayta bajarilishi xavfsiz: faqat `queued` va urinishlari tugamagan
    `failed` xabarlar olinadi, muvaffaqiyatlisi esa `sent` bo'lib
    ro'yxatdan chiqadi. `acks_late` bilan qayta yetkazilgan vazifa
    shuning uchun takroriy SMS yubormaydi.
    """
    from apps.notifications.models import Notification, NotificationStatus
    from apps.notifications.services import dispatch_notification
    from apps.organizations.models import Organization
    from apps.settings_app.services import get_setting

    sent = failed = held = 0
    with platform_context():
        organizations = list(Organization.objects.filter(is_active=True))

    for organization in organizations:
        with organization_context(organization.id):
            if not get_setting(key="notifications.sms_enabled"):
                continue

            attempts = int(get_setting(key="notifications.max_retries") or MAX_ATTEMPTS)
            pending = (
                Notification.objects.filter(
                    Q(status=NotificationStatus.QUEUED)
                    | Q(status=NotificationStatus.FAILED, retry_count__lt=attempts)
                )
                .filter(
                    # Rejalashtirilgan xabar vaqti kelmaguncha kutadi.
                    Q(scheduled_for__isnull=True) | Q(scheduled_for__lte=timezone.now())
                )
                .order_by("created_at")[:batch_size]
            )

            for notification in pending:
                try:
                    result = dispatch_notification(notification)
                except Exception:  # noqa: BLE001 — bitta xabar butun tsiklni to'xtatmasin
                    logger.exception("Xabar uzatilmadi: %s", notification.id)
                    failed += 1
                    continue
                if result.status in (NotificationStatus.SENT, NotificationStatus.TEST_MODE):
                    sent += 1
                elif result.status == NotificationStatus.QUEUED:
                    # Yuborish oynasidan tashqarida (Q9) — xato emas,
                    # kutayotgan xabar. Uni `failed` deb sanash
                    # monitoringda soxta signal berardi.
                    held += 1
                else:
                    failed += 1

    return {"sent": sent, "failed": failed, "held": held}
