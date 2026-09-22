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
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext

from apps.children.models import Child, EnrollmentStatus
from apps.core.exceptions import BusinessRuleViolation
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
    SourceType,
)

__all__ = [
    "child_balance",
    "post_ledger_entry",
    "issue_invoice",
    "cancel_invoice",
    "generate_monthly_invoices",
    "recompute_child_balance",
    "applicable_discount",
    "record_payment",
    "reverse_payment",
    "daily_cash_summary",
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
        raise BusinessRuleViolation(gettext("Ledger summasi musbat bo'lishi kerak."))

    return ChildLedgerEntry.objects.create(
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
    if child.tariff_id is None:
        raise BusinessRuleViolation(
            gettext(
                "{full_name}: tarif biriktirilmagan — hisob-faktura chiqarib bo'lmaydi."
            ).format(full_name=child.full_name)
        )

    existing = (
        Invoice.objects.filter(child=child, period_year=period_year, period_month=period_month)
        .exclude(status=InvoiceStatus.CANCELLED)
        .first()
    )
    if existing:
        return existing

    issued = issued_date or date(period_year, period_month, 1)
    if due_date is None:
        last_day = calendar.monthrange(period_year, period_month)[1]
        due_date = date(period_year, period_month, min(10, last_day))
    if due_date < issued:
        due_date = issued

    tariff = child.tariff
    assert tariff is not None  # yuqoridagi `tariff_id is None` tekshiruvi kafolati
    discount = applicable_discount(child, issued)
    amount_due, discount_amount = apply_discount(tariff.amount, discount)

    try:
        invoice = Invoice.objects.create(
            organization=child.organization,
            branch=child.branch,
            number=_next_invoice_number(child.branch, period_year, period_month),
            child=child,
            tariff=tariff,
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
        raise BusinessRuleViolation(gettext("Hisob-fakturani yaratib bo'lmadi.")) from exc

    InvoiceLine.objects.create(
        invoice=invoice,
        description=f"{tariff.name} — {period_month:02d}/{period_year}",
        quantity=Decimal("1"),
        unit_amount=tariff.amount,
        line_total=tariff.amount,
    )
    if discount_amount > 0 and discount is not None:
        InvoiceLine.objects.create(
            invoice=invoice,
            description=f"Chegirma: {discount.reason or discount}",
            quantity=Decimal("1"),
            unit_amount=-discount_amount,
            line_total=-discount_amount,
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
                "To'lov qilingan hisob-fakturani bekor qilib bo'lmaydi — avval to'lovni qaytaring."
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
    total_amount: Decimal = Decimal("0.00")

    def as_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "created": self.created,
            "skipped_existing": self.skipped_existing,
            "skipped_no_tariff": self.skipped_no_tariff,
            "total_amount": str(self.total_amount),
        }


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
        raise BusinessRuleViolation(gettext("Oy 1–12 oralig'ida bo'lishi kerak."))

    result = BillingRunResult(period=f"{period_year}-{period_month:02d}")

    children = Child.objects.filter(
        is_active=True, enrollment_status=EnrollmentStatus.ACTIVE
    ).select_related("tariff", "branch", "organization")
    if branch is not None:
        children = children.filter(branch=branch)

    for child in children:
        if child.tariff_id is None:
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
        raise BusinessRuleViolation(gettext("To'lov summasi musbat bo'lishi kerak."))

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
                gettext("Bekor qilingan hisob-fakturaga to'lov qabul qilinmaydi.")
            )

        locked = Invoice.objects.select_for_update().get(pk=invoice.pk)
        outstanding = locked.amount_due - locked.amount_paid
        if amount > outstanding:
            raise BusinessRuleViolation(
                gettext(
                    "Ortiqcha to'lov: qoldiq {outstanding}, kiritilgan {amount}. "
                    "Ortiqcha summani hisob-fakturasiz avans sifatida kiriting."
                ).format(outstanding=outstanding, amount=amount)
            )
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

    if locked is not None:
        _refresh_invoice_payment_state(locked)

    recompute_child_balance(child)

    # Ota-onaga kvitansiya SMS'i. Bu ATAYLAB tranzaksiyaning oxirida va
    # xatosi yutiladi: pul allaqachon qabul qilingan va yozilgan, uni
    # SMS shlyuzi ishlamagani uchun bekor qilish mumkin emas (P8).
    from apps.notifications.services import notify_payment_received

    notify_payment_received(payment=payment)
    return payment


def _refresh_invoice_payment_state(invoice: Invoice) -> Invoice:
    """
    `amount_paid` va statusni to'lovlardan qayta hisoblaydi.

    Kesh qo'shish/ayirish bilan emas, QAYTA HISOBLASH bilan yangilanadi:
    inkremental yangilash bitta o'tkazib yuborilgan hodisada jimgina
    siljiydi va siljish qachon boshlanganini hech kim ayta olmaydi.
    """
    paid = Payment.objects.filter(invoice=invoice, reversed_at__isnull=True).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0")
    paid = _money(paid)

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
def reverse_payment(*, payment: Payment, reason: str = "", created_by: Any = None) -> Payment:
    """
    To'lovni qaytaradi — QARSHI yozuv bilan, o'chirish bilan emas (D3).

    Asl to'lov qatori ham, asl ledger krediti ham joyida qoladi. Ustiga
    teng debet qo'shiladi. Shunda kassa jurnali "1 500 000 qabul qilindi,
    keyin qaytarildi" deb ko'rsatadi — "hech narsa bo'lmagan" emas.
    """
    if payment.is_reversed:
        raise BusinessRuleViolation(gettext("Bu to'lov allaqachon qaytarilgan."))

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

    if payment.invoice is not None:
        _refresh_invoice_payment_state(payment.invoice)

    recompute_child_balance(payment.child)
    return payment


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
