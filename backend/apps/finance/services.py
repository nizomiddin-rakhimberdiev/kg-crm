"""
Moliya biznes mantiqi (docs/03 §13, §26).

Ledger shartnomasi:
- Har bir pul harakati **avval ledger'ga** yoziladi, keyin keshlar yangilanadi.
- Ledger qatorlari o'zgartirilmaydi — tuzatish qarshi yozuv bilan.
- Hisob-faktura generatsiyasi **idempotent**: ikki marta ishga tushsa ham
  ikkinchi marta hisoblanmaydi.
"""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext

from apps.cash import services as cash
from apps.cash.models import MovementDirection, MovementSource
from apps.children.models import (
    Child,
    Enrollment,
    EnrollmentState,
)
from apps.core.exceptions import BusinessRuleViolation
from apps.finance import balance
from apps.finance.models import (
    ChildLedgerEntry,
    Direction,
    Discount,
    DiscountType,
    EntryType,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentAllocation,
    PaymentMethod,
    SourceType,
)
from apps.finance.selectors import child_monthly_price

__all__ = [
    "child_balance",
    "post_ledger_entry",
    "issue_invoice",
    "cancel_invoice",
    "generate_monthly_invoices",
    "preview_monthly_invoices",
    "recompute_child_balance",
    "applicable_discount",
    "first_month_share",
    "record_opening_debt",
    "apply_claim_to_open_invoice",
    "first_invoice_due_date",
    "record_payment",
    "record_payment_batch",
    "reverse_payment",
    "daily_cash_summary",
    "receipt_for",
    "receipt_number",
    "open_invoices",
    "invoice_allocated",
    "payment_unallocated",
    "child_advance",
    "allocate_payment",
    "release_allocations",
    "apply_advance_to_invoice",
]

CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    """Pulni ikki xonagacha yaxlitlaydi (bank yaxlitlashi emas, HALF_UP)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


# --- Ledger ---


def child_balance(child_id: Any) -> Decimal:
    """
    Bolaning HAQIQIY balansi — ledger'dan hisoblanadi.

    `child.balance` ustuni faqat kesh. Pul bilan bog'liq har qanday qaror
    shu funksiyadan foydalanadi, keshdan emas (D3).
    """
    # Bitta so'rovda ikkita shartli yig'indi — Python'da sikl bilan
    # hisoblash 10 000 qatorli ledger'da sezilarli sekinlashuv berardi.
    totals = ChildLedgerEntry.objects.filter(child_id=child_id).aggregate(
        debit=Sum("amount", filter=Q(direction=Direction.DEBIT)),
        credit=Sum("amount", filter=Q(direction=Direction.CREDIT)),
    )
    return _money((totals["debit"] or Decimal("0")) - (totals["credit"] or Decimal("0")))


def post_ledger_entry(
    *,
    child: Child,
    entry_type: str,
    direction: str,
    amount: Decimal,
    source_type: str,
    source_id: Any = None,
    description: str = "",
    occurred_at: Any = None,
    created_by: Any = None,
) -> ChildLedgerEntry:
    """
    Ledger'ga bitta yozuv qo'shadi.

    Bu ledger'ga yozishning YAGONA yo'li: har bir yozuv shu funksiyadan
    o'tadi, shuning uchun invariantlar bir joyda tekshiriladi.
    """
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Ledger summasi musbat boʻlishi kerak."))

    entry = ChildLedgerEntry.objects.create(
        organization=child.organization,
        branch=child.branch,
        child=child,
        entry_type=entry_type,
        direction=direction,
        amount=_money(amount),
        source_type=source_type,
        source_id=source_id,
        occurred_at=occurred_at or timezone.now(),
        description=description[:255],
        created_by=created_by,
    )
    # Qarz o'zgardi — dashboard keshi eskirdi (yozish nuqtasi YAGONA).
    from apps.reports.services import invalidate_dashboard_on_commit

    invalidate_dashboard_on_commit(organization_id=child.organization_id)
    return entry


def recompute_child_balance(child: Child) -> Decimal:
    """
    Kesh ustunini ledger'dan qayta hisoblaydi.

    Kesh har doim tiklanadigan bo'lishi shart (D3) — bu funksiya
    moslik tekshiruvi vazifasining ham asosi.
    """
    balance = child_balance(child.id)
    Child.objects.filter(pk=child.pk).update(balance=balance)
    return balance


# --- Chegirmalar ---


def applicable_discount(child: Child, on_date: date) -> Discount | None:
    """Berilgan sanada amal qiladigan chegirma (eng so'nggisi)."""
    return (
        Discount.objects.filter(child=child, is_active=True, valid_from__lte=on_date)
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=on_date))
        .order_by("-valid_from")
        .first()
    )


def apply_discount(base: Decimal, discount: Discount | None) -> tuple[Decimal, Decimal]:
    """Qaytaradi: (chegirmadan keyingi summa, chegirma summasi)."""
    if discount is None:
        return _money(base), Decimal("0.00")

    if discount.discount_type == DiscountType.PERCENT:
        reduction = base * discount.value / Decimal("100")
    else:
        reduction = discount.value

    reduction = min(_money(reduction), _money(base))  # manfiy hisob-faktura bo'lmaydi
    return _money(base - reduction), reduction


# --- Hisob-faktura ---


def _next_invoice_number(branch: Any, year: int, month: int) -> str:
    """
    Filial ichida ketma-ket raqam: `MAIN-202607-0001`.

    Raqam `uq_invoice_number` bilan qo'riqlanadi; poyga holatida ikkinchi
    urinish `IntegrityError` beradi va chaqiruvchi qayta uriladi.
    """
    prefix = f"{branch.code}-{year}{month:02d}"
    last = (
        Invoice.objects.filter(branch=branch, number__startswith=prefix)
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    sequence = int(last.rsplit("-", 1)[1]) + 1 if last else 1
    return f"{prefix}-{sequence:04d}"


@transaction.atomic
def apply_claim_to_open_invoice(*, claim: Any, created_by: Any = None) -> bool:
    """
    Tasdiqlangan da'voni SHU OYNING to'lanmagan fakturasiga qo'llaydi.

    Egasining qoidasi (PLAN 7.7): ota-ona bu oy uchun hali to'lamagan
    bo'lsa, qayta hisob shu oyning summasidan ayriladi; to'lagan bo'lsa,
    kredit keyingi oyga o'tadi va keyingi faktura chiqarilganda minus
    qator bo'lib tushadi (avvalgi xatti-harakat).

    `False` qaytsa — hech narsa qilinmadi va da'vo `approved` bo'lib
    qoladi, ya'ni uni `_apply_absence_credits` keyingi fakturada
    oladi.

    **Qoldiqdan katta kredit KEYINGI oyga o'tadi, bo'linmaydi.** Qisman
    qo'llash da'voni ikkiga bo'lishni talab qilardi; bo'linmagan holda
    esa "qoldiq 300 000, kredit 554 000" holatida 254 000 jimgina
    yo'qolardi.

    Hujjat o'zgaradi (minus qator va yangi summa) — bu ataylab: ota-ona
    hali to'lamagan qog'ozdagi raqam bilan tizimdagi raqam bir xil
    bo'lishi kerak. Ledger esa alohida KREDIT yozuvi bilan to'g'rilanadi,
    chunki debet allaqachon to'liq summada yozilgan (3-invariant:
    yozuvlar o'chirilmaydi, qarshi yozuv qo'shiladi).
    """
    from apps.attendance.models_absence import ClaimStatus

    if claim.status != ClaimStatus.APPROVED or claim.credit_amount <= 0:
        return False

    invoice = (
        Invoice.objects.select_for_update()
        .filter(
            child=claim.child,
            period_year=claim.date_from.year,
            period_month=claim.date_from.month,
        )
        .exclude(status=InvoiceStatus.CANCELLED)
        .first()
    )
    if invoice is None:
        return False

    outstanding = _money(invoice.amount_due - invoice.amount_paid)
    if outstanding <= 0 or claim.credit_amount > outstanding:
        # To'langan yoki kredit qoldiqdan katta — keyingi oyga.
        return False

    credit = _money(claim.credit_amount)
    InvoiceLine.objects.create(
        invoice=invoice,
        description=gettext("Kelmagan kunlar uchun qayta hisob: {days} kun × {rate}").format(
            days=claim.billable_days, rate=claim.daily_rate
        )[:255],
        quantity=Decimal("1"),
        unit_amount=-credit,
        line_total=-credit,
    )
    new_due = _money(invoice.amount_due - credit)
    Invoice.objects.filter(pk=invoice.pk).update(amount_due=new_due)
    invoice.amount_due = new_due

    # Ledger: debet allaqachon to'liq summada yozilgan, shuning uchun
    # farq KREDIT yozuvi bilan qaytariladi — aks holda balans qog'ozdagi
    # yangi summadan katta bo'lib qolardi.
    post_ledger_entry(
        child=claim.child,
        entry_type=EntryType.DISCOUNT,
        direction=Direction.CREDIT,
        amount=credit,
        source_type=SourceType.INVOICE,
        source_id=invoice.id,
        description=gettext("Kelmagan kunlar uchun qayta hisob ({number})").format(
            number=invoice.number
        )[:255],
        created_by=created_by,
    )
    _refresh_invoice_payment_state(invoice)

    claim.status = ClaimStatus.APPLIED
    claim.applied_invoice = invoice
    claim.save(update_fields=["status", "applied_invoice", "updated_at"])
    return True


def _apply_absence_credits(
    *, invoice: Invoice, amount_due: Decimal, created_by: Any = None
) -> Decimal:
    """
    Tasdiqlangan da'volarni hisob-fakturaga minus qator qilib qo'shadi.

    Da'vo `applied_invoice` bilan belgilanadi, shuning uchun ikkinchi
    marta qo'llanishi mumkin emas — bu kafolat servisda emas, ma'lumot
    modelida.

    Chegirma hisob-fakturani MANFIY qilmaydi: bog'cha ota-onaga pul
    qarzdor bo'lib qolishi kerak bo'lsa, bu ledger orqali balansda
    ko'rinadi, hisob-faktura esa hujjat bo'lib qoladi.
    """
    from apps.attendance.models_absence import AbsenceClaim, ClaimStatus

    claims = list(
        AbsenceClaim.objects.filter(child=invoice.child, status=ClaimStatus.APPROVED).order_by(
            "date_from"
        )
    )
    if not claims:
        return amount_due

    remaining = amount_due
    for claim in claims:
        if remaining <= 0:
            break
        credit = min(claim.credit_amount, remaining)
        if credit <= 0:
            continue

        InvoiceLine.objects.create(
            invoice=invoice,
            description=gettext("Kelmagan kunlar uchun qayta hisob: {days} kun × {rate}").format(
                days=claim.billable_days, rate=claim.daily_rate
            )[:255],
            quantity=Decimal("1"),
            unit_amount=-credit,
            line_total=-credit,
        )
        remaining = _money(remaining - credit)

        claim.status = ClaimStatus.APPLIED
        claim.applied_invoice = invoice
        claim.save(update_fields=["status", "applied_invoice", "updated_at"])

    if remaining != amount_due:
        Invoice.objects.filter(pk=invoice.pk).update(amount_due=remaining)
        invoice.amount_due = remaining
    return remaining


# --- Birinchi oy: proporsiya va muddat (PLAN 1.3, Q2 va Q3) ---

SOM = Decimal("1")

#: `finance.first_month_mode` qiymatlari.
FIRST_MONTH_FULL = "full"
FIRST_MONTH_PRORATED = "prorated"
FIRST_MONTH_NEXT = "next_month"


def _setting(key: str, branch: Any = None) -> Any:
    from apps.settings_app.services import get_setting

    return get_setting(key=key, branch=branch)


def _whole_som(value: Decimal) -> Decimal:
    """
    Butun so'mgacha yaxlitlash (Q2).

    Tiyin ishlatilmaydi: kvitansiyada "68 181,82 soʻm" degan raqam
    ota-onaga hech narsa demaydi va kassada shunday pul yo'q.
    """
    return value.quantize(SOM, rounding=ROUND_HALF_UP)


def _is_first_period(child: Child, period_year: int, period_month: int) -> bool:
    """
    Bu davr bolaning BIRINCHI hisob-faktura oyimi?

    Ikki shart: qabul sanasi shu oyga tushadi va undan oldin hech qanday
    hisob-faktura yozilmagan. Ikkinchi shart kerak — bola chiqib ketib,
    keyin qaytib kelgan bo'lishi mumkin, va o'shanda ikkinchi marta
    proporsional hisoblash noto'g'ri bo'lardi.
    """
    enrolled = child.enrolled_on
    if enrolled is None:
        return False
    if (enrolled.year, enrolled.month) != (period_year, period_month):
        return False
    return not (
        Invoice.objects.filter(child=child).exclude(status=InvoiceStatus.CANCELLED).exists()
    )


@transaction.atomic
def record_opening_debt(
    *, child: Child, amount: Decimal, created_by: Any = None
) -> ChildLedgerEntry | None:
    """
    Eski qarzni ledger'ga kiritadi — import uchun (PLAN 7.8).

    Bog'cha tizimga o'tganda bolalarning bir qismi qarz bilan keladi.
    U qarz hisob-faktura emas (hujjat yo'q, davri ham noma'lum), lekin
    PUL — shuning uchun u ledger'ga `adjustment` debeti bo'lib tushadi
    va bola qarzdorlar ro'yxatida darhol ko'rinadi (4-invariant).

    **Faqat toza ledger'da.** Bitta yozuvi bor bolaga boshlang'ich qarz
    qo'yib bo'lmaydi: import ikki marta ishga tushsa yoki xodim qo'lda
    takrorlasa, qarz jimgina ikkilanardi.
    """
    if amount is None or amount <= 0:
        return None
    if ChildLedgerEntry.objects.filter(child=child).exists():
        raise BusinessRuleViolation(
            gettext("Bolada allaqachon moliyaviy yozuv bor — boshlangʻich qarz qoʻshilmaydi.")
        )
    return post_ledger_entry(
        child=child,
        entry_type=EntryType.ADJUSTMENT,
        direction=Direction.DEBIT,
        amount=amount,
        source_type=SourceType.MANUAL,
        description=gettext("Tizimga oʻtishdagi eski qarz"),
        created_by=created_by,
    )


def first_month_share(
    *, child: Child, period_year: int, period_month: int
) -> tuple[int, int] | None:
    """
    Birinchi oy uchun (bolaning kunlari, oyning ish kunlari).

    `None` — bu oy proporsional hisoblanmaydi (birinchi oy emas yoki
    sozlama `full`).
    """
    from apps.attendance.services_absence import billable_days, working_days_in_month

    if child.is_existing_client:
        # Tizimga o'tishdan oldin ham qatnab yurgan bola (PLAN 7.8):
        # uning uchun bu oy "birinchi oy" emas, to'liq oy.
        return None
    if not _is_first_period(child, period_year, period_month):
        return None
    if str(_setting("finance.first_month_mode", child.branch)) != FIRST_MONTH_PRORATED:
        return None

    last_day = calendar.monthrange(period_year, period_month)[1]
    assert child.enrolled_on is not None  # `_is_first_period` kafolati
    attended = billable_days(
        organization_id=child.organization_id,
        date_from=child.enrolled_on,
        date_to=date(period_year, period_month, last_day),
        branch=child.branch,
    )
    total = working_days_in_month(
        organization_id=child.organization_id,
        year=period_year,
        month=period_month,
        branch=child.branch,
    )
    return attended, total


def first_invoice_due_date(*, child: Child, period_year: int, period_month: int) -> date:
    """
    Hisob-faktura muddati (Q3): `max(to'lov kuni, qabul + imtiyoz kunlari)`.

    Ilgari muddat har doim oyning 10-kuni edi. Natijada 30-sentabrda
    qabul qilingan bolaning fakturasi yaratilgan kuniyoq 20 kun
    kechikkan bo'lib chiqardi — va u darhol qarzdorlar ro'yxatiga,
    eslatma SMS navbatiga va brifingga tushardi.
    """
    last_day = calendar.monthrange(period_year, period_month)[1]
    payment_day = int(_setting("finance.due_day", child.branch) or 10)
    due = date(period_year, period_month, min(max(payment_day, 1), last_day))

    if _is_first_period(child, period_year, period_month):
        grace = int(_setting("finance.first_invoice_grace_days", child.branch) or 0)
        assert child.enrolled_on is not None
        due = max(due, child.enrolled_on + timedelta(days=grace))
    return due


@transaction.atomic
def issue_invoice(
    *,
    child: Child,
    period_year: int,
    period_month: int,
    issued_date: date | None = None,
    due_date: date | None = None,
    created_by: Any = None,
) -> Invoice:
    """
    Bolaga bir davr uchun hisob-faktura chiqaradi va ledger'ga debet yozadi.

    Idempotentlik `uq_invoice_child_period` qisman indeksi bilan bazada
    kafolatlanadi — ilova qatlamidagi tekshiruv poyga holatida yetarli
    emas (docs/03 §26).
    """
    price = child_monthly_price(child)
    if price is None:
        raise BusinessRuleViolation(
            gettext(
                "{full_name}: narx belgilanmagan (tarif ham, individual narx ham yoʻq) — "
                "hisob-faktura chiqarib boʻlmaydi."
            ).format(full_name=child.full_name)
        )

    existing = (
        Invoice.objects.filter(child=child, period_year=period_year, period_month=period_month)
        .exclude(status=InvoiceStatus.CANCELLED)
        .first()
    )
    if existing:
        return existing

    # Birinchi oy sozlamasi "keyingi oydan" bo'lsa, hujjat yozilmaydi
    # (Q2). Oy o'rtasida kelgan bola birinchi to'lovini keyingi oy
    # boshida to'liq qiladi.
    if (
        _is_first_period(child, period_year, period_month)
        and str(_setting("finance.first_month_mode", child.branch)) == FIRST_MONTH_NEXT
    ):
        raise BusinessRuleViolation(
            gettext(
                "{full_name}: sozlamaga koʻra birinchi hisob-faktura keyingi oydan yoziladi."
            ).format(full_name=child.full_name)
        )

    # Hujjat sanasi qabul sanasidan oldin bo'la olmaydi: 30-sentabrda
    # kelgan bolaning fakturasi 1-sentabrdan boshlansa, u kelmagan
    # kunlari uchun ham to'lagan bo'lardi.
    issued = issued_date or date(period_year, period_month, 1)
    if child.enrolled_on is not None and _is_first_period(child, period_year, period_month):
        issued = max(issued, child.enrolled_on)
    if due_date is None:
        due_date = first_invoice_due_date(
            child=child, period_year=period_year, period_month=period_month
        )
    if due_date < issued:
        due_date = issued

    discount = applicable_discount(child, issued)
    amount_due, discount_amount = apply_discount(price.amount, discount)

    # Proporsional birinchi oy (Q2): faqat bolaning ish kunlari.
    share = first_month_share(child=child, period_year=period_year, period_month=period_month)
    prorated_note = ""
    if share is not None:
        attended, total = share
        if total > 0 and attended < total:
            full_amount = amount_due
            amount_due = _whole_som(full_amount * attended / total)
            prorated_note = gettext("{month}, {total} ish kunidan {attended} kun").format(
                month=f"{period_month:02d}/{period_year}", total=total, attended=attended
            )

    try:
        invoice = Invoice.objects.create(
            organization=child.organization,
            branch=child.branch,
            number=_next_invoice_number(child.branch, period_year, period_month),
            child=child,
            # Individual narxda `None` — hujjat qaysi tarifdan emasligini
            # ochiq ko'rsatadi; summa `amount_due` va qatorda nusxalangan.
            tariff=price.tariff,
            period_year=period_year,
            period_month=period_month,
            amount_due=amount_due,
            status=InvoiceStatus.ISSUED,
            issued_date=issued,
            due_date=due_date,
        )
    except IntegrityError as exc:
        # Parallel generatsiya bir vaqtda bir bolaga urindi — bazadagi
        # qisman indeks ushladi. Mavjudini qaytaramiz: bu xato emas,
        # idempotentlikning ishlagani.
        existing = (
            Invoice.objects.filter(child=child, period_year=period_year, period_month=period_month)
            .exclude(status=InvoiceStatus.CANCELLED)
            .first()
        )
        if existing:
            return existing
        raise BusinessRuleViolation(gettext("Hisob-fakturani yaratib boʻlmadi.")) from exc

    # Satr izohida proporsiya KO'RINADI. "68 182 soʻm" degan raqam
    # sababsiz tushunarsiz; "22 ish kunidan 1 kun" esa ota-onaga ham,
    # mudiraga ham bir qarashda hamma narsani aytadi.
    InvoiceLine.objects.create(
        invoice=invoice,
        # Narx manbai — tarif YOKI individual narx (`child_monthly_price`);
        # proporsiya bo'lsa, satr summasi va izohi shuni aytadi.
        description=(
            f"{price.label} — {prorated_note}"
            if prorated_note
            else f"{price.label} — {period_month:02d}/{period_year}"
        )[:255],
        quantity=Decimal("1"),
        unit_amount=amount_due if prorated_note else price.amount,
        line_total=amount_due if prorated_note else price.amount,
    )
    if discount_amount > 0 and discount is not None:
        InvoiceLine.objects.create(
            invoice=invoice,
            description=f"Chegirma: {discount.reason or discount}",
            quantity=Decimal("1"),
            unit_amount=-discount_amount,
            line_total=-discount_amount,
        )

    # Kelmagan kunlar uchun qaytarish — MINUS QATOR (ADR-19).
    #
    # Nega o'tgan oyning hisob-fakturasini qayta hisoblash emas:
    # chiqarilgan hujjat ledger yozuvini yaratgan, uni tahrirlash
    # hujjat bilan ledgerni ajratib yuborardi (D3). Minus qator esa
    # ota-ona qo'lidagi qog'oz bilan balansni bir xil raqamda
    # ushlab turadi.
    amount_due = _apply_absence_credits(
        invoice=invoice, amount_due=amount_due, created_by=created_by
    )

    if amount_due > 0:
        # Ledger — hujjatdan KEYIN, lekin bitta tranzaksiyada.
        # Hisob-faktura bor, ledger yozuvi yo'q holat balansning jimgina
        # noto'g'ri bo'lishi demak; tranzaksiya buni imkonsiz qiladi.
        post_ledger_entry(
            child=child,
            entry_type=EntryType.CHARGE,
            direction=Direction.DEBIT,
            amount=amount_due,
            source_type=SourceType.INVOICE,
            source_id=invoice.id,
            description=f"Hisob-faktura {invoice.number}",
            occurred_at=timezone.now(),
            created_by=created_by,
        )
    else:
        # To'liq chegirma: to'lanadigan summa yo'q, demak pul harakati
        # ham yo'q. Nol summali ledger yozuvi `amount > 0` invariantini
        # bo'shashtirishni talab qilardi — u esa haqiqiy xatolarni
        # ushlaydigan kuchli qoida. Hujjat esa qoladi: u "bu bola bu oyda
        # hech narsa to'lamaydi" faktini isbotlaydi.
        invoice.status = InvoiceStatus.PAID
        invoice.save(update_fields=["status", "updated_at"])

    # Mavjud avansni darhol qo'llash (Q1).
    #
    # Audit ssenariysi: bola yaratildi → 200 000 naqd qabul qilindi →
    # "Hisob-faktura chiqarish". Ilgari hujjat "To'lanmagan" bo'lib
    # tug'ilardi va kassirga bolaning puli kassada turgani ko'rinmasdi.
    if invoice.status != InvoiceStatus.PAID:
        apply_advance_to_invoice(invoice=invoice, created_by=created_by)
        invoice.refresh_from_db()

    recompute_child_balance(child)
    return invoice


@transaction.atomic
def cancel_invoice(*, invoice: Invoice, reason: str = "", created_by: Any = None) -> Invoice:
    """
    Hisob-fakturani bekor qiladi — QARSHI yozuv bilan.

    Ledger'dagi debet o'chirilmaydi: uning o'rniga teng kredit qo'shiladi.
    Shunda "nima bo'ldi?" degan savolga jurnal javob beradi (D3).
    """
    if invoice.status == InvoiceStatus.CANCELLED:
        return invoice
    if invoice.amount_paid > 0:
        raise BusinessRuleViolation(
            gettext(
                "Toʻlov qilingan hisob-fakturani bekor qilib boʻlmaydi — avval toʻlovni qaytaring."
            )
        )

    invoice.status = InvoiceStatus.CANCELLED
    invoice.save(update_fields=["status", "updated_at"])

    post_ledger_entry(
        child=invoice.child,
        entry_type=EntryType.ADJUSTMENT,
        direction=Direction.CREDIT,
        amount=invoice.amount_due,
        source_type=SourceType.INVOICE,
        source_id=invoice.id,
        description=f"Bekor qilindi {invoice.number}: {reason}"[:255],
        created_by=created_by,
    )
    recompute_child_balance(invoice.child)
    return invoice


# --- Oylik generatsiya ---


@dataclass
class BillingRunResult:
    period: str
    created: int = 0
    skipped_existing: int = 0
    skipped_no_tariff: list[str] = field(default_factory=list)
    skipped_next_month: list[str] = field(default_factory=list)
    total_amount: Decimal = Decimal("0.00")

    def as_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "created": self.created,
            "skipped_existing": self.skipped_existing,
            "skipped_no_tariff": self.skipped_no_tariff,
            "skipped_next_month": self.skipped_next_month,
            "total_amount": str(self.total_amount),
        }


@dataclass
class BillingPreviewRow:
    """Preview'dagi bitta bola."""

    child_id: str
    full_name: str
    group_name: str
    amount: Decimal
    note: str
    advance: Decimal

    def as_dict(self) -> dict[str, Any]:
        return {
            "child_id": self.child_id,
            "full_name": self.full_name,
            "group_name": self.group_name,
            "amount": f"{self.amount:.2f}",
            "note": self.note,
            "advance": f"{self.advance:.2f}",
        }


@dataclass
class BillingPreview:
    """
    Generatsiya nima qilishini OLDINDAN aytadi (PLAN 1.4).

    Auditda "Hisob-faktura chiqarish" tugmasi hech narsa so'ramasdan
    ishlab ketardi. 200 bolali bog'chada bu 200 ta moliyaviy hujjat —
    va ularni qaytarish uchun har birini alohida bekor qilish kerak.
    Shuning uchun endi avval ro'yxat ko'rsatiladi.
    """

    period: str
    will_create: int = 0
    skipped_existing: int = 0
    skipped_no_tariff: list[str] = field(default_factory=list)
    skipped_next_month: list[str] = field(default_factory=list)
    total_amount: Decimal = Decimal("0.00")
    rows: list[BillingPreviewRow] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "will_create": self.will_create,
            "skipped_existing": self.skipped_existing,
            "skipped_no_tariff": self.skipped_no_tariff,
            "skipped_next_month": self.skipped_next_month,
            "total_amount": f"{self.total_amount:.2f}",
            "rows": [row.as_dict() for row in self.rows],
        }


def _billing_candidates(*, period_year: int, period_month: int, branch: Any = None) -> list[Child]:
    """
    Generatsiyaga tushadigan bolalar — preview va ishning o'zi uchun BIR XIL.

    Ikki qatlam:
      * baza filtri — arxivlanmagan, faol yozuvlar (Q6);
      * `children.is_billable_for()` — holat va o'zgarish SANASI (Q5).

    Ikkinchisi kerak, chunki oyning 20-kunida ketgan bolaga o'sha oy
    uchun hujjat yozilishi kerak: u oyning bir qismida bog'chada
    bo'lgan. Faqat `enrollment_status` ga qarash buni o'tkazib
    yuborardi — va qoida ikki joyda ikki xil bo'lib qolardi.
    """
    from apps.children.services import is_billable_for

    children = Child.objects.filter(
        is_active=True,
        archived_at__isnull=True,
    ).select_related("tariff", "branch", "organization")
    if branch is not None:
        children = children.filter(branch=branch)
    return [
        child
        for child in children
        if is_billable_for(child, period_year=period_year, period_month=period_month)
    ]


def preview_monthly_invoices(
    *,
    organization: Any,
    branch: Any = None,
    period_year: int,
    period_month: int,
) -> BillingPreview:
    """
    Generatsiyani HISOBLAYDI, lekin hech narsa yozmaydi (PLAN 1.4).

    Nomzodlar ro'yxati `generate_monthly_invoices` bilan BITTA
    funksiyadan keladi (`_billing_candidates`) — aks holda preview
    "12 ta bola" deb, ish esa 14 tasini yaratib qo'yishi mumkin edi va
    bunday farq eng yomon turdagi xato bo'lardi: u ishonchni oshirib,
    keyin sindiradi.
    """
    if not 1 <= period_month <= 12:
        raise BusinessRuleViolation(gettext("Oy 1–12 oraligʻida boʻlishi kerak."))

    preview = BillingPreview(period=f"{period_year}-{period_month:02d}")

    for child in _billing_candidates(
        period_year=period_year, period_month=period_month, branch=branch
    ):
        # Narx — `issue_invoice` bilan BIR XIL manbadan (tarif yoki
        # individual narx). Aks holda preview individual narxli bolani
        # "tarifsiz" deb ko'rsatib, generatsiya esa unga faktura yozardi.
        price = child_monthly_price(child)
        if price is None:
            preview.skipped_no_tariff.append(child.full_name)
            continue

        already = (
            Invoice.objects.filter(child=child, period_year=period_year, period_month=period_month)
            .exclude(status=InvoiceStatus.CANCELLED)
            .exists()
        )
        if already:
            preview.skipped_existing += 1
            continue

        if (
            _is_first_period(child, period_year, period_month)
            and str(_setting("finance.first_month_mode", child.branch)) == FIRST_MONTH_NEXT
        ):
            preview.skipped_next_month.append(child.full_name)
            continue

        issued = date(period_year, period_month, 1)
        if child.enrolled_on is not None and _is_first_period(child, period_year, period_month):
            issued = max(issued, child.enrolled_on)
        amount, _discount = apply_discount(price.amount, applicable_discount(child, issued))

        note = ""
        share = first_month_share(child=child, period_year=period_year, period_month=period_month)
        if share is not None:
            attended, total = share
            if total > 0 and attended < total:
                amount = _whole_som(amount * attended / total)
                note = gettext("{month}, {total} ish kunidan {attended} kun").format(
                    month=f"{period_month:02d}/{period_year}", total=total, attended=attended
                )

        group = (
            Enrollment.objects.filter(child=child, status=EnrollmentState.ACTIVE)
            .order_by("-start_date")
            .values_list("group__name", flat=True)
            .first()
        )
        preview.rows.append(
            BillingPreviewRow(
                child_id=str(child.id),
                full_name=child.full_name,
                group_name=group or "",
                amount=amount,
                note=note,
                # Avans bo'lsa, faktura yozilishi bilan yeyiladi —
                # mudira buni tasdiqlashdan oldin ko'rishi kerak.
                advance=child_advance(child),
            )
        )
        preview.will_create += 1
        preview.total_amount += amount

    preview.rows.sort(key=lambda row: row.full_name)
    return preview


def generate_monthly_invoices(
    *,
    organization: Any,
    branch: Any = None,
    period_year: int,
    period_month: int,
    created_by: Any = None,
) -> BillingRunResult:
    """
    Davr uchun barcha faol bolalarga hisob-faktura chiqaradi.

    **Idempotent**: qayta ishga tushirilsa mavjudlari o'tkazib yuboriladi.
    Har bir bola ALOHIDA tranzaksiyada — bitta bolaning xatosi (masalan
    tarif yo'q) butun ishni to'xtatmasligi kerak, aks holda 200 bolali
    bog'chada bitta nosozlik oyni bloklab qo'yardi.
    """
    if not 1 <= period_month <= 12:
        raise BusinessRuleViolation(gettext("Oy 1–12 oraligʻida boʻlishi kerak."))

    result = BillingRunResult(period=f"{period_year}-{period_month:02d}")

    for child in _billing_candidates(
        period_year=period_year, period_month=period_month, branch=branch
    ):
        # Narxi yo'q bola (tarif ham, individual narx ham yo'q) — o'tkaziladi.
        # Maydon nomi API muvofiqligi uchun `skipped_no_tariff` bo'lib qoldi.
        if child.tariff_id is None and child.monthly_fee is None:
            result.skipped_no_tariff.append(child.full_name)
            continue

        already = (
            Invoice.objects.filter(child=child, period_year=period_year, period_month=period_month)
            .exclude(status=InvoiceStatus.CANCELLED)
            .exists()
        )
        if already:
            result.skipped_existing += 1
            continue

        # Yuqoridagi tekshiruv "tekshir-keyin-yoz" oynasini qoldiradi:
        # ikkinchi ishga tushish (yoki `acks_late` bilan qayta
        # yetkazilgan vazifa) bir vaqtda kelsa, ikkalasi ham "yo'q" deb
        # ko'radi. Oxirgi so'z `uq_invoice_child_period` da — va u
        # ikkinchisini `IntegrityError` bilan to'xtatadi.
        #
        # Avval bu istisno TUTILMASDI va butun ishni yiqitardi: 200
        # bolali bog'chada 3-bolada yuz bergan to'qnashuv qolgan 197
        # tasini hisob-fakturasiz qoldirardi. Holbuki to'qnashuvning
        # ma'nosi "bu bola uchun allaqachon bor" — ya'ni aynan
        # o'tkazib yuborish kerak bo'lgan holat.
        # Sozlama "keyingi oydan" bo'lsa, bu bola bu oyda o'tkazib
        # yuboriladi — bitta bolaning qoidasi butun ishni to'xtatmaydi.
        if (
            _is_first_period(child, period_year, period_month)
            and str(_setting("finance.first_month_mode", child.branch)) == FIRST_MONTH_NEXT
        ):
            result.skipped_next_month.append(child.full_name)
            continue

        try:
            with transaction.atomic():
                invoice = issue_invoice(
                    child=child,
                    period_year=period_year,
                    period_month=period_month,
                    created_by=created_by,
                )
        except IntegrityError:
            result.skipped_existing += 1
            continue

        result.created += 1
        result.total_amount += invoice.amount_due

    return result


def mark_overdue_invoices(*, organization_id: Any, today: date | None = None) -> int:
    """Muddati o'tgan hisob-fakturalarni belgilaydi (rejalashtirilgan vazifa)."""
    today = today or timezone.localdate()
    return Invoice.objects.filter(
        organization_id=organization_id,
        status__in=[InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID],
        due_date__lt=today,
    ).update(status=InvoiceStatus.OVERDUE)


# --- To'lovlar ---


@transaction.atomic
def record_payment(
    *,
    child: Child,
    amount: Decimal,
    method: str,
    invoice: Invoice | None = None,
    reference: str = "",
    paid_at: Any = None,
    received_by: Any = None,
    idempotency_key: str = "",
    batch_id: Any = None,
) -> Payment:
    """
    To'lovni qayd etadi — BITTA tranzaksiyada (docs/03 §13.5, §26).

    Tartib muhim:
      1. Hisob-faktura qatorini QULFLAYMIZ (`SELECT ... FOR UPDATE`)
      2. Ortiqcha to'lov emasligini qayta tekshiramiz
      3. To'lov qatorini yozamiz
      4. Ledger'ga KREDIT yozamiz
      5. `invoice.amount_paid` va statusni yangilaymiz
      6. `child.balance` keshini ledger'dan qayta hisoblaymiz

    Qulf shart: ikkita kassir bir vaqtda bir hisob-fakturaga to'lov
    kiritsa, qulfsiz ikkalasi ham "qoldiq yetarli" deb ko'radi va
    hisob-faktura ortiqcha to'langan bo'lib qoladi. `CHECK` buni
    ushlay olmaydi — u boshqa tranzaksiyani ko'rmaydi.
    """
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Toʻlov summasi musbat boʻlishi kerak."))

    amount = _money(amount)

    # Takroriy yuborish (P1-003): shu kalit bilan to'lov allaqachon
    # yozilgan bo'lsa, YANGISINI yaratmaymiz — mavjudini qaytaramiz.
    # Chaqiruvchi uchun natija bir xil ko'rinadi, ya'ni "ikki marta
    # bosdim" holati jimgina va zararsiz hal bo'ladi.
    if idempotency_key:
        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing

    if invoice is not None:
        if invoice.child_id != child.id:
            raise BusinessRuleViolation(gettext("Hisob-faktura boshqa bolaga tegishli."))
        if invoice.status == InvoiceStatus.CANCELLED:
            raise BusinessRuleViolation(
                gettext("Bekor qilingan hisob-fakturaga toʻlov qabul qilinmaydi.")
            )
        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
    else:
        locked = None

    # Yuqoridagi tekshiruv "tekshir-keyin-yoz" oynasini qoldiradi: ikkita
    # so'rov bir vaqtda kelsa, ikkalasi ham "mavjud emas" deb ko'radi.
    # Shuning uchun oxirgi so'z BAZADA — `uq_payment_idempotency` qisman
    # unikal indeksi. Ikkinchi `INSERT` shu yerda to'xtaydi va biz
    # birinchisining natijasini qaytaramiz.
    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                organization=child.organization,
                branch=child.branch,
                invoice=locked,
                child=child,
                amount=amount,
                method=method,
                reference=reference[:100],
                paid_at=paid_at or timezone.now(),
                received_by=received_by,
                idempotency_key=idempotency_key[:64],
                batch_id=batch_id,
            )
    except IntegrityError:
        if not idempotency_key:
            raise
        winner = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if winner is None:  # pragma: no cover — boshqa cheklov buzilgan
            raise
        return winner

    post_ledger_entry(
        child=child,
        entry_type=EntryType.PAYMENT,
        direction=Direction.CREDIT,
        amount=amount,
        source_type=SourceType.PAYMENT,
        source_id=payment.id,
        description=f"To'lov {method}" + (f" — {locked.number}" if locked else ""),
        occurred_at=payment.paid_at,
        created_by=received_by,
    )

    # Kassa jurnali (ADR-17): pul QAYSI qopga tushgani shu yerda qoladi.
    # Bu ATAYLAB `post_ledger_entry` bilan bitta tranzaksiyada: ikkalasi
    # bir savolga emas, ikki savolga javob beradi — "oila qancha qarz?"
    # va "qaysi qopda qancha pul bor?" — lekin bitta hodisadan keladi va
    # biri yozilib, ikkinchisi yozilmay qolishi mumkin emas.
    cash.post_movement(
        account=cash.account_for_method(branch=payment.branch, method=method),
        direction=MovementDirection.IN,
        amount=amount,
        source_type=MovementSource.PAYMENT,
        source_id=payment.id,
        description=(f"{child.full_name} — {locked.number}" if locked else child.full_name)[:255],
        occurred_at=payment.paid_at,
        created_by=received_by,
    )

    # Taqsimot (Q1): tanlangan hujjat → FIFO → qoldiq avans. Bu ATAYLAB
    # ledger yozuvidan keyin: ledger pulning KELGANINI yozadi va u
    # taqsimotdan mustaqil, taqsimot esa o'sha pul qaysi hujjatni
    # yopganini aytadi. Ikkisi bitta tranzaksiyada.
    allocate_payment(payment=payment, prefer_invoice=locked)

    recompute_child_balance(child)

    # Ota-onaga kvitansiya SMS'i. Bu ATAYLAB tranzaksiyaning oxirida va
    # xatosi yutiladi: pul allaqachon qabul qilingan va yozilgan, uni
    # SMS shlyuzi ishlamagani uchun bekor qilish mumkin emas (P8).
    from apps.notifications.services import notify_payment_received

    notify_payment_received(payment=payment)
    return payment


# --- Taqsimot: qaysi pul qaysi hisob-fakturani yopadi (PLAN 1.2, Q1) ---

#: Ochiq hisob-faktura — pul hali to'liq qoplamagan hujjat.
OPEN_INVOICE_STATUSES = (
    InvoiceStatus.ISSUED,
    InvoiceStatus.PARTIALLY_PAID,
    InvoiceStatus.OVERDUE,
)


def open_invoices(child: Child) -> Any:
    """
    Bolaning ochiq hisob-fakturalari — ENG ESKISIDAN (FIFO, Q1).

    Tartib `due_date` bo'yicha: ota-ona uchun "eng eski qarz" degani
    muddati birinchi kelgan hujjat, u qaysi oyda yozilganidan qat'i
    nazar. Teng muddatlarda davr, keyin raqam — natija BARQAROR
    bo'lishi kerak, aks holda bir xil to'lov ikki marta ishga
    tushirilganda boshqacha taqsimlanardi.
    """
    return Invoice.objects.filter(child=child, status__in=OPEN_INVOICE_STATUSES).order_by(
        "due_date", "period_year", "period_month", "number"
    )


def invoice_allocated(invoice: Invoice) -> Decimal:
    """Hisob-fakturaga taqsimlangan pul — faol qatorlar yig'indisi."""
    total = PaymentAllocation.objects.filter(invoice=invoice, released_at__isnull=True).aggregate(
        total=Sum("amount")
    )["total"]
    return _money(total or Decimal("0"))


def payment_unallocated(payment: Payment) -> Decimal:
    """To'lovning hali hech qaysi hujjatga biriktirilmagan qismi (avans)."""
    if payment.is_reversed:
        return Decimal("0.00")
    allocated = PaymentAllocation.objects.filter(
        payment=payment, released_at__isnull=True
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return _money(payment.amount - allocated)


def child_advance(child: Child) -> Decimal:
    """
    Bolaning avans qoldig'i — taqsimlanmagan pul.

    Ledger balansidan ALOHIDA hisoblanadi va shunday bo'lishi kerak:
    balans "oila qancha qarz" degan savolga javob beradi, avans esa
    "qo'limizda uning qancha puli bor" degan savolga. Ikkisi bir xil
    raqam emas — bolada bir vaqtning o'zida yopilmagan faktura ham,
    taqsimlanmagan pul ham bo'lishi mumkin.
    """
    payments = Payment.objects.filter(child=child, reversed_at__isnull=True)
    paid = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    allocated = PaymentAllocation.objects.filter(
        payment__child=child, released_at__isnull=True
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    return _money(paid - allocated)


def allocate_payment(
    *, payment: Payment, prefer_invoice: Invoice | None = None
) -> list[PaymentAllocation]:
    """
    To'lovning taqsimlanmagan qismini ochiq hujjatlarga tarqatadi (Q1).

    Tartib: kassir tanlagan hisob-faktura (bo'lsa) → qolganlari FIFO →
    qoldiq avans bo'lib qoladi.

    **Ortiqcha to'lov endi XATO emas.** Ilgari kassir 3 000 000 keltirgan
    ota-onaga sentabr fakturasini tanlasa, tizim "Ortiqcha to'lov" deb
    rad etardi va kassir summani ikkiga bo'lib, ikki marta kiritishga
    majbur bo'lardi. Endi tanlangan hujjat birinchi yopiladi, ortig'i
    keyingisiga o'tadi, oxirgi qoldiq esa avans bo'lib turadi — Q1
    aynan shuni talab qiladi.

    Har bir hujjat qatori QULFLANADI: ikki kassir bir vaqtda to'lov
    kiritsa, qulfsiz ikkalasi ham "qoldiq yetarli" deb ko'rardi va
    `amount_paid <= amount_due` invarianti buzilardi.
    """
    remaining = payment_unallocated(payment)
    if remaining <= 0:
        return []

    queue: list[Invoice] = []
    if prefer_invoice is not None and prefer_invoice.status in OPEN_INVOICE_STATUSES:
        queue.append(prefer_invoice)
    queue.extend(
        invoice
        for invoice in open_invoices(payment.child)
        if prefer_invoice is None or invoice.pk != prefer_invoice.pk
    )

    created: list[PaymentAllocation] = []
    for invoice in queue:
        if remaining <= 0:
            break
        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
        outstanding = _money(locked.amount_due - invoice_allocated(locked))
        if outstanding <= 0:
            continue

        share = min(remaining, outstanding)
        created.append(
            PaymentAllocation.objects.create(
                organization=payment.organization,
                branch=payment.branch,
                payment=payment,
                invoice=locked,
                amount=share,
                allocated_at=payment.paid_at,
            )
        )
        remaining -= share
        _refresh_invoice_payment_state(locked)

    return created


def release_allocations(
    *, payment: Payment | None = None, invoice: Invoice | None = None, reason: str = ""
) -> list[Invoice]:
    """
    Taqsimotni bo'shatadi — pul yana avansga aylanadi.

    Ikki holatda chaqiriladi: to'lov qaytarilganda va hisob-faktura
    bekor qilinganda. Qator o'chirilmaydi, `released_at` bilan
    belgilanadi: "bu pul bir vaqtlar shu hujjatni yopgan edi" degan
    fakt hisobotda va nizoda kerak bo'ladi.

    Qaytaradi: `amount_paid` i qayta hisoblangan hujjatlar.
    """
    queryset = PaymentAllocation.objects.filter(released_at__isnull=True)
    if payment is not None:
        queryset = queryset.filter(payment=payment)
    if invoice is not None:
        queryset = queryset.filter(invoice=invoice)

    touched = {
        allocation.invoice_id: allocation.invoice
        for allocation in queryset.select_related("invoice")
    }
    queryset.update(
        released_at=timezone.now(), release_reason=reason[:255], updated_at=timezone.now()
    )

    for affected in touched.values():
        _refresh_invoice_payment_state(affected)
    return list(touched.values())


def apply_advance_to_invoice(*, invoice: Invoice, created_by: Any = None) -> Decimal:
    """
    Yangi hisob-fakturaga bolaning mavjud avansini qo'llaydi (Q1).

    Audit ssenariysi: bola yaratildi → 200 000 naqd qabul qilindi →
    hisob-faktura chiqarildi. Ilgari faktura "To'lanmagan" bo'lib
    tug'ilardi, holbuki pul allaqachon kassada edi.

    Qaytaradi: qo'llangan summa.
    """
    applied = Decimal("0.00")
    payments = (
        Payment.objects.filter(child=invoice.child, reversed_at__isnull=True)
        .order_by("paid_at", "created_at")
        .select_for_update()
    )
    for payment in payments:
        outstanding = _money(invoice.amount_due - invoice_allocated(invoice))
        if outstanding <= 0:
            break
        spare = payment_unallocated(payment)
        if spare <= 0:
            continue
        share = min(spare, outstanding)
        PaymentAllocation.objects.create(
            organization=invoice.organization,
            branch=invoice.branch,
            payment=payment,
            invoice=invoice,
            amount=share,
            allocated_at=timezone.now(),
        )
        applied += share

    if applied > 0:
        _refresh_invoice_payment_state(invoice)
    return applied


def _refresh_invoice_payment_state(invoice: Invoice) -> Invoice:
    """
    `amount_paid` va statusni TAQSIMOTDAN qayta hisoblaydi.

    Kesh qo'shish/ayirish bilan emas, QAYTA HISOBLASH bilan yangilanadi:
    inkremental yangilash bitta o'tkazib yuborilgan hodisada jimgina
    siljiydi va siljish qachon boshlanganini hech kim ayta olmaydi.
    """
    # Manba — taqsimot jadvali, `payment.invoice` ustuni emas. Farq shu
    # yerda: avans ham taqsimlanadi, ya'ni hisob-faktura "to'landi" deb
    # belgilanishi uchun pul aynan SHU hujjatga kelgan bo'lishi shart
    # emas — u bolaning kassadagi puli bo'lsa ham yetadi.
    paid = _money(invoice_allocated(invoice))

    if paid <= 0:
        status = InvoiceStatus.ISSUED
    elif paid >= invoice.amount_due:
        status = InvoiceStatus.PAID
    else:
        status = InvoiceStatus.PARTIALLY_PAID

    # Muddati o'tgan, lekin to'liq to'lanmagan hisob-faktura `overdue`
    # bo'lib qoladi — u qarzdorlar ro'yxatidan tushib ketmasin.
    if status != InvoiceStatus.PAID and invoice.due_date < timezone.localdate():
        status = InvoiceStatus.OVERDUE

    Invoice.objects.filter(pk=invoice.pk).update(amount_paid=paid, status=status)
    invoice.refresh_from_db()
    return invoice


@transaction.atomic
def record_payment_batch(
    *,
    child: Child,
    lines: list[dict[str, Any]],
    invoice: Invoice | None = None,
    paid_at: Any = None,
    received_by: Any = None,
    idempotency_key: str = "",
) -> list[Payment]:
    """
    Bitta kassir harakatida bir nechta usulda to'lov (docs/03 §13.5a).

    Ota-ona 1 400 000 ni naqd, 100 000 ni terminalda beradi — bu bitta
    hodisa. U bir nechta `payment` qatori bo'lib yoziladi (usul qatorning
    bir qismi), lekin ular bitta `batch_id` bilan bog'lanadi va bitta
    tranzaksiyada yoziladi: yarim to'plam bo'lishi mumkin emas.

    **Ortiqcha summa rad ETILMAYDI.** Hisob-faktura qoldig'i to'lgach,
    qolgani hisob-fakturasiz avans bo'lib yoziladi va bolaning
    balansiga tushadi. Eski xatti-harakat — "ortiqcha to'lov" deb rad
    etish — kassa oldida noto'g'ri edi: pul allaqachon kassirning
    qo'lida, va uni qaytarib berish tizimning ishi emas.

    Taqsimlash tartibi qatorlar tartibida: birinchi qator avval
    hisob-fakturani to'ldiradi, oxirgisi avansga tushadi. Shunday qilib
    kassir qaysi usul avansga ketganini oldindan ko'radi.
    """
    if not lines:
        raise BusinessRuleViolation(gettext("Kamida bitta toʻlov qatori kerak."))

    # Takrorlanish TO'PLAM darajasida tekshiriladi, qator darajasida
    # emas — va bu farq muhim.
    #
    # Qator kaliti yolg'iz yetarli emasdi: qayta yuborishda
    # hisob-faktura allaqachon to'langan bo'ladi, shuning uchun
    # taqsimlash BOSHQA yo'ldan ketadi (`0a` o'rniga `0b`) va kalit
    # mos kelmay, o'sha pul ikkinchi marta avans bo'lib yozilardi.
    # Prefiks bo'yicha qidirish esa "bu forma allaqachon yuborilgan"
    # degan savolga yo'ldan qat'i nazar javob beradi.
    if idempotency_key:
        existing = list(
            Payment.objects.filter(idempotency_key__startswith=f"{idempotency_key}:").order_by(
                "created_at"
            )
        )
        if existing:
            return existing

    batch_id = uuid.uuid4()
    payments: list[Payment] = []

    def key(suffix: str) -> str:
        return f"{idempotency_key}:{suffix}" if idempotency_key else ""

    # Qoldiqni BIR MARTA o'qiymiz va o'zimiz kamaytirib boramiz.
    # `record_payment` har chaqiruvda qatorni qayta qulflab tekshiradi,
    # ya'ni baza baribir oxirgi so'zni aytadi — bu hisob esa qaysi
    # qator avansga tushishini oldindan bilish uchun.
    outstanding = Decimal("0")
    if invoice is not None:
        if invoice.child_id != child.id:
            raise BusinessRuleViolation(gettext("Hisob-faktura boshqa bolaga tegishli."))
        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if locked.status == InvoiceStatus.CANCELLED:
            raise BusinessRuleViolation(
                gettext("Bekor qilingan hisob-fakturaga toʻlov qabul qilinmaydi.")
            )
        outstanding = locked.amount_due - locked.amount_paid

    for index, line in enumerate(lines):
        amount = _money(Decimal(line["amount"]))
        if amount <= 0:
            raise BusinessRuleViolation(gettext("Toʻlov summasi musbat boʻlishi kerak."))
        method = line["method"]
        reference = str(line.get("reference", ""))

        applied = min(amount, outstanding) if invoice is not None else Decimal("0")
        if applied > 0:
            payments.append(
                record_payment(
                    child=child,
                    amount=applied,
                    method=method,
                    invoice=invoice,
                    reference=reference,
                    paid_at=paid_at,
                    received_by=received_by,
                    idempotency_key=key(f"{index}a"),
                    batch_id=batch_id,
                )
            )
            outstanding -= applied

        remainder = amount - applied
        if remainder > 0:
            payments.append(
                record_payment(
                    child=child,
                    amount=remainder,
                    method=method,
                    invoice=None,
                    reference=reference,
                    paid_at=paid_at,
                    received_by=received_by,
                    idempotency_key=key(f"{index}b"),
                    batch_id=batch_id,
                )
            )

    return payments


@transaction.atomic
def reverse_payment(*, payment: Payment, reason: str = "", created_by: Any = None) -> Payment:
    """
    To'lovni qaytaradi — QARSHI yozuv bilan, o'chirish bilan emas (D3).

    Asl to'lov qatori ham, asl ledger krediti ham joyida qoladi. Ustiga
    teng debet qo'shiladi. Shunda kassa jurnali "1 500 000 qabul qilindi,
    keyin qaytarildi" deb ko'rsatadi — "hech narsa bo'lmagan" emas.
    """
    if payment.is_reversed:
        raise BusinessRuleViolation(gettext("Bu toʻlov allaqachon qaytarilgan."))

    payment.reversed_at = timezone.now()
    payment.reversal_reason = reason[:255]
    payment.save(update_fields=["reversed_at", "reversal_reason", "updated_at"])

    post_ledger_entry(
        child=payment.child,
        entry_type=EntryType.REFUND,
        direction=Direction.DEBIT,
        amount=payment.amount,
        source_type=SourceType.PAYMENT,
        source_id=payment.id,
        description=f"To'lov qaytarildi: {reason}"[:255],
        created_by=created_by,
    )

    # Kassadan ham chiqadi — qarshi yozuv bilan, o'chirish bilan emas.
    cash.reverse_movements_for(
        source_type=MovementSource.PAYMENT,
        source_id=payment.id,
        description=reason or gettext("toʻlov qaytarildi"),
        created_by=created_by,
    )

    # Taqsimot bo'shaydi: pul endi hech qaysi hujjatni yopmaydi va
    # yopilgan deb belgilangan hisob-fakturalar yana ochiladi.
    release_allocations(payment=payment, reason=reason or gettext("toʻlov qaytarildi"))

    recompute_child_balance(payment.child)
    return payment


def receipt_number(payment: Payment) -> str:
    """
    Kvitansiya raqami — `KVT-YYYYMMDD-NNNN`.

    Alohida ketma-ketlik jadvali YO'Q va bu ataylab: raqam to'lovning
    o'z sanasi va o'sha kundagi tartibidan chiqadi, ya'ni qayta chop
    etilganda AYNAN o'sha raqam qaytadi. Saqlanadigan hisoblagich esa
    migratsiya, qulf va "raqam berildi, lekin to'lov yozilmadi" degan
    uchinchi holatni olib kelardi.

    To'lovlar append-only va `paid_at` o'zgarmaydi, shuning uchun
    tartib barqaror. Qaytarilgan to'lov ham sanaladi — u bo'lgan
    hodisa va uning kvitansiyasi ham bo'lgan.
    """
    day = timezone.localtime(payment.paid_at).date()
    order = (
        Payment.objects.filter(
            branch_id=payment.branch_id,
            paid_at__date=day,
        )
        .filter(Q(paid_at__lt=payment.paid_at) | Q(paid_at=payment.paid_at, id__lte=payment.id))
        .count()
    )
    return f"KVT-{day:%Y%m%d}-{order:04d}"


def receipt_for(payment: Payment) -> dict[str, Any]:
    """
    Kvitansiya ma'lumoti — bitta KASSIR HARAKATI bo'yicha (PLAN 1.7).

    Ota-ona 1 400 000 ni naqd, 100 000 ni terminalda to'lasa, bu bitta
    hodisa va ikkita to'lov qatori (`batch_id` ularni bog'laydi).
    Kvitansiya ham bitta bo'lishi kerak — ikkita qog'oz berish ota-onani
    "men ikki marta to'ladimmi?" degan savolga olib boradi.

    Qarz va avans kvitansiya ustida turadi, chunki ota-onaning keyingi
    savoli aynan shu: "yana qancha qoldi?".
    """
    lines = (
        Payment.objects.filter(batch_id=payment.batch_id).order_by("paid_at", "created_at")
        if payment.batch_id
        else Payment.objects.filter(pk=payment.pk)
    )
    lines = list(lines.select_related("child", "invoice", "received_by", "branch"))
    first = lines[0]

    allocations = (
        PaymentAllocation.objects.filter(payment__in=lines, released_at__isnull=True)
        .select_related("invoice")
        .order_by("allocated_at")
    )
    detail = balance.child_balance(first.child)

    return {
        "number": receipt_number(first),
        "paid_at": first.paid_at.isoformat(),
        "child": first.child.full_name,
        "branch": first.branch.name,
        "cashier": first.received_by.full_name if first.received_by_id else "",
        "reversed": any(line.reversed_at for line in lines),
        "lines": [
            {
                "method": str(PaymentMethod(line.method).label),
                "amount": f"{line.amount:.2f}",
                "reference": line.reference,
            }
            for line in lines
        ],
        "total": f"{sum((line.amount for line in lines), Decimal('0')):.2f}",
        # Pul qaysi hujjatlarni yopgani — nizoda eng kerakli qator.
        "allocations": [
            {
                "invoice": allocation.invoice.number,
                "period": f"{allocation.invoice.period_year}-{allocation.invoice.period_month:02d}",
                "amount": f"{allocation.amount:.2f}",
            }
            for allocation in allocations
        ],
        "balance_after": f"{detail.outstanding:.2f}",
        "advance_after": f"{detail.advance:.2f}",
    }


def daily_cash_summary(
    *, organization_id: Any, on_date: date, branch_id: Any = None
) -> dict[str, Any]:
    """Kassirning kunlik hisoboti — usul bo'yicha (docs/04 §9.3)."""
    queryset = Payment.objects.filter(
        organization_id=organization_id,
        paid_at__date=on_date,
        reversed_at__isnull=True,
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    by_method = {
        row["method"]: str(row["total"])
        for row in queryset.values("method").annotate(total=Sum("amount"))
    }
    total = queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    reversed_total = Payment.objects.filter(
        organization_id=organization_id,
        paid_at__date=on_date,
        reversed_at__isnull=False,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return {
        "date": on_date.isoformat(),
        "by_method": by_method,
        "total": str(_money(total)),
        "reversed_total": str(_money(reversed_total)),
        "count": queryset.count(),
    }
