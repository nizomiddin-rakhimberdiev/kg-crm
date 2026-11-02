"""
Kelmagan kunlar uchun qaytarish (ADR-19, docs/03 §12.2).

Uchta qaror shu faylda yashaydi va uchalasi ham ataylab:

1. **Ish kuni** — bog'chaning ish kunlari minus bayramlar. Bog'cha
   yopiq bo'lgan kun ota-ona sog'inган kun emas.
2. **Kun narxi** = o'sha oyning hisob-fakturasi ÷ o'sha oydagi ish
   kunlari. `tarif ÷ 30` EMAS: 22 ish kunlik oyni 30 ga bo'lish
   ota-onaga u to'lamagan pulni qaytarib berardi. Va tarifdan emas,
   HISOBLANGAN summadan: chegirmasi bor bolaga to'laganidan ko'p
   qaytmasligi uchun.
3. **Raqamlar tasdiqlashda muzlatiladi.** Keyingi oy o'zgargan tarif
   allaqachon berilgan chegirmani qimirlatmaydi.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.attendance.models_absence import (
    AbsenceClaim,
    AbsenceKind,
    ClaimKind,
    ClaimStatus,
    Holiday,
    RefundMode,
)
from apps.core.exceptions import BusinessRuleViolation

__all__ = [
    "ensure_absence_kinds",
    "kind_for",
    "create_claim",
    "attach_document",
    "working_weekdays",
    "working_days_in_month",
    "billable_days",
    "daily_rate_for",
    "approve_claim",
    "can_approve_now",
    "cancel_claim",
    "reject_claim",
    "pending_credits",
]


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def working_weekdays(branch: Any = None) -> set[int]:
    """
    Bog'cha ishlaydigan hafta kunlari — ISO (1 = dushanba).

    Sozlamada, chunki shanba ishlaydigan bog'cha sxema o'zgarishi emas.
    """
    from apps.settings_app.services import get_setting

    raw = str(get_setting(key="attendance.working_weekdays", branch=branch) or "")
    days = {int(part) for part in raw.split(",") if part.strip().isdigit()}
    return days or {1, 2, 3, 4, 5}


def _holidays(organization_id: Any, date_from: date, date_to: date) -> set[date]:
    return set(
        Holiday.objects.filter(
            organization_id=organization_id,
            is_active=True,
            holiday_date__gte=date_from,
            holiday_date__lte=date_to,
        ).values_list("holiday_date", flat=True)
    )


def billable_days(
    *,
    organization_id: Any,
    date_from: date,
    date_to: date,
    branch: Any = None,
    weekdays: set[int] | None = None,
) -> int:
    """
    Oraliqdagi ish kunlari soni — bayramlar chiqarib tashlangan.

    `weekdays` berilsa, filial kalendari o'rniga o'sha kunlar
    hisoblanadi: xodimning o'z grafigi uchun kerak (PLAN 9.1).
    """
    weekdays = working_weekdays(branch) if weekdays is None else set(weekdays)
    closed = _holidays(organization_id, date_from, date_to)

    count = 0
    day = date_from
    while day <= date_to:
        if day.isoweekday() in weekdays and day not in closed:
            count += 1
        day += timedelta(days=1)
    return count


def working_days_in_month(
    *,
    organization_id: Any,
    year: int,
    month: int,
    branch: Any = None,
    weekdays: set[int] | None = None,
) -> int:
    """O'sha oydagi ish kunlari — kun narxining maxraji."""
    last = calendar.monthrange(year, month)[1]
    return billable_days(
        organization_id=organization_id,
        date_from=date(year, month, 1),
        date_to=date(year, month, last),
        branch=branch,
        weekdays=weekdays,
    )


def daily_rate_for(*, child: Any, on_date: date) -> tuple[Decimal, int]:
    """
    Bolaning o'sha oydagi bir kunlik narxi va oyning ish kunlari.

    Manba — imtiyozdan keyingi TO'LIQ oylik (`charges.plan_month`),
    hisob-fakturaning `amount_due` si EMAS (Bosqich 12.1). Oy o'rtasida
    kelgan bolaning fakturasi allaqachon qisqartirilgan, va undan olingan
    stavka uning har bir kunini arzonroq qilib qo'yardi.
    """
    from apps.finance.charges import plan_month

    charge = plan_month(child, on_date.year, on_date.month)
    if charge.price is None:
        raise BusinessRuleViolation(
            gettext("{full_name}: narx ham, hisob-faktura ham yoʻq.").format(
                full_name=child.full_name
            )
        )
    return _money(charge.monthly / Decimal(charge.working_days)), charge.working_days


# --- Qayta hisob turlari (Bosqich 12.3) ---

#: Tizim bilan keladigan turlar — brifdagi Oriental Kinderland qoidasi.
#: Maʼlumotnoma: 1–2 kun ovqat puli, 3+ kun hamma kunlar to'liq stavkada.
DEFAULT_KINDS: tuple[dict[str, Any], ...] = (
    {
        "code": ClaimKind.MEDICAL,
        "name": "Shifokor maʼlumotnomasi",
        "refund_mode": RefundMode.FIXED_PER_DAY,
        "full_rate_from_days": 3,
        "min_days": 1,
        "requires_document": True,
    },
    {
        "code": ClaimKind.PARENTAL,
        "name": "Ota-ona arizasi",
        "refund_mode": RefundMode.FULL_RATE,
        "full_rate_from_days": None,
        "min_days": 1,
        "requires_document": False,
    },
)


def ensure_absence_kinds(organization: Any) -> None:
    """Tizim turlari bor boʻlsin — idempotent, mavjudiga TEGMAYDI."""
    existing = set(AbsenceKind.objects.filter(is_active=True).values_list("code", flat=True))
    for spec in DEFAULT_KINDS:
        if spec["code"] in existing:
            continue
        AbsenceKind.objects.create(organization=organization, **spec)


def kind_for(*, organization: Any, code: str) -> AbsenceKind:
    ensure_absence_kinds(organization)
    kind = AbsenceKind.objects.filter(code=code, is_active=True).first()
    if kind is None:
        raise BusinessRuleViolation(
            gettext("Bunday qayta hisob turi yoʻq: {code}.").format(code=code)
        )
    return kind


def _per_day_amount(kind: AbsenceKind, branch: Any = None) -> Decimal:
    if kind.daily_amount is not None:
        return Decimal(kind.daily_amount)
    from apps.settings_app.services import get_setting

    return Decimal(str(get_setting(key="contracts.daily_meal_fee", branch=branch) or 0))


@transaction.atomic
def create_claim(
    *,
    child: Any,
    kind: str,
    date_from: date,
    date_to: date,
    document_no: str = "",
    note: str = "",
    document_file: Any = None,
    created_by: Any = None,
) -> AbsenceClaim:
    """
    Da'vo yozadi.

    Kesishma BAZADA taqiqlangan (`ck_absence_claim_no_overlap`), lekin
    bu yerda ham oldindan tekshiriladi — foydalanuvchiga tushunarli
    xabar berish uchun. Kafolat emas, xushmuomalalik: kafolat
    cheklovning o'zi, chunki u poygani yutqazmaydi.
    """
    if date_to < date_from:
        raise BusinessRuleViolation(gettext("Tugash sanasi boshlanishdan oldin boʻlolmaydi."))

    absence_kind = kind_for(organization=child.organization, code=kind)
    days = billable_days(
        organization_id=child.organization_id,
        date_from=date_from,
        date_to=date_to,
        branch=child.branch,
    )
    if days < absence_kind.min_days:
        raise BusinessRuleViolation(
            gettext("«{kind}» uchun kamida {n} ish kuni kerak — bu oraliqda {days}.").format(
                kind=absence_kind.name, n=absence_kind.min_days, days=days
            )
        )

    clash = (
        AbsenceClaim.objects.filter(child=child, date_from__lte=date_to, date_to__gte=date_from)
        .exclude(status=ClaimStatus.REJECTED)
        .first()
    )
    if clash is not None:
        raise BusinessRuleViolation(
            gettext("Bu kunlar uchun daʼvo allaqachon bor: {date_from} — {date_to}.").format(
                date_from=clash.date_from, date_to=clash.date_to
            )
        )

    return AbsenceClaim.objects.create(
        organization=child.organization,
        branch=child.branch,
        child=child,
        kind=kind,
        date_from=date_from,
        date_to=date_to,
        document_no=document_no[:60],
        document_file=document_file or "",
        note=note[:255],
        created_by=created_by,
    )


def attach_document(*, claim: AbsenceClaim, uploaded: Any) -> AbsenceClaim:
    """
    Spravka yoki arizani da'voga biriktiradi (PLAN 7.7).

    `pending` da'voga — istalgancha (eski fayl almashtiriladi). Qaror
    chiqqan da'voga — faqat BIRINCHI hujjat (2026-10-14).

    Qaror chiqqandan keyin hujjatni ALMASHTIRISH — pulni harakatga
    keltirgan dalilni orqadan o'zgartirish bo'lardi: tasdiqlovchi bir
    narsani ko'rib imzolagan, papkada esa boshqa narsa turardi. Lekin
    da'vo endi yozilishi bilan tasdiqlanadi (yozgan odam tasdiqlashga
    haqli bo'lsa), qog'oz esa ko'pincha keyin keladi — hujjatsiz
    tasdiqlangan da'voga birinchi faylni qo'shish almashtirish emas.

    Eski fayl o'chiriladi: biriktirishni ikki marta bosish diskda
    egasiz nusxa qoldirardi.
    """
    if claim.status != ClaimStatus.PENDING and claim.document_file:
        raise BusinessRuleViolation(
            gettext("Qaror chiqqan daʼvoning hujjatini almashtirib boʻlmaydi.")
        )
    if claim.status == ClaimStatus.REJECTED:
        raise BusinessRuleViolation(gettext("Qaror chiqqan daʼvoga hujjat biriktirib boʻlmaydi."))
    old = claim.document_file
    if old:
        old.delete(save=False)
    claim.document_file = uploaded
    claim.save(update_fields=["document_file", "updated_at"])
    return claim


def can_approve_now(*, claim: AbsenceClaim) -> bool:
    """
    Daʼvoni HOZIR tasdiqlab boʻladimi — hujjati joyidami?

    Avtomatik tasdiqlash uchun: hujjat talab qilinadigan turda qogʻoz
    keyinroq kelishi mumkin, va shu sabab ariza umuman yozilmay
    qolmasligi kerak (audit, 2026-10-30).
    """
    kind = kind_for(organization=claim.organization, code=claim.kind)
    if not kind.requires_document:
        return True
    return bool(claim.document_no.strip() or claim.document_file)


@transaction.atomic
def approve_claim(*, claim: AbsenceClaim, approved_by: Any = None, note: str = "") -> AbsenceClaim:
    """
    Da'voni tasdiqlaydi va qaytariladigan summani MUZLATADI.

    Qoida da'vo TURIDAN (Bosqich 12.3): to'liq stavka, kuniga qat'iy summa
    yoki qaytarilmaydi; `full_rate_from_days` dan boshlab — hamma kunlar
    to'liq stavkada. Bu 2026-09-30 dagi "chegara yo'q" qarorini almashtiradi
    (brif 2026-10-14, ADR-33).
    """
    if claim.status != ClaimStatus.PENDING:
        raise BusinessRuleViolation(
            gettext("Daʼvo '{status}' holatida — tasdiqlab boʻlmaydi.").format(
                status=claim.get_status_display()
            )
        )
    child = claim.child
    days = billable_days(
        organization_id=claim.organization_id,
        date_from=claim.date_from,
        date_to=claim.date_to,
        branch=claim.branch,
    )
    if days <= 0:
        raise BusinessRuleViolation(
            gettext(
                "Bu oraliqda bogʻcha ishlamagan (dam olish yoki bayram) — qaytariladigan kun yoʻq."
            )
        )

    # Kunlar × stavka natijasi yaxlitlanadi, stavka emas (Bosqich 12.1).
    from apps.finance.charges import credit_for_days

    absence_kind = kind_for(organization=claim.organization, code=claim.kind)
    # Hujjat talab qiladigan turda hujjatsiz tasdiq yoʻq (audit,
    # 2026-10-30). Maʼlumotnoma — pulni qaytarish ASOSI; uning oʻzi
    # boʻlmasa, qaytarishga asos ham yoʻq. Qogʻoz nusxaning raqami ham
    # hujjat: skaner har bogʻchada ham yoʻq.
    if absence_kind.requires_document and not (claim.document_no.strip() or claim.document_file):
        raise BusinessRuleViolation(
            gettext(
                "Bu turdagi daʼvo hujjatsiz tasdiqlanmaydi — "
                "maʼlumotnoma raqamini yozing yoki nusxasini yuklang."
            )
        )
    basis = absence_kind.refund_mode
    if absence_kind.full_rate_from_days and days >= absence_kind.full_rate_from_days:
        basis = RefundMode.FULL_RATE

    if basis == RefundMode.FULL_RATE:
        credit, rate, _ = credit_for_days(child=child, on_date=claim.date_from, days=days)
    elif basis == RefundMode.FIXED_PER_DAY:
        from apps.finance.charges import round_to_step

        rate = _money(_per_day_amount(absence_kind, child.branch))
        credit = round_to_step(rate * days, child.branch)
    else:
        rate, credit = Decimal("0.00"), Decimal("0.00")

    # Chegirma o'sha oyda hisoblanganidan oshib ketmaydi.
    from apps.finance.models import Invoice, InvoiceStatus

    invoice = (
        Invoice.objects.filter(
            child=child,
            period_year=claim.date_from.year,
            period_month=claim.date_from.month,
        )
        .exclude(status=InvoiceStatus.CANCELLED)
        .first()
    )
    if invoice is not None:
        credit = min(credit, invoice.amount_due)

    claim.status = ClaimStatus.APPROVED
    claim.basis = basis
    claim.billable_days = days
    claim.daily_rate = rate
    claim.credit_amount = credit
    claim.approved_by = approved_by
    claim.decided_at = timezone.now()
    claim.decision_note = note[:255]
    claim.save(
        update_fields=[
            "status",
            "billable_days",
            "daily_rate",
            "credit_amount",
            "basis",
            "approved_by",
            "decided_at",
            "decision_note",
            "updated_at",
        ]
    )

    # Shu oyning fakturasi hali to'lanmagan bo'lsa — kredit DARHOL
    # o'sha summadan ayriladi (PLAN 7.7). To'langan bo'lsa yoki kredit
    # qoldiqdan katta bo'lsa, da'vo `approved` bo'lib qoladi va keyingi
    # faktura chiqarilganda minus qator bo'lib tushadi.
    from apps.finance.services import apply_claim_to_open_invoice

    apply_claim_to_open_invoice(claim=claim, created_by=approved_by)
    return claim


@transaction.atomic
def reject_claim(*, claim: AbsenceClaim, approved_by: Any = None, note: str = "") -> AbsenceClaim:
    """Rad etilgan da'vo O'CHIRILMAYDI — nima so'ralgani yozuv bo'lib qoladi."""
    if claim.status != ClaimStatus.PENDING:
        raise BusinessRuleViolation(
            gettext("Daʼvo '{status}' holatida — rad etib boʻlmaydi.").format(
                status=claim.get_status_display()
            )
        )
    claim.status = ClaimStatus.REJECTED
    claim.approved_by = approved_by
    claim.decided_at = timezone.now()
    claim.decision_note = note[:255]
    claim.save(update_fields=["status", "approved_by", "decided_at", "decision_note", "updated_at"])
    return claim


@transaction.atomic
def cancel_claim(*, claim: AbsenceClaim, reason: str, approved_by: Any = None) -> AbsenceClaim:
    """
    Tasdiqlangan daʼvoni bekor qiladi — SABAB bilan (audit, 2026-10-30).

    Ilgari tasdiqlangan daʼvo abadiy qolardi: xato tasdiq ham,
    keyin oʻzgargan kelishuv ham. Daʼvoning oʻzi oʻchirilmaydi —
    u `rad etilgan` boʻladi va sabab yozuvda qoladi.

    Fakturaga TUSHGAN daʼvo bu yerda bekor qilinmaydi: u allaqachon
    pul harakati, va uni faqat tuzatish qatori qaytaradi
    (3-invariant).
    """
    if claim.status == ClaimStatus.APPLIED:
        raise BusinessRuleViolation(
            gettext("Daʼvo hisob-fakturaga tushgan — uni tuzatish qatori bilan qaytaring.")
        )
    if claim.status != ClaimStatus.APPROVED:
        raise BusinessRuleViolation(
            gettext(
                "Faqat tasdiqlangan daʼvo bekor qilinadi — bu daʼvo '{status}' holatida."
            ).format(status=claim.get_status_display())
        )
    if not reason.strip():
        raise BusinessRuleViolation(gettext("Bekor qilish sababini yozing."))

    claim.status = ClaimStatus.REJECTED
    claim.approved_by = approved_by
    claim.decided_at = timezone.now()
    claim.decision_note = gettext("Bekor qilindi: {reason}").format(reason=reason.strip())[:255]
    claim.save(update_fields=["status", "approved_by", "decided_at", "decision_note", "updated_at"])
    return claim


def pending_credits(*, child: Any) -> list[AbsenceClaim]:
    """Tasdiqlangan, lekin hali hisob-fakturaga tushmagan da'volar."""
    return list(
        AbsenceClaim.objects.filter(child=child, status=ClaimStatus.APPROVED).order_by("date_from")
    )
