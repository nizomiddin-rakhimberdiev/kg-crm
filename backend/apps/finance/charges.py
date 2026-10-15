"""
Bitta oylik hisoblagich (Bosqich 12.1) — bolaning bir oy uchun summasi.

**Nega alohida modul.** Oyning summasi ilgari ikki joyda deyarli bir xil
nusxada hisoblanardi — `issue_invoice` va `preview_monthly_invoices` — va
kelmagan kunlar stavkasi hisob-fakturaning `amount_due` sidan olinardi. Oy
oʻrtasida kelgan bolada u allaqachon qisqartirilgan summa, ya'ni stavka
past chiqardi. Endi faktura, oldindan koʻrish, qayta hisob stavkasi,
"Nega?" tushuntirishi va oylik yigʻma hammasi `plan_month()` ni oʻqiydi.

Tartib — har doim shu:

1. **Narx** — tarif yoki individual summa (`child_monthly_price`).
2. **Imtiyoz** — `applicable_discount`; natija `monthly` — kunlik stavka
   shundan olinadi (brif: "imtiyozdan keyingi oylik summa").
3. **Ish kunlari oynasi** — kelgan kun, sinov muddati, ketgan kun, pauza.
4. **Yaxlitlash** — `finance.rounding_step` (sukut 1 000). Kunlik stavka
   emas, natija yaxlitlanadi: bir xil holatdagi bolalarga bir xil summa.

Har bir qator oʻz FORMULASINI olib yuradi ("3 050 000 × 8 / 21 = 1 162 000")
— hujjatdagi raqam oʻzini oʻzi tushuntiradi.

Bu modul hech narsa YOZMAYDI. Yozish `services.issue_invoice` da.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation

__all__ = [
    "ChargeLine",
    "MonthCharge",
    "plan_month",
    "rounding_step",
    "round_to_step",
    "trial_end",
    "credit_for_days",
    "som",
    "FIRST_MONTH_FULL",
    "FIRST_MONTH_PRORATED",
    "FIRST_MONTH_NEXT",
]

#: `finance.first_month_mode` qiymatlari. `prorated` endi ikkala chetni
#: qamraydi: kelgan oy (kelgan kundan) va ketgan oy (oxirgi kungacha).
FIRST_MONTH_FULL = "full"
FIRST_MONTH_PRORATED = "prorated"
FIRST_MONTH_NEXT = "next_month"


def _setting(key: str, branch: Any = None) -> Any:
    from apps.settings_app.services import get_setting

    return get_setting(key=key, branch=branch)


def som(value: Decimal | int) -> str:
    """Formula ichidagi raqam — "3 050 000" (tiyinsiz, boʻsh joy bilan)."""
    return f"{Decimal(value):,.0f}".replace(",", " ")


def rounding_step(branch: Any = None) -> Decimal:
    raw = _setting("finance.rounding_step", branch)
    try:
        step = Decimal(str(raw))
    except (ArithmeticError, ValueError):
        step = Decimal("1")
    return step if step > 0 else Decimal("1")


def round_to_step(value: Decimal, branch: Any = None) -> Decimal:
    """Eng yaqin qadamgacha — yarmi yuqoriga (1 161 905 → 1 162 000)."""
    step = rounding_step(branch)
    return ((Decimal(value) / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * step).quantize(
        Decimal("0.01")
    )


@dataclass(frozen=True)
class ChargeLine:
    """Hisob-faktura qatori — summasi va uni keltirib chiqargan formula."""

    kind: str  # base | benefit | proration | pause
    description: str
    amount: Decimal
    formula: str = ""
    #: `benefit` qatorida: imtiyoz turi va (qo'lda kiritilgan bo'lsa) yozuvi.
    benefit_kind: str = ""
    discount_id: Any = None


@dataclass
class MonthCharge:
    period_year: int
    period_month: int
    price: Any  # ChildPrice | None
    monthly: Decimal  # imtiyozdan keyingi to'liq oy
    discount: Any = None
    discount_amount: Decimal = Decimal("0")
    working_days: int = 0
    billable_days: int = 0
    amount_due: Decimal = Decimal("0")
    issued_date: date | None = None
    paused: bool = False
    #: Bo'sh emas — bu oy uchun hujjat yozilmaydi: `no_price`, `next_month`.
    skip: str = ""
    lines: list[ChargeLine] = field(default_factory=list)

    @property
    def daily_rate(self) -> Decimal:
        """Ko'rsatish uchun — butun so'mgacha (145 238)."""
        if not self.working_days:
            return Decimal("0")
        return (self.monthly / self.working_days).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    @property
    def proration_note(self) -> str:
        line = next((ln for ln in self.lines if ln.kind in ("proration", "pause")), None)
        return line.description if line else ""


def trial_end(child: Any) -> date | None:
    """Sinovning OXIRGI kuni — qabuldan boshlab N-ish kuni; sinov yo'q bo'lsa `None`."""
    from apps.attendance.services_absence import working_weekdays

    if child.skip_trial or child.is_existing_client or child.enrolled_on is None:
        return None
    days = int(_setting("finance.trial_days", child.branch) or 0)
    if days <= 0:
        return None

    from apps.attendance.models_absence import Holiday

    weekdays = working_weekdays(child.branch)
    closed = set(
        Holiday.objects.filter(
            organization_id=child.organization_id,
            is_active=True,
            holiday_date__gte=child.enrolled_on,
            holiday_date__lte=child.enrolled_on + timedelta(days=days * 7 + 14),
        ).values_list("holiday_date", flat=True)
    )
    counted = 0
    day = child.enrolled_on
    while True:
        if day.isoweekday() in weekdays and day not in closed:
            counted += 1
            if counted == days:
                return day
        day += timedelta(days=1)


def _is_first_period(child: Any, year: int, month: int) -> bool:
    """Qabul shu oyga tushadi va undan oldin hujjat yozilmagan."""
    from apps.finance.models import Invoice, InvoiceStatus

    enrolled = child.enrolled_on
    if enrolled is None or (enrolled.year, enrolled.month) != (year, month):
        return False
    return not Invoice.objects.filter(child=child).exclude(status=InvoiceStatus.CANCELLED).exists()


def plan_month(child: Any, year: int, month: int) -> MonthCharge:
    """Bolaning `year-month` uchun summasi va qatorlari — hech narsa yozmaydi."""
    from apps.attendance.services_absence import billable_days, working_days_in_month
    from apps.children.services import CLOSED_STATUSES, pause_for
    from apps.finance.models import BenefitKind
    from apps.finance.selectors import child_monthly_price
    from apps.finance.services import (
        applicable_discount,
        apply_discount,
        benefit_terms,
        sibling_reduction,
    )

    price = child_monthly_price(child)
    working = working_days_in_month(
        organization_id=child.organization_id, year=year, month=month, branch=child.branch
    )
    if price is None:
        return MonthCharge(
            period_year=year, period_month=month, price=None, monthly=Decimal("0"), skip="no_price"
        )
    if working <= 0:
        raise BusinessRuleViolation(
            gettext("{year}-{month:02d} oyida ish kuni yoʻq — kalendarni tekshiring.").format(
                year=year, month=month
            )
        )

    mode = str(_setting("finance.first_month_mode", child.branch))
    first = _is_first_period(child, year, month)
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    issued = month_start
    if first and child.enrolled_on is not None:
        issued = max(issued, child.enrolled_on)

    charge = MonthCharge(
        period_year=year,
        period_month=month,
        price=price,
        monthly=Decimal("0"),
        working_days=working,
        issued_date=issued,
    )
    if first and mode == FIRST_MONTH_NEXT:
        charge.skip = "next_month"
        return charge

    # Imtiyoz: qo'lda kiritilgani (turi, sababi bilan) ustun; yo'q bo'lsa —
    # oiladan aka-uka chegirmasi (Bosqich 12.2). Ular QO'SHILMAYDI:
    # qo'lda kiritilgan imtiyoz — odamning ongli qarori.
    discount = applicable_discount(child, issued)
    benefit_kind = ""
    if discount is not None:
        monthly, discount_amount = apply_discount(price.amount, discount)
        benefit_kind = discount.kind or BenefitKind.CUSTOM
    else:
        sibling = sibling_reduction(child, year, month)
        discount_amount = min(sibling, Decimal(price.amount).quantize(Decimal("0.01")))
        monthly = (Decimal(price.amount) - discount_amount).quantize(Decimal("0.01"))
        if discount_amount > 0:
            benefit_kind = BenefitKind.SIBLING
    charge.monthly = monthly
    charge.discount = discount
    charge.discount_amount = discount_amount

    # --- Ish kunlari oynasi ---
    prorate = mode == FIRST_MONTH_PRORATED
    start, end = month_start, month_end
    reasons: list[str] = []
    if prorate and not child.is_existing_client and child.enrolled_on is not None:
        if child.enrolled_on > month_start:
            start = child.enrolled_on
            reasons.append(gettext("kelgan: {d}").format(d=child.enrolled_on.strftime("%d.%m")))
        last_trial_day = trial_end(child)
        if last_trial_day is not None and last_trial_day >= start:
            start = last_trial_day + timedelta(days=1)
            reasons.append(
                gettext("sinov {n} ish kuni bepul").format(
                    n=int(_setting("finance.trial_days", child.branch))
                )
            )
    if (
        prorate
        and child.enrollment_status in CLOSED_STATUSES
        and child.status_changed_on is not None
        and child.status_changed_on <= month_end
    ):
        # Holat sanasi — bola bog'chada BO'LMAGAN birinchi kun.
        end = child.status_changed_on - timedelta(days=1)
        reasons.append(gettext("oxirgi kun: {d}").format(d=end.strftime("%d.%m")))

    pause = pause_for(child, year, month)
    if pause is not None:
        charge.paused = True
        charge.billable_days = 0
        charge.amount_due = Decimal("0.00")
    else:
        charge.billable_days = (
            billable_days(
                organization_id=child.organization_id,
                date_from=start,
                date_to=end,
                branch=child.branch,
            )
            if start <= end
            else 0
        )
        if charge.billable_days == working:
            charge.amount_due = monthly
        else:
            charge.amount_due = round_to_step(
                monthly * charge.billable_days / working, child.branch
            )

    # --- Qatorlar: yig'indisi har doim `amount_due` ---
    charge.lines.append(
        ChargeLine(
            kind="base",
            description=f"{price.label} — {month:02d}/{year}",
            amount=Decimal(price.amount).quantize(Decimal("0.01")),
        )
    )
    if discount_amount > 0:
        label = str(BenefitKind(benefit_kind).label) if benefit_kind else gettext("Chegirma")
        reason = discount.reason if discount is not None else ""
        if benefit_kind and benefit_kind != BenefitKind.CUSTOM:
            kind_type, value = benefit_terms(benefit_kind, child.branch)
            rule = f"{value:g}%" if kind_type == "percent" else som(value)
        elif discount is not None and discount.discount_type == "percent":
            rule = f"{discount.value:g}%"
        else:
            rule = som(discount_amount)
        charge.lines.append(
            ChargeLine(
                kind="benefit",
                description=(f"{label}: {reason}" if reason else label)[:255],
                amount=-discount_amount,
                formula=f"{som(price.amount)} − {rule} = {som(monthly)}",
                benefit_kind=benefit_kind,
                discount_id=discount.id if discount is not None else None,
            )
        )
    if charge.paused:
        charge.lines.append(
            ChargeLine(
                kind="pause",
                description=gettext("Vaqtincha toʻxtatilgan: {reason}").format(reason=pause.reason)[
                    :255
                ],
                amount=-monthly,
                formula=f"{som(monthly)} − {som(monthly)} = 0",
            )
        )
    elif charge.amount_due != monthly:
        formula = f"{som(monthly)} × {charge.billable_days} / {working} = {som(charge.amount_due)}"
        detail = "; ".join(reasons)
        charge.lines.append(
            ChargeLine(
                kind="proration",
                description=(
                    gettext("{total} ish kunidan {days} kun ({detail})").format(
                        total=working, days=charge.billable_days, detail=detail
                    )
                    if detail
                    else gettext("{total} ish kunidan {days} kun").format(
                        total=working, days=charge.billable_days
                    )
                )[:255],
                amount=charge.amount_due - monthly,
                formula=formula,
            )
        )
    return charge


def credit_for_days(*, child: Any, on_date: date, days: int) -> tuple[Decimal, Decimal, int]:
    """
    Kelmagan kunlar uchun to'liq stavkadagi qaytarish: (summa, stavka, oyning ish kunlari).

    Stavka — imtiyozdan keyingi TO'LIQ oylikdan, kesilgan fakturadan emas;
    natija `finance.rounding_step` gacha yaxlitlanadi (8 × 145 238 →
    1 162 000).
    """
    charge = plan_month(child, on_date.year, on_date.month)
    if charge.price is None:
        raise BusinessRuleViolation(
            gettext("{full_name}: narx belgilanmagan.").format(full_name=child.full_name)
        )
    working = charge.working_days
    rate = (charge.monthly / working).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    credit = round_to_step(charge.monthly * days / working, child.branch)
    return credit, rate, working
