"""
Bildirishnoma mantiqi (docs/03 §17.2, docs/04 §15).

Oqim: navbatga qo'yish → yuborish → jurnalga yozish. Yuborish HAR DOIM
alohida qadam: SMS shlyuzi sekin yoki mavjud bo'lmasligi mumkin va uni
so'rov ichida kutish to'lov qabul qilishni sekinlashtirardi (P8).
"""

from __future__ import annotations

import logging
from datetime import date, time
from decimal import Decimal
from string import Template
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.notifications.models import (
    Channel,
    Notification,
    NotificationStatus,
    NotificationTemplate,
    TemplateCode,
    TemplateLanguage,
)
from apps.notifications.providers import get_provider
from apps.notifications.segments import parts_for, sms_safe

logger = logging.getLogger(__name__)

__all__ = [
    "seed_default_templates",
    "guardian_language",
    "TEMPLATE_VARIABLES",
    "preview_debt_reminders",
    "debt_reminder_targets",
    "render_template",
    "queue_notification",
    "dispatch_notification",
    "notify_payment_received",
    "queue_debt_reminders",
]

# Shablonda ishlatiladigan o'rinbosarlar — muharrirdagi tugmalar shu
# ro'yxatdan quriladi (PLAN 3.4). Ro'yxat KOD tomonida: mijoz o'zi
# o'ylab topgan `${summa}` hech narsaga almashmasdi va xabar shu
# ko'rinishda ota-onaga ketardi.
TEMPLATE_VARIABLES: dict[str, tuple[str, ...]] = {
    TemplateCode.PAYMENT_RECEIVED: ("guardian", "child", "amount", "organization"),
    TemplateCode.DEBT_REMINDER: ("guardian", "child", "amount", "days", "organization"),
    TemplateCode.ABSENCE_NOTICE: ("guardian", "child", "organization"),
    TemplateCode.CUSTOM: ("guardian", "child", "organization"),
}

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


#: Ruscha boshlang'ich matnlar (PLAN 3.4).
#:
#: Faqat SHU ikki til seed qilinadi: o'zbek va rus — O'zbekiston
#: bog'chalarida ota-onalarning amalda ishlatadigan tillari. Inglizcha
#: shablonni bog'cha o'zi qo'shadi, agar kerak bo'lsa.
DEFAULT_TEMPLATES_RU: dict[str, str] = {
    TemplateCode.PAYMENT_RECEIVED: (
        "Уважаемый(ая) ${guardian}! Оплата ${amount} сум за ${child} принята. "
        "Спасибо! ${organization}"
    ),
    TemplateCode.DEBT_REMINDER: (
        "Уважаемый(ая) ${guardian}! По ${child} числится задолженность ${amount} сум. "
        "Просим произвести оплату. ${organization}"
    ),
    TemplateCode.ABSENCE_NOTICE: (
        "Уважаемый(ая) ${guardian}! ${child} сегодня не пришёл(ла) в детский сад. ${organization}"
    ),
}


def seed_default_templates(organization: Any) -> int:
    """Tashkilot uchun boshlang'ich shablonlarni yaratadi (idempotent)."""
    created = 0
    catalogues = (
        (TemplateLanguage.UZ, DEFAULT_TEMPLATES),
        (TemplateLanguage.RU, DEFAULT_TEMPLATES_RU),
    )
    for language, bodies in catalogues:
        for code, body in bodies.items():
            _, was_created = NotificationTemplate.all_objects.get_or_create(
                organization=organization,
                code=code,
                channel=Channel.SMS,
                language=language,
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


def guardian_language(guardian: Any, branch: Any = None) -> str:
    """
    Ota-ona qaysi tilda xabar oladi (PLAN 3.4).

    Vasiyning o'z tili bo'lmasa — bog'chaning sukut tili. Bu xodimning
    interfeys tilidan MUSTAQIL: ruscha ishlaydigan mudira o'zbek
    oilasiga o'zbekcha SMS yuborishi kerak.
    """
    chosen = (getattr(guardian, "language", "") or "").strip()
    if chosen:
        return chosen
    return str(_rule("general.default_language", branch) or "uz")


def _resolve_template(
    *,
    organization: Any,
    code: str,
    channel: str = Channel.SMS,
    branch: Any = None,
    language: str = "",
) -> NotificationTemplate | None:
    """
    Shablonni tanlaydi: filial + til → global + til → filial → global.

    Til bo'yicha mos shablon topilmasa, xabar YUBORILMAY qolmaydi —
    o'zbekchasiga tushadi. Ota-ona uchun boshqa tildagi xabar ham
    hech qanday xabardan yaxshiroq.
    """
    queryset = NotificationTemplate.objects.filter(code=code, channel=channel, is_active=True)
    candidates = []
    if language:
        if branch is not None:
            candidates.append(queryset.filter(branch=branch, language=language))
        candidates.append(queryset.filter(branch__isnull=True, language=language))
    if branch is not None:
        candidates.append(queryset.filter(branch=branch))
    candidates.append(queryset.filter(branch__isnull=True))

    for candidate in candidates:
        found = candidate.first()
        if found:
            return found
    return None


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

    # Kunlik chegara (PLAN 3.3) — faqat qarz eslatmasiga. To'lov
    # kvitansiyasi yoki boshqa hodisa xabari cheklanmaydi: ular
    # takrorlanmaydi va har biri yangi ma'lumot.
    if code == TemplateCode.DEBT_REMINDER and not may_send_reminder(
        guardian=guardian, branch=branch
    ):
        logger.info("Eslatma o'tkazib yuborildi: bugun allaqachon yuborilgan")
        return None

    language = guardian_language(guardian, branch)
    template = _resolve_template(
        organization=organization, code=code, channel=channel, branch=branch, language=language
    )
    fallback = (DEFAULT_TEMPLATES_RU if language == "ru" else DEFAULT_TEMPLATES).get(code, "")
    body = body_override or (template.body if template else fallback)
    if not body:
        raise BusinessRuleViolation(gettext("'{code}' uchun shablon topilmadi.").format(code=code))

    return Notification.objects.create(
        organization=organization,
        branch=branch,
        template=template,
        guardian=guardian,
        channel=channel,
        # Manzil va matn SNAPSHOT: vasiy telefonini keyin o'zgartirsa ham
        # jurnalda AYNAN qayerga nima yuborilgani ko'rinib turishi kerak.
        recipient_address=address[:120],
        # Q11: `ʻ` va `ʼ` oddiy `'` ga almashtiriladi. Ular GSM-7 da
        # yo'q va bitta shunday belgi 160 belgilik xabarni 70 belgilik
        # UCS-2 xabariga aylantiradi — narx ikki baravar.
        rendered_body=(
            sms_safe(render_template(body, variables or {}))
            if channel == Channel.SMS
            else render_template(body, variables or {})
        ),
        scheduled_for=scheduled_for,
    )


# --- Yuborish qoidalari (PLAN 3.3, Q9) ---


def _rule(key: str, branch: Any = None) -> Any:
    from apps.settings_app.services import get_setting

    return get_setting(key=key, branch=branch)


def within_sending_window(at_time: time | None = None, branch: Any = None) -> bool:
    """
    Hozir xabar yuborish mumkinmi? (Q9)

    Tungi SMS ota-onani uyg'otadi va bog'cha haqida eng yomon
    taassurot qoldiradi; qarz eslatmasi esa bir necha soat kutsa hech
    narsa yo'qotmaydi. Shuning uchun oyna tashqarisidagi xabar
    YO'QOLMAYDI — u navbatda qoladi va ertalab ketadi.
    """
    at_time = at_time or timezone.localtime().time()
    start = int(_rule("notifications.send_from_hour", branch) or 0)
    end = int(_rule("notifications.send_to_hour", branch) or 24)
    return start <= at_time.hour < end


def delivery_problem(address: str) -> str:
    """
    Raqam bilan bog'liq muammo — bo'sh satr bo'lsa hammasi joyida.

    Noto'g'ri raqamga urinish ma'nosiz: provayder uni qabul qilishi
    ham mumkin va o'shanda jurnalda "yuborildi" deb turadi, ota-ona
    esa hech narsa olmaydi. Auditda aynan shunday bo'lgan — "12345"
    raqamiga yuborilgan xabar "Yuborildi" holatida edi.
    """
    from apps.core.phone import is_valid_phone

    if not address.strip():
        return gettext("Telefon raqami yo'q")
    if not is_valid_phone(address):
        return gettext("Noto'g'ri raqam")
    return ""


def reminders_sent_today(*, guardian_id: Any, on_date: date | None = None) -> int:
    """Shu vasiyga bugun nechta qarz eslatmasi ketgan."""
    day = on_date or timezone.localdate()
    return Notification.objects.filter(
        guardian_id=guardian_id,
        template__code=TemplateCode.DEBT_REMINDER,
        created_at__date=day,
    ).count()


def may_send_reminder(*, guardian: Any, branch: Any = None) -> bool:
    """
    Bugun yana bitta eslatma yuborish mumkinmi? (PLAN 3.3)

    Ikkinchi SMS yangi ma'lumot bermaydi, faqat bezovta qiladi —
    va ommaviy yuborish tugmasi ikki marta bosilsa ota-ona buni
    sezmaydi.
    """
    limit = int(_rule("notifications.debt_reminders_per_day", branch) or 0)
    if limit <= 0:
        return True
    return reminders_sent_today(guardian_id=guardian.id) < limit


def dispatch_notification(
    notification: Notification, *, now_time: time | None = None
) -> Notification:
    """
    Bitta xabarni provayderga uzatadi va natijani jurnalga yozadi.

    Xato bo'lsa `failed` holatiga o'tadi va sabab saqlanadi — keyin
    `retry` orqali qayta urinish mumkin. Xato JIMGINA yo'qolmaydi:
    "SMS kelmadi" degan shikoyatga javob jurnalda bo'lishi kerak.
    """
    if notification.status not in (NotificationStatus.QUEUED, NotificationStatus.FAILED):
        raise BusinessRuleViolation(
            gettext("'{status}' holatidagi xabarni yuborib bo'lmaydi.").format(
                status=notification.get_status_display()
            )
        )

    # 1. Raqam (PLAN 3.1). Noto'g'ri raqamga URINILMAYDI ham: provayder
    #    uni qabul qilishi mumkin va o'shanda jurnal "yuborildi" deb
    #    turadi, ota-ona esa hech narsa olmaydi.
    problem = delivery_problem(notification.recipient_address)
    if problem:
        notification.status = NotificationStatus.FAILED
        notification.error = problem
        notification.save(update_fields=["status", "error", "updated_at"])
        return notification

    # 2. Soat (Q9). Oyna tashqarisida xabar YO'QOLMAYDI — navbatda
    #    qoladi va `dispatch_queued` uni ertalab oladi.
    if not within_sending_window(now_time, branch=notification.branch):
        return notification

    # 3. Provayder sozlanganmi. Yarim sozlangan shlyuz (masalan
    #    `ESKIZ_FROM` yo'q) so'rovni `500` bilan yiqitardi — holbuki
    #    bu sozlama xatosi va javobi jurnalda sabab bilan turishi
    #    kerak.
    try:
        provider = get_provider(notification.channel)
    except ImproperlyConfigured as exc:
        logger.error("SMS provayderi sozlanmagan: %s", exc)
        notification.status = NotificationStatus.FAILED
        notification.error = gettext("SMS provayderi sozlanmagan.")
        notification.save(update_fields=["status", "error", "updated_at"])
        return notification

    result = provider.send(address=notification.recipient_address, body=notification.rendered_body)

    if result.success:
        # Test rejimi "Yuborildi" EMAS (PLAN 3.2): provayder ulanmagan
        # bo'lsa, xabar hech qayerga ketmagan va jurnal buni aytishi
        # kerak.
        notification.status = (
            NotificationStatus.TEST_MODE if result.test_mode else NotificationStatus.SENT
        )
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


def debt_reminder_targets(
    *,
    min_amount: Decimal | None = None,
    min_days: int | None = None,
    group_id: Any = None,
    child_ids: list[Any] | None = None,
) -> Any:
    """
    Eslatma KIMGA ketishi — ko'rib chiqish va yuborish uchun BIR xil
    ro'yxat.

    Ikkita alohida so'rov yozilsa, ko'rib chiqishda "48 ta" deb
    ko'rsatib, 51 tasiga yuborish holati paydo bo'lardi — va buni hech
    kim sezmasdi.
    """
    from apps.finance.selectors import debtor_queryset

    queryset = debtor_queryset(min_amount=min_amount, min_days=min_days, group_id=group_id)
    if child_ids:
        queryset = queryset.filter(id__in=child_ids)
    return queryset.prefetch_related("guardian_links__guardian")


def preview_debt_reminders(
    *,
    min_amount: Decimal | None = None,
    min_days: int | None = None,
    group_id: Any = None,
    child_ids: list[Any] | None = None,
) -> dict[str, Any]:
    """
    Ommaviy yuborishdan OLDINGI ko'rib chiqish (PLAN 3.5).

    "Eslatma yuborish" tugmasi 200 ta SMS yuborishi mumkin va uni
    qaytarib bo'lmaydi. Shuning uchun tasdiqdan oldin aniq son
    ko'rsatiladi: nechtasiga ketadi, nechtasi telefonsiz, nechtasi
    bugun allaqachon olgan va taxminan qanchaga tushadi.
    """
    from apps.settings_app.services import get_setting

    eligible = 0
    no_phone = 0
    already = 0
    parts = 0
    seen: set[Any] = set()

    for child in debt_reminder_targets(
        min_amount=min_amount, min_days=min_days, group_id=group_id, child_ids=child_ids
    ):
        links = list(child.guardian_links.all())
        primary = next((link for link in links if link.is_primary), next(iter(links), None))
        if primary is None or not (primary.guardian.phone or "").strip():
            no_phone += 1
            continue
        if primary.guardian_id in seen:
            continue
        seen.add(primary.guardian_id)
        if not may_send_reminder(guardian=primary.guardian, branch=child.branch):
            already += 1
            continue
        eligible += 1
        parts += parts_for(
            sms_safe(
                render_template(
                    DEFAULT_TEMPLATES[TemplateCode.DEBT_REMINDER],
                    {
                        "guardian": primary.guardian.full_name,
                        "child": child.full_name,
                        "amount": f"{child.ledger_balance:,.0f}".replace(",", " "),
                        "organization": "",
                    },
                )
            )
        )

    price = Decimal(str(get_setting(key="notifications.sms_price") or "0"))
    return {
        "eligible": eligible,
        "skipped_no_phone": no_phone,
        "skipped_already_sent": already,
        "parts": parts,
        "estimated_cost": str(price * parts) if price > 0 else None,
    }


def queue_debt_reminders(
    *,
    organization: Any,
    min_amount: Decimal | None = None,
    min_days: int | None = None,
    group_id: Any = None,
    child_ids: list[Any] | None = None,
) -> list[Notification]:
    """
    Qarzdorlarga eslatma navbatga qo'yadi (docs/04 §10).

    Qarzdorlar ro'yxati ledger'dan hisoblanadi — alohida jadvaldan emas
    (ADR-7), shuning uchun eslatma hech qachon allaqachon to'lagan
    ota-onaga ketmaydi.
    """
    queued: list[Notification] = []
    children = debt_reminder_targets(
        min_amount=min_amount, min_days=min_days, group_id=group_id, child_ids=child_ids
    )

    # Bugun allaqachon eslatma olgan vasiylar — ular ikkinchi marta
    # olmasligi kerak.
    #
    # Bu tekshiruv Celery `task_acks_late` bilan birga MAJBURIY bo'lib
    # qoldi: `acks_late` ishchi vazifa o'rtasida yiqilsa uni QAYTA
    # yetkazadi, va bu to'g'ri xatti-harakat — yo'qolgan hisob-fakturadan
    # ko'ra takrorlangani yaxshi. Lekin SMS uchun teskari: takrorlangan
    # "qarzingiz bor" xabari ota-onaga ikki marta boradi va bog'chaning
    # obro'siga tegadi. Shuning uchun takrorlanishni vazifa emas, SHU
    # YER to'xtatadi.
    #
    # Sana bo'yicha: eslatma kuniga bir marta yuboriladi (beat jadvali
    # `crontab(hour=10)`), ya'ni "bugun yuborilganmi?" to'g'ri savol.
    today = timezone.localdate()
    already_reminded = set(
        Notification.objects.filter(
            template__code=TemplateCode.DEBT_REMINDER,
            created_at__date=today,
        ).values_list("guardian_id", flat=True)
    )

    for child in children:
        links = list(child.guardian_links.all())
        primary = next((link for link in links if link.is_primary), next(iter(links), None))
        if primary is None:
            continue
        if primary.guardian_id in already_reminded:
            continue
        # Bir vasiyning bir nechta bolasi bo'lishi mumkin — u ham bitta
        # eslatma olsin, har bir bola uchun alohida emas.
        already_reminded.add(primary.guardian_id)

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
