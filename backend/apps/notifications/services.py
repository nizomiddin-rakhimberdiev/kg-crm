"""
Bildirishnoma mantiqi (docs/03 §17.2, docs/04 §15).

Oqim: navbatga qo'yish → yuborish → jurnalga yozish. Yuborish HAR DOIM
alohida qadam: SMS shlyuzi sekin yoki mavjud bo'lmasligi mumkin va uni
so'rov ichida kutish to'lov qabul qilishni sekinlashtirardi (P8).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from string import Template
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import BusinessRuleViolation
from apps.notifications.models import (
    Channel,
    Notification,
    NotificationStatus,
    NotificationTemplate,
    TemplateCode,
)
from apps.notifications.providers import get_provider

logger = logging.getLogger(__name__)

__all__ = [
    "seed_default_templates",
    "render_template",
    "queue_notification",
    "dispatch_notification",
    "notify_payment_received",
    "queue_debt_reminders",
]

# Signup'da seed qilinadigan boshlang'ich shablonlar. Bog'cha ularni
# tahrirlashi mumkin — matn mahsulot qarori emas, mijoz qarori.
DEFAULT_TEMPLATES: dict[str, str] = {
    TemplateCode.PAYMENT_RECEIVED: (
        "Hurmatli ${guardian}! ${child} uchun ${amount} so'm to'lov qabul qilindi. "
        "Rahmat! ${organization}"
    ),
    TemplateCode.DEBT_REMINDER: (
        "Hurmatli ${guardian}! ${child} bo'yicha ${amount} so'm qarzdorlik mavjud. "
        "Iltimos, to'lovni amalga oshiring. ${organization}"
    ),
    TemplateCode.ABSENCE_NOTICE: (
        "Hurmatli ${guardian}! ${child} bugun bog'chaga kelmadi. ${organization}"
    ),
}


def seed_default_templates(organization: Any) -> int:
    """Tashkilot uchun boshlang'ich shablonlarni yaratadi (idempotent)."""
    created = 0
    for code, body in DEFAULT_TEMPLATES.items():
        _, was_created = NotificationTemplate.all_objects.get_or_create(
            organization=organization,
            code=code,
            channel=Channel.SMS,
            branch=None,
            defaults={"body": body},
        )
        created += int(was_created)
    return created


def render_template(body: str, variables: dict[str, Any]) -> str:
    """
    Shablonni to'ldiradi.

    `string.Template` ishlatiladi, f-string yoki `.format()` emas:
    shablon matnini MIJOZ tahrirlaydi, va `.format()` da tasodifiy `{`
    belgisi butun yuborishni yiqitardi. `safe_substitute` esa noma'lum
    o'rinbosarni matnda qoldiradi — xabar baribir ketadi.
    """
    return Template(body).safe_substitute(
        {key: ("" if value is None else str(value)) for key, value in variables.items()}
    )


def _resolve_template(
    *, organization: Any, code: str, channel: str = Channel.SMS, branch: Any = None
) -> NotificationTemplate | None:
    """Filialga xos shablon global shablonni qoplaydi."""
    queryset = NotificationTemplate.objects.filter(code=code, channel=channel, is_active=True)
    if branch is not None:
        specific = queryset.filter(branch=branch).first()
        if specific:
            return specific
    return queryset.filter(branch__isnull=True).first()


@transaction.atomic
def queue_notification(
    *,
    organization: Any,
    branch: Any,
    guardian: Any,
    code: str,
    variables: dict[str, Any] | None = None,
    channel: str = Channel.SMS,
    body_override: str | None = None,
    scheduled_for: Any = None,
) -> Notification | None:
    """
    Xabarni navbatga qo'yadi.

    Vasiy telefonsiz bo'lsa `None` qaytaradi — bu xato emas, oddiy holat
    (import qilingan bola vasiysiz bo'lishi mumkin). Istisno ko'tarish
    to'lov qabul qilishni yiqitardi, holbuki to'lovning o'zi muvaffaqiyatli.
    """
    address = (getattr(guardian, "phone", "") or "").strip()
    if not address:
        logger.info("Bildirishnoma o'tkazib yuborildi: vasiyda telefon yo'q")
        return None

    template = _resolve_template(
        organization=organization, code=code, channel=channel, branch=branch
    )
    body = body_override or (template.body if template else DEFAULT_TEMPLATES.get(code, ""))
    if not body:
        raise BusinessRuleViolation(f"'{code}' uchun shablon topilmadi.")

    return Notification.objects.create(
        organization=organization,
        branch=branch,
        template=template,
        guardian=guardian,
        channel=channel,
        # Manzil va matn SNAPSHOT: vasiy telefonini keyin o'zgartirsa ham
        # jurnalda AYNAN qayerga nima yuborilgani ko'rinib turishi kerak.
        recipient_address=address[:120],
        rendered_body=render_template(body, variables or {}),
        scheduled_for=scheduled_for,
    )


def dispatch_notification(notification: Notification) -> Notification:
    """
    Bitta xabarni provayderga uzatadi va natijani jurnalga yozadi.

    Xato bo'lsa `failed` holatiga o'tadi va sabab saqlanadi — keyin
    `retry` orqali qayta urinish mumkin. Xato JIMGINA yo'qolmaydi:
    "SMS kelmadi" degan shikoyatga javob jurnalda bo'lishi kerak.
    """
    if notification.status not in (NotificationStatus.QUEUED, NotificationStatus.FAILED):
        raise BusinessRuleViolation(
            f"'{notification.get_status_display()}' holatidagi xabarni yuborib bo'lmaydi."
        )

    provider = get_provider(notification.channel)
    result = provider.send(address=notification.recipient_address, body=notification.rendered_body)

    if result.success:
        notification.status = NotificationStatus.SENT
        notification.provider_message_id = result.provider_message_id[:120]
        notification.sent_at = timezone.now()
        notification.error = ""
    else:
        notification.status = NotificationStatus.FAILED
        notification.error = result.error
        notification.retry_count += 1

    notification.save(
        update_fields=[
            "status",
            "provider_message_id",
            "sent_at",
            "error",
            "retry_count",
            "updated_at",
        ]
    )
    return notification


# --- Hodisalarni ulash (docs/06 Sprint 8) ---


def notify_payment_received(*, payment: Any) -> Notification | None:
    """
    To'lov qabul qilinganda ota-onaga SMS.

    Chaqiruvchi (to'lov servisi) bu funksiyaning xatosidan ta'sirlanmasligi
    kerak: pul allaqachon qabul qilingan va yozilgan. Shuning uchun
    istisno ushlanadi va log'ga yoziladi.
    """
    child = payment.child
    primary = child.guardian_links.filter(is_primary=True).select_related("guardian").first()
    if primary is None:
        primary = child.guardian_links.select_related("guardian").first()
    if primary is None:
        return None

    try:
        return queue_notification(
            organization=payment.organization,
            branch=payment.branch,
            guardian=primary.guardian,
            code=TemplateCode.PAYMENT_RECEIVED,
            variables={
                "guardian": primary.guardian.full_name,
                "child": child.full_name,
                "amount": f"{payment.amount:,.0f}".replace(",", " "),
                "organization": payment.organization.name,
            },
        )
    except Exception:  # noqa: BLE001 — to'lov bildirishnoma tufayli yiqilmasin
        logger.exception("To'lov bildirishnomasini navbatga qo'yib bo'lmadi")
        return None


def queue_debt_reminders(
    *, organization: Any, min_amount: Decimal | None = None
) -> list[Notification]:
    """
    Barcha qarzdorlarga eslatma navbatga qo'yadi (docs/04 §10).

    Qarzdorlar ro'yxati ledger'dan hisoblanadi — alohida jadvaldan emas
    (ADR-7), shuning uchun eslatma hech qachon allaqachon to'lagan
    ota-onaga ketmaydi.
    """
    from apps.finance.selectors import debtor_queryset

    queued: list[Notification] = []
    children = debtor_queryset(min_amount=min_amount).prefetch_related("guardian_links__guardian")

    for child in children:
        links = list(child.guardian_links.all())
        primary = next((link for link in links if link.is_primary), next(iter(links), None))
        if primary is None:
            continue

        notification = queue_notification(
            organization=organization,
            branch=child.branch,
            guardian=primary.guardian,
            code=TemplateCode.DEBT_REMINDER,
            variables={
                "guardian": primary.guardian.full_name,
                "child": child.full_name,
                "amount": f"{child.ledger_balance:,.0f}".replace(",", " "),
                "organization": organization.name,
            },
        )
        if notification:
            queued.append(notification)

    return queued
