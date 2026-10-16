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
from datetime import date, datetime, time, timedelta
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
    BenefitKind,
    ChildLedgerEntry,
    Direction,
    Discount,
    DiscountType,
    EntryType,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    InvoiceWriteOff,
    MonthClose,
    Payment,
    PaymentAllocation,
    PaymentMethod,
    Refund,
    SourceType,
)

__all__ = [
    "child_balance",
    "post_ledger_entry",
    "issue_invoice",
    "cancel_invoice",
    "generate_monthly_invoices",
    "preview_monthly_invoices",
    "recompute_child_balance",
    "applicable_discount",
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


#: Turi bor imtiyozlar — qiymati sozlamadan (`benefits.*`), yozuvdan emas.
_BENEFIT_PERCENT_SETTING: dict[str, str] = {
    BenefitKind.STAFF_CHILD: "benefits.staff_child_percent",
    BenefitKind.LOW_INCOME: "benefits.low_income_percent",
    BenefitKind.FULL: "benefits.full_percent",
}


def benefit_terms(kind: str, branch: Any = None) -> tuple[str, Decimal]:
    """Imtiyoz turining amaldagi shartlari: (`percent` | `fixed`, qiymat)."""
    if kind == BenefitKind.SIBLING:
        return DiscountType.FIXED, Decimal(str(_setting("benefits.sibling_amount", branch) or 0))
    key = _BENEFIT_PERCENT_SETTING[kind]
    return DiscountType.PERCENT, Decimal(str(_setting(key, branch) or 0))


def apply_discount(base: Decimal, discount: Discount | None) -> tuple[Decimal, Decimal]:
    """
    Qaytaradi: (chegirmadan keyingi summa, chegirma summasi).

    `custom` — yozuvdagi qiymat; boshqa turlar — sozlamadagi (Bosqich 12.2).
    """
    if discount is None:
        return _money(base), Decimal("0.00")

    if discount.kind and discount.kind != BenefitKind.CUSTOM:
        discount_type, value = benefit_terms(discount.kind, discount.branch)
    else:
        discount_type, value = discount.discount_type, discount.value
    return _reduce(base, discount_type, value)


def _reduce(base: Decimal, discount_type: str, value: Decimal) -> tuple[Decimal, Decimal]:
    reduction = base * value / Decimal("100") if discount_type == DiscountType.PERCENT else value
    reduction = min(_money(reduction), _money(base))  # manfiy hisob-faktura bo'lmaydi
    return _money(base - reduction), reduction


def sibling_reduction(child: Child, year: int, month: int) -> Decimal:
    """
    Aka-uka chegirmasi — oila (umumiy vasiy) bo'yicha, avtomatik (Bosqich 12.2).

    Oilada shu oy hisob-faktura oladigan kamida ikki bola bo'lsa — har biriga
    `benefits.sibling_amount`. `benefits.sibling_rule = after_first` da eng
    oldin qabul qilingan bola to'liq to'laydi. Ikkinchi bola paydo bo'lishi
    bilan chegirma birinchisiga ham o'zi tushadi — hech kim uni qo'lda
    kiritmaydi va unutmaydi.
    """
    from apps.children.services import family_of, is_billable_for

    members = [
        member
        for member in family_of(child)
        if member.is_active
        and member.archived_at is None
        and is_billable_for(member, period_year=year, period_month=month)
    ]
    if len(members) < 2 or child.id not in {member.id for member in members}:
        return Decimal("0.00")
    if (
        str(_setting("benefits.sibling_rule", child.branch)) == "after_first"
        and members[0].id == child.id
    ):
        return Decimal("0.00")
    _kind, amount = benefit_terms(BenefitKind.SIBLING, child.branch)
    return _money(amount)


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


def is_month_closed(*, branch: Any, year: int, month: int) -> bool:
    """Shu filialning shu oyi yopilganmi (Bosqich 12.6)."""
    return MonthClose.objects.filter(branch=branch, period_year=year, period_month=month).exists()


def assert_month_open(*, branch: Any, year: int, month: int) -> None:
    """Yopilgan oyga tegadigan amalni rad etadi — sababi va yo'li bilan."""
    if is_month_closed(branch=branch, year=year, month=month):
        raise BusinessRuleViolation(
            gettext(
                "{month} oyi yopilgan — u faqat keyingi oyga tuzatish qatori orqali oʻzgaradi."
            ).format(month=f"{month:02d}.{year}")
        )


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
    # Yopilgan oy fakturasi o'zgarmaydi — kredit keyingi fakturaga
    # tuzatish qatori bo'lib tushadi (Bosqich 12.6).
    if is_month_closed(
        branch=claim.child.branch, year=claim.date_from.year, month=claim.date_from.month
    ):
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
        kind="credit",
        description=_credit_text(claim)[:255],
        formula=_credit_formula(claim, credit),
        absence_claim=claim,
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


def _credit_text(claim: Any) -> str:
    """Qayta hisob qatorining matni — qaysi qoida bilan (Bosqich 12.3)."""
    if claim.basis == "fixed_per_day":
        return gettext("Kelmagan kunlar: {days} kun × {rate} (ovqat puli)").format(
            days=claim.billable_days, rate=som(claim.daily_rate)
        )
    return gettext("Kelmagan kunlar uchun qayta hisob: {days} kun × {rate}").format(
        days=claim.billable_days, rate=som(claim.daily_rate)
    )


def _credit_formula(claim: Any, amount: Decimal) -> str:
    """
    "2 × 37 500 = 75 000". Faktura qoldig'i kichik bo'lsa, qatorga tushgan
    summa alohida aytiladi — formula hech qachon noto'g'ri arifmetika
    ko'rsatmaydi.
    """
    full = f"{claim.billable_days} × {som(claim.daily_rate)} = {som(claim.credit_amount)}"
    if _money(amount) != _money(claim.credit_amount):
        return f"{full} → {som(amount)}"
    return full


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

        text = _credit_text(claim)
        if (claim.date_from.year, claim.date_from.month) != (
            invoice.period_year,
            invoice.period_month,
        ):
            # Boshqa (ko'pincha yopilgan) oyning qayta hisobi — tuzatish
            # qatori: qaysi oy uchunligi matnda turadi (brif §2).
            text = gettext("Tuzatish ({month}): {text}").format(
                month=claim.date_from.strftime("%m.%Y"), text=text
            )
            from apps.intelligence import alerts

            alerts.notify(
                organization_id=invoice.organization_id,
                text=gettext("✏️ Yopilgan oyga tuzatish: {child} — {text}").format(
                    child=invoice.child.full_name, text=text
                ),
            )
        InvoiceLine.objects.create(
            invoice=invoice,
            kind="credit",
            description=text[:255],
            formula=_credit_formula(claim, credit),
            absence_claim=claim,
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

# Rejim qiymatlari va "birinchi oymi?" — hisoblagich bilan BITTA manba
# (`charges.py`); bu yerda faqat qayta eksport, eski importlar uchun.
from apps.finance.charges import (  # noqa: E402
    FIRST_MONTH_NEXT,
    _is_first_period,
    plan_month,
    som,
)


def _setting(key: str, branch: Any = None) -> Any:
    from apps.settings_app.services import get_setting

    return get_setting(key=key, branch=branch)


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
    assert_month_open(branch=child.branch, year=period_year, month=period_month)
    # Summa va qatorlar — YAGONA hisoblagichdan (Bosqich 12.1): oldindan
    # ko'rish, qayta hisob stavkasi va "Nega?" ham aynan shuni o'qiydi.
    charge = plan_month(child, period_year, period_month)
    price = charge.price
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
    if charge.skip == "next_month":
        raise BusinessRuleViolation(
            gettext(
                "{full_name}: sozlamaga koʻra birinchi hisob-faktura keyingi oydan yoziladi."
            ).format(full_name=child.full_name)
        )

    # Hujjat sanasi qabul sanasidan oldin bo'la olmaydi: 30-sentabrda
    # kelgan bolaning fakturasi 1-sentabrdan boshlansa, u kelmagan
    # kunlari uchun ham to'lagan bo'lardi.
    issued = issued_date or charge.issued_date or date(period_year, period_month, 1)
    if issued_date is not None and charge.issued_date is not None:
        issued = max(issued_date, charge.issued_date)
    if due_date is None:
        due_date = first_invoice_due_date(
            child=child, period_year=period_year, period_month=period_month
        )
    if due_date < issued:
        due_date = issued

    amount_due = charge.amount_due

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

    # Qatorlar hisoblagichdan — har biri o'z formulasi bilan: to'liq narx,
    # imtiyoz, so'ng "21 ish kunidan 8 kun: 3 050 000 × 8 / 21 = 1 162 000".
    # Raqam sababsiz turmaydi; "Nega?" ham shu formulani ko'rsatadi.
    for line in charge.lines:
        InvoiceLine.objects.create(
            invoice=invoice,
            kind=line.kind,
            description=line.description[:255],
            formula=line.formula[:255],
            benefit_kind=line.benefit_kind,
            discount_id=line.discount_id,
            quantity=Decimal("1"),
            unit_amount=line.amount,
            line_total=line.amount,
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
def write_off_invoice(
    *, invoice: Invoice, amount: Decimal, reason: str, created_by: Any = None
) -> InvoiceWriteOff:
    """
    Qarzning bir qismini yoki hammasini kechiradi — hujjat bilan (Bosqich 12.3).

    Mavjud yo'ldan (qayta hisob, PLAN 7.7): fakturaga sababi yozilgan minus
    qator, `amount_due` kamayadi, ledgerda KREDIT. Shuning uchun "qarz" ni
    hisoblaydigan hamma joy — doska, qarzdorlar, bola kartasi, hisobot — hech
    narsa o'zgartirmasdan to'g'ri qoladi (13-invariant: formula bitta).
    """
    cleaned = (reason or "").strip()
    if not cleaned:
        raise BusinessRuleViolation(gettext("Hisobdan chiqarish sababini yozing."))
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status not in (
        InvoiceStatus.ISSUED,
        InvoiceStatus.PARTIALLY_PAID,
        InvoiceStatus.OVERDUE,
    ):
        raise BusinessRuleViolation(gettext("Bu hisob-fakturada qarz yoʻq."))
    amount = _money(Decimal(amount))
    outstanding = _money(invoice.amount_due - invoice.amount_paid)
    if amount <= 0 or amount > outstanding:
        raise BusinessRuleViolation(
            gettext("Hisobdan faqat qolgan qarz chiqariladi: {outstanding}.").format(
                outstanding=som(outstanding)
            )
        )

    InvoiceLine.objects.create(
        invoice=invoice,
        kind="write_off",
        description=gettext("Hisobdan chiqarildi: {reason}").format(reason=cleaned)[:255],
        formula=f"{som(outstanding)} − {som(amount)} = {som(outstanding - amount)}",
        quantity=Decimal("1"),
        unit_amount=-amount,
        line_total=-amount,
    )
    Invoice.objects.filter(pk=invoice.pk).update(amount_due=invoice.amount_due - amount)
    invoice.amount_due -= amount
    post_ledger_entry(
        child=invoice.child,
        entry_type=EntryType.ADJUSTMENT,
        direction=Direction.CREDIT,
        amount=amount,
        source_type=SourceType.INVOICE,
        source_id=invoice.id,
        description=gettext("Hisobdan chiqarildi ({number}): {reason}").format(
            number=invoice.number, reason=cleaned
        )[:255],
        created_by=created_by,
    )
    _refresh_invoice_payment_state(invoice)
    record = InvoiceWriteOff.objects.create(
        organization=invoice.organization,
        branch=invoice.branch,
        invoice=invoice,
        amount=amount,
        reason=cleaned[:255],
        created_by=created_by,
    )
    recompute_child_balance(invoice.child)
    from apps.intelligence import alerts

    alerts.notify(
        organization_id=invoice.organization_id,
        text=gettext(
            "🧾 Qarz hisobdan chiqarildi: {child} — {amount} soʻm. Sabab: {reason}"
        ).format(child=invoice.child.full_name, amount=som(amount), reason=reason),
    )
    return record


@transaction.atomic
def cancel_invoice(*, invoice: Invoice, reason: str = "", created_by: Any = None) -> Invoice:
    """
    Hisob-fakturani bekor qiladi — QARSHI yozuv bilan.

    Ledger'dagi debet o'chirilmaydi: uning o'rniga teng kredit qo'shiladi.
    Shunda "nima bo'ldi?" degan savolga jurnal javob beradi (D3).
    """
    if invoice.status == InvoiceStatus.CANCELLED:
        return invoice
    assert_month_open(branch=invoice.branch, year=invoice.period_year, month=invoice.period_month)
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
        # Summa — `issue_invoice` bilan BIR XIL hisoblagichdan
        # (`charges.plan_month`). Ilgari bu yerda uning nusxasi turardi va
        # preview bilan generatsiya bir kun ajralib qolishi mumkin edi.
        charge = plan_month(child, period_year, period_month)
        if charge.skip == "no_price":
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

        if charge.skip == "next_month":
            preview.skipped_next_month.append(child.full_name)
            continue

        amount = charge.amount_due
        note = charge.proration_note

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
    payer: Any = None,
    employee: Any = None,
    backdate_reason: str = "",
    allocation_reason: str = "",
    payer_kind: str = "guardian",
    payer_org: str = "",
    payer_tin: str = "",
) -> Payment:
    """
    To'lovni qayd etadi — BITTA tranzaksiyada (docs/03 §13.5, §26).

    Bosqich 12.4 qoidalari shu yerda — har bir yo'l (kassa, onlayn, import)
    shu funksiyadan o'tadi: sana (`check_payment_date`), to'lovchi vasiy,
    `payroll` usulida xodim, va eng eski qarzni chetlab o'tgan tanlovga
    sabab (`_check_manual_allocation`).

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

    paid_at = paid_at or timezone.now()
    backdate_reason = check_payment_date(paid_at, backdate_reason)
    payer_name = _check_payer(child, payer)
    payer_kind, payer_name, payer_tin = _check_payer_kind(
        payer_kind, payer_name, payer_org, payer_tin
    )
    _check_payroll(method, employee)

    if invoice is not None:
        if invoice.child_id != child.id:
            raise BusinessRuleViolation(gettext("Hisob-faktura boshqa bolaga tegishli."))
        if invoice.status == InvoiceStatus.CANCELLED:
            raise BusinessRuleViolation(
                gettext("Bekor qilingan hisob-fakturaga toʻlov qabul qilinmaydi.")
            )
        allocation_reason = _check_manual_allocation(child, invoice, allocation_reason)
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
                paid_at=paid_at,
                received_by=received_by,
                idempotency_key=idempotency_key[:64],
                batch_id=batch_id,
                payer=payer,
                payer_name=payer_name,
                payer_kind=payer_kind,
                payer_tin=payer_tin,
                employee=employee if method == PaymentMethod.PAYROLL else None,
                backdate_reason=backdate_reason,
                allocation_reason=allocation_reason if invoice is not None else "",
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
    #
    # Oylikdan ushlashda qopga hech narsa TUSHMAYDI: pul kassadan oylik
    # bo'lib chiqmay qoladi. Uni bu yerda "kirim" desak, oylik to'langanda
    # yana "chiqim" bo'lmay, kassa yo'q pulni ko'rsatardi.
    if method == PaymentMethod.PAYROLL:
        _sync_payroll_tuition(payment)
    else:
        pot = cash.account_for_method(branch=payment.branch, method=method)
        cash.post_movement(
            account=pot,
            direction=MovementDirection.IN,
            amount=amount,
            source_type=MovementSource.PAYMENT,
            source_id=payment.id,
            description=(f"{child.full_name} — {locked.number}" if locked else child.full_name)[
                :255
            ],
            occurred_at=payment.paid_at,
            created_by=received_by,
        )
        # Usul komissiyasi — bank xarajati, o'sha qopdan (Bosqich 12.5).
        from apps.expenses.services import record_bank_commission

        # Muallifsiz: komissiyani kassir emas, bank o'zi ushlaydi — u
        # kassirning javobgarligidagi pulni kamaytirmasligi kerak.
        record_bank_commission(payment=payment, account=pot)

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


# --- To'lov qoidalari (Bosqich 12.4, brif §4) ---


def check_payment_date(paid_at: Any, reason: str = "") -> str:
    """
    To'lov sanasini tekshiradi; kerak bo'lsa sababni qaytaradi.

    Excel'da bitta katakda ikki sana, 2027 va 2029 yillar, sanasiz
    to'lovlar bor edi. Bu yerda: bitta yozuv — bitta sana (ustun bitta),
    kelajak — yo'q, `finance.backdate_days` dan eski — faqat sabab bilan.
    """
    from apps.settings_app.services import get_setting

    if not isinstance(paid_at, datetime):
        day = paid_at  # sana sifatida kelgan (import, testlar)
    elif timezone.is_aware(paid_at):
        day = timezone.localtime(paid_at).date()
    else:
        day = paid_at.date()
    today = timezone.localdate()
    if day > today:
        raise BusinessRuleViolation(
            gettext("Toʻlov sanasi kelajakda boʻlishi mumkin emas: {day}.").format(
                day=day.strftime("%d.%m.%Y")
            )
        )
    limit = int(get_setting(key="finance.backdate_days") or 0)
    reason = (reason or "").strip()[:255]
    if limit and (today - day).days > limit and not reason:
        raise BusinessRuleViolation(
            gettext("{days} kundan eski sana faqat sabab bilan kiritiladi.").format(days=limit)
        )
    return reason


def _check_payer(child: Child, payer: Any) -> str:
    """To'lovchi — shu bolaning vasiysi. Ismi suratga olinadi."""
    if payer is None:
        return ""
    from apps.children.models import ChildGuardian

    if not ChildGuardian.objects.filter(child=child, guardian=payer).exists():
        raise BusinessRuleViolation(gettext("Toʻlovchi bu bolaning vasiysi emas."))
    return str(payer.full_name)[:255]


def _check_payer_kind(kind: str, name: str, organization: str, tin: str) -> tuple[str, str, str]:
    """
    Ota-onaning ish beruvchisi to'laganda — tashkilot nomi va STIR (13.8).
    STIR 9 raqam; bo'sh qolishi mumkin, noto'g'risi — yo'q.
    """
    from apps.finance.models import PayerKind

    kind = kind or PayerKind.GUARDIAN
    if kind not in PayerKind.values:
        raise BusinessRuleViolation(gettext("Toʻlovchi turi notoʻgʻri."))
    tin = "".join(str(tin or "").split())
    if tin and not (tin.isdigit() and len(tin) == 9):
        raise BusinessRuleViolation(gettext("STIR 9 ta raqamdan iborat boʻlishi kerak."))
    if kind == PayerKind.GUARDIAN:
        return kind, name, ""
    organization = str(organization or "").strip()[:255]
    if not organization:
        raise BusinessRuleViolation(gettext("Toʻlovchi tashkilot nomini kiriting."))
    return kind, organization, tin


def _check_payroll(method: str, employee: Any) -> None:
    if method == PaymentMethod.PAYROLL and employee is None:
        raise BusinessRuleViolation(
            gettext("Oylikdan ushlash uchun xodimni tanlang — kimning oyligidan?")
        )


def _check_manual_allocation(child: Child, invoice: Invoice, reason: str) -> str:
    """
    Eng eski qarzni chetlab o'tish — faqat sabab bilan (brif §4).

    Sukut bo'yicha pul eng eski ochiq hujjatga ketadi. Kassir boshqa oyni
    tanlasa, eski qarz ochiq qoladi — buning sababi yozilmasa, keyin
    "nega avgust ochiq qoldi?" degan savolga hech kim javob bera olmaydi.
    Eng eskisini tanlash esa tanlov emas — sabab so'ralmaydi.
    """
    reason = (reason or "").strip()[:255]
    oldest = open_invoices(child).first()
    if oldest is not None and oldest.pk != invoice.pk and not reason:
        raise BusinessRuleViolation(
            gettext("Eng eski qarz — {period}. Boshqa oyni tanlash uchun sababini yozing.").format(
                period=f"{oldest.period_month:02d}.{oldest.period_year}"
            )
        )
    return reason


def _sync_payroll_tuition(payment: Payment) -> None:
    """
    Oylikdan ushlashni o'sha oyning oylik hisoblashiga yetkazadi.

    Hisoblash hali yo'q bo'lsa — u yaratilganda o'zi oladi (davr bo'yicha
    bog'lanadi, avans kabi). Yakunlangan bo'lsa — rad etiladi: yopilgan
    oylik o'zgarmaydi, demak ushlab ham bo'lmaydi.
    """
    from apps.payroll.models import PayrollRun, PayrollStatus
    from apps.payroll.services import sync_advances

    paid_at = payment.paid_at
    day = timezone.localtime(paid_at).date() if isinstance(paid_at, datetime) else paid_at
    run = PayrollRun.objects.filter(
        branch=payment.employee.branch if payment.employee else payment.branch,
        period_year=day.year,
        period_month=day.month,
    ).first()
    if run is None:
        return
    if run.status != PayrollStatus.DRAFT:
        raise BusinessRuleViolation(
            gettext(
                "{month} oyligi yopilgan — undan ushlab boʻlmaydi. Keyingi oy sanasi bilan "
                "kiriting yoki boshqa usulni tanlang."
            ).format(month=f"{day.month:02d}.{day.year}")
        )
    sync_advances(run)


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
    # Ota-onaga qaytarilgan qismi ham endi bizda emas (Bosqich 13.2b).
    refunded = Refund.objects.filter(payment=payment).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0")
    return _money(payment.amount - allocated - refunded)


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
    refunded = Refund.objects.filter(child=child, payment__reversed_at__isnull=True).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    return _money(paid - allocated - refunded)


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

    if invoice.amount_due <= 0:
        # To'liq qayta hisob yoki hisobdan chiqarish — to'lanadigan narsa
        # qolmadi. Ilgari bu `paid <= 0` ga tushib "chiqarilgan" bo'lib
        # qolardi va qarzdorlar ro'yxatida 0 so'mlik qarz turardi.
        status = InvoiceStatus.PAID
    elif paid <= 0:
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
    payer: Any = None,
    backdate_reason: str = "",
    allocation_reason: str = "",
    payer_kind: str = "guardian",
    payer_org: str = "",
    payer_tin: str = "",
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
                    payer=payer,
                    employee=line.get("employee"),
                    backdate_reason=backdate_reason,
                    allocation_reason=allocation_reason,
                    payer_kind=payer_kind,
                    payer_org=payer_org,
                    payer_tin=payer_tin,
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
                    payer=payer,
                    employee=line.get("employee"),
                    backdate_reason=backdate_reason,
                    payer_kind=payer_kind,
                    payer_org=payer_org,
                    payer_tin=payer_tin,
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
    if Refund.objects.filter(payment=payment).exists():
        # Qismi ota-onaga qaytarilgan: butun to'lovni bekor qilish o'sha
        # pulni ikkinchi marta qaytarardi.
        raise BusinessRuleViolation(
            gettext("Bu toʻlovdan ota-onaga pul qaytarilgan — uni bekor qilib boʻlmaydi.")
        )

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

    # Oylikdan ushlangan bo'lsa — oylik hisoblashidan ham qaytadi. Oylik
    # yopilgan bo'lsa bu rad etiladi va butun qaytarish ham bekor bo'ladi:
    # xodimga to'langan oylik endi o'zgarmaydi.
    if payment.method == PaymentMethod.PAYROLL:
        _sync_payroll_tuition(payment)

    recompute_child_balance(payment.child)
    from apps.intelligence import alerts

    alerts.notify(
        organization_id=payment.organization_id,
        text=gettext("↩️ Toʻlov bekor qilindi: {child} — {amount} soʻm. Sabab: {reason}").format(
            child=payment.child.full_name, amount=som(payment.amount), reason=reason or "—"
        ),
    )
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
        "payer": first.payer_name,
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
    *,
    organization_id: Any,
    on_date: date,
    branch_id: Any = None,
    received_by_id: Any = None,
) -> dict[str, Any]:
    """
    Kassirning kunlik hisoboti — usul bo'yicha (docs/04 §9.3).

    `received_by_id` — faqat shu xodim qabul qilgan pul (ADR-30).
    Filial va xodim filtri qaytarilganlar yig'indisiga ham tegadi:
    ilgari u faqat tashkilot bo'yicha sanalardi va filial kassiri
    boshqa filialning qaytarishlarini ham ko'rardi.
    """
    day = Payment.objects.filter(organization_id=organization_id, paid_at__date=on_date)
    if branch_id:
        day = day.filter(branch_id=branch_id)
    if received_by_id:
        day = day.filter(received_by_id=received_by_id)
    queryset = day.filter(reversed_at__isnull=True)

    by_method = {
        row["method"]: str(row["total"])
        for row in queryset.values("method").annotate(total=Sum("amount"))
    }
    total = queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    reversed_total = day.filter(reversed_at__isnull=False).aggregate(total=Sum("amount"))[
        "total"
    ] or Decimal("0")

    return {
        "date": on_date.isoformat(),
        "by_method": by_method,
        "total": str(_money(total)),
        "reversed_total": str(_money(reversed_total)),
        "count": queryset.count(),
    }


# --- Oyni yopish (Bosqich 12.6) ---


@transaction.atomic
def close_month(*, branch: Any, year: int, month: int, closed_by: Any = None) -> MonthClose:
    """
    Oyni yopadi — faqat tugagan, tengligi "yashil" oy, bir marta.

    Qizil oy yopilmaydi: noto'g'ri raqamni "rasmiy" qilib qotirish —
    Excel'dagi "tenglashtiruvchi qator"ning o'zi. Yig'ma suratga olinadi.
    """
    from apps.finance.selectors import monthly_summary

    if not 1 <= month <= 12:
        raise BusinessRuleViolation(gettext("Oy 1–12 oraligʻida boʻlishi kerak."))
    last_day = date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)
    if timezone.localdate() <= last_day:
        raise BusinessRuleViolation(gettext("Oy hali tugamagan — uni tugagach yopish mumkin."))
    if is_month_closed(branch=branch, year=year, month=month):
        raise BusinessRuleViolation(gettext("Bu oy allaqachon yopilgan."))

    summary = monthly_summary(
        organization_id=branch.organization_id, year=year, month=month, branch_id=branch.id
    )
    if not summary["check"]["ok"]:
        raise BusinessRuleViolation(
            gettext("Tenglik buzilgan ({equation}) — avval farqni toping, keyin yoping.").format(
                equation=summary["check"]["equation"]
            )
        )
    return MonthClose.objects.create(
        organization=branch.organization,
        branch=branch,
        period_year=year,
        period_month=month,
        closed_by=closed_by,
        snapshot=summary,
    )


# --- Ota-onaga pul qaytarish (Bosqich 13.2b) ---


@transaction.atomic
def refund_payment(
    *,
    payment: Payment,
    amount: Decimal,
    account: Any,
    reason: str,
    refunded_on: Any = None,
    created_by: Any = None,
    allow_negative: bool = False,
) -> Refund:
    """
    To'lovning ishlatilmagan (avans) qismini ota-onaga qaytaradi.

    Faktura yopgan pul qaytarilmaydi — avval taqsimot bo'shatilishi kerak
    (hisobdan chiqarish yoki fakturani bekor qilish). Bitta tranzaksiya:
    hujjat, ledger DEBET (oila endi o'sha pulga ega emas) va qopdan `out`.
    """
    reason = (reason or "").strip()
    if not reason:
        raise BusinessRuleViolation(gettext("Sabab yozilishi shart."))
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.is_reversed:
        raise BusinessRuleViolation(gettext("Bu toʻlov allaqachon qaytarilgan."))
    amount = _money(amount)
    spare = payment_unallocated(payment)
    if amount <= 0 or amount > spare:
        raise BusinessRuleViolation(
            gettext(
                "Bu toʻlovdan {spare} soʻmgacha qaytarish mumkin — qolgani fakturalarni yopgan."
            ).format(spare=som(spare))
        )
    if account.organization_id != payment.organization_id:
        raise BusinessRuleViolation(gettext("Kassa hisobi boshqa tashkilotga tegishli."))
    day = refunded_on or timezone.localdate()
    refund = Refund.objects.create(
        organization=payment.organization,
        branch=payment.branch,
        payment=payment,
        child=payment.child,
        cash_account=account,
        amount=amount,
        refunded_on=day,
        reason=reason[:255],
        created_by=created_by,
    )
    post_ledger_entry(
        child=payment.child,
        entry_type=EntryType.REFUND,
        direction=Direction.DEBIT,
        amount=amount,
        source_type=SourceType.REFUND,
        source_id=refund.id,
        description=gettext("Ota-onaga qaytarildi: {reason}").format(reason=reason)[:255],
        created_by=created_by,
    )
    cash.post_movement(
        account=account,
        direction=MovementDirection.OUT,
        amount=amount,
        source_type=MovementSource.REFUND,
        source_id=refund.id,
        description=f"{payment.child.full_name}: {reason}"[:255],
        occurred_at=timezone.make_aware(datetime.combine(day, time(12))),
        created_by=created_by,
        allow_negative=allow_negative,
    )
    recompute_child_balance(payment.child)
    return refund


# --- Yo'ldagi pul bankka tushdi (Bosqich 13.2c) ---


@transaction.atomic
def settle_payments(
    *, payments: list[Payment], settled_on: Any, reference: str = "", created_by: Any = None
) -> Decimal:
    """
    Bank tushumini tasdiqlaydi — bir nechta to'lov bitta tushum bo'lib
    kelishi mumkin (Click kunlik reestri). Qaytaradi: kutilgan jami.
    """
    from apps.expenses.models import Expense
    from apps.finance.models import TRANSIT_METHODS, PaymentSettlement

    if not payments:
        raise BusinessRuleViolation(gettext("Kamida bitta toʻlovni tanlang."))
    total = Decimal("0")
    for payment in payments:
        if payment.method not in TRANSIT_METHODS or payment.is_reversed:
            raise BusinessRuleViolation(
                gettext("Bu toʻlov yoʻlda emas: {child}.").format(child=payment.child.full_name)
            )
        if PaymentSettlement.objects.filter(payment=payment).exists():
            raise BusinessRuleViolation(
                gettext("Bu toʻlov allaqachon bankka tushgan: {child}.").format(
                    child=payment.child.full_name
                )
            )
        PaymentSettlement.objects.create(
            organization=payment.organization,
            branch=payment.branch,
            payment=payment,
            settled_on=settled_on,
            reference=reference.strip()[:120],
            created_by=created_by,
        )
        commission = Expense.objects.filter(payment=payment).aggregate(total=Sum("amount"))[
            "total"
        ] or Decimal("0")
        total += payment.amount - commission
    return _money(total)
