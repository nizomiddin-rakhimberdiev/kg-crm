"""
Pul prognozi 30 / 60 / 90 kun va xavfsiz olish summasi (Bosqich 13.7,
brif §5.3-12; test 11).

Prognoz — taxmin, shuning uchun har qatori sanasi va ASOSI bilan qaytadi:
"sentabr fakturalari × oxirgi 3 oy yig'ish darajasi", "nasiya, muddati
12.10", "avgust oyligi, to'lanmagan". Hech qanday raqam ko'rinmas
koeffitsientdan kelmaydi.

* Boshlang'ich pul — `money.position`: kassa + bank + yo'ldagi pul.
* Kirim — joriy oy fakturalarining kutilgan qismi va kelgusi oylar
  (joriy oy summasi × yig'ish darajasi), har biri `finance.due_day` da.
  Eski qarzlar kirimga qo'shilmaydi — ehtiyotkor taxmin.
* Chiqim — to'lanmagan oylik va soliq (hozir), kelgusi oyliklar
  (`forecast.pay_day`) va soliqlar (`forecast.tax_day`) oxirgi yakunlangan
  hisob bo'yicha, nasiya muddati bilan, doimiy xarajatlar oxirgi 3 oy
  o'rtachasi bilan.
* Xavfsiz olish = pul − 30 kun ichidagi chiqim − zaxira. Zaxira —
  `forecast.reserve_amount`, bo'lmasa `forecast.reserve_months` × oylik
  fondi (yalpi + ijtimoiy soliq). Hech qachon manfiy emas: yetishmovchilik
  alohida ko'rsatiladi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Q, Sum
from django.utils.translation import gettext

__all__ = ["HORIZONS", "forecast", "payroll_fund"]

HORIZONS = (30, 60, 90)
ZERO = Decimal("0")


def _money(value: Decimal) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def _setting(key: str, branch_id: Any, default: Any) -> Any:
    from apps.settings_app.services import get_setting

    value = get_setting(key=key, branch=branch_id)
    return default if value in (None, "") else value


def _decimal(value: Any, default: Decimal) -> Decimal:
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError, TypeError):
        return default


def _scoped(queryset: Any, organization_id: Any, branch_id: Any) -> Any:
    queryset = queryset.filter(organization_id=organization_id)
    return queryset.filter(branch_id=branch_id) if branch_id else queryset


def _day_of(year: int, month: int, day: int) -> date:
    import calendar

    return date(year, month, min(max(day, 1), calendar.monthrange(year, month)[1]))


def _shift(year: int, month: int, by: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + by
    return index // 12, index % 12 + 1


def _last_run(organization_id: Any, branch_id: Any, as_of: date) -> dict[str, Decimal]:
    """Oxirgi yakunlangan oylik hisobi — kelgusi oylar shundan taxmin qilinadi."""
    from apps.payroll.models import PayrollItem, PayrollRun, PayrollStatus

    runs = _scoped(PayrollRun.objects, organization_id, branch_id).filter(
        status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID]
    )
    runs = runs.filter(
        Q(period_year__lt=as_of.year) | Q(period_year=as_of.year, period_month__lte=as_of.month)
    )
    latest = runs.order_by("-period_year", "-period_month").first()
    if latest is None:
        return {"gross": ZERO, "net": ZERO, "taxes": ZERO, "social": ZERO}
    items = _scoped(PayrollItem.objects, organization_id, branch_id).filter(
        payroll_run__period_year=latest.period_year,
        payroll_run__period_month=latest.period_month,
        payroll_run__status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
    )
    totals = items.aggregate(
        gross=Sum("gross"),
        net=Sum("net"),
        income=Sum("tax_income"),
        pension=Sum("tax_pension"),
        social=Sum("tax_social"),
    )
    return {
        "gross": totals["gross"] or ZERO,
        "net": totals["net"] or ZERO,
        "taxes": (totals["income"] or ZERO)
        + (totals["pension"] or ZERO)
        + (totals["social"] or ZERO),
        "social": totals["social"] or ZERO,
    }


def payroll_fund(organization_id: Any, branch_id: Any, as_of: date) -> Decimal:
    """Oylik ish haqi fondi: yalpi + ish beruvchi ijtimoiy soliq (brif §5.3-12)."""
    run = _last_run(organization_id, branch_id, as_of)
    return run["gross"] + run["social"]


def _collection_rate(organization_id: Any, branch_id: Any, as_of: date) -> Decimal | None:
    """Oxirgi 3 tugagan oy: shu sanagacha yig'ilgan ÷ to'lanishi kerak."""
    from datetime import datetime, time

    from django.utils import timezone

    from apps.finance.models import Invoice, InvoiceStatus, PaymentAllocation

    periods = [_shift(as_of.year, as_of.month, -back) for back in (1, 2, 3)]
    where = Q()
    for year, month in periods:
        where |= Q(period_year=year, period_month=month)
    invoices = (
        _scoped(Invoice.objects, organization_id, branch_id)
        .filter(where)
        .exclude(status=InvoiceStatus.CANCELLED)
    )
    due = invoices.aggregate(total=Sum("amount_due"))["total"] or ZERO
    if due <= 0:
        return None
    moment = timezone.make_aware(datetime.combine(as_of, time.max))
    collected = (
        PaymentAllocation.objects.filter(
            invoice__in=invoices, released_at__isnull=True, payment__paid_at__lte=moment
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    return min(collected / due, Decimal("1"))


def _month_collected(
    organization_id: Any, branch_id: Any, year: int, month: int, as_of: date
) -> tuple[Decimal, Decimal]:
    from datetime import datetime, time

    from django.utils import timezone

    from apps.finance.models import Invoice, InvoiceStatus, PaymentAllocation

    invoices = (
        _scoped(Invoice.objects, organization_id, branch_id)
        .filter(period_year=year, period_month=month)
        .exclude(status=InvoiceStatus.CANCELLED)
    )
    due = invoices.aggregate(total=Sum("amount_due"))["total"] or ZERO
    moment = timezone.make_aware(datetime.combine(as_of, time.max))
    collected = (
        PaymentAllocation.objects.filter(
            invoice__in=invoices, released_at__isnull=True, payment__paid_at__lte=moment
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    return due, collected


def _recurring(organization_id: Any, branch_id: Any, as_of: date) -> Decimal:
    """Oxirgi 3 to'liq oyda xarajatga chiqqan pul (investitsiyasiz) ÷ 3."""
    from datetime import datetime, time

    from django.utils import timezone

    from apps.cash.models import CashMovement
    from apps.expenses.models import Expense

    start_year, start_month = _shift(as_of.year, as_of.month, -3)
    start = timezone.make_aware(datetime.combine(date(start_year, start_month, 1), time.min))
    end = timezone.make_aware(datetime.combine(as_of.replace(day=1), time.min))
    moves = _scoped(CashMovement.objects, organization_id, branch_id).filter(
        source_type="expense", occurred_at__gte=start, occurred_at__lt=end
    )
    capex = Expense.objects.filter(pk__in=moves.values("source_id"), is_capex=True).values_list(
        "pk", flat=True
    )
    out = moves.filter(direction="out").exclude(source_id__in=list(capex))
    back = moves.filter(direction="in").exclude(source_id__in=list(capex))
    spent = (out.aggregate(t=Sum("amount"))["t"] or ZERO) - (
        back.aggregate(t=Sum("amount"))["t"] or ZERO
    )
    return max(spent, ZERO) / 3


def forecast(*, organization_id: Any, as_of: date, branch_id: Any = None) -> dict[str, Any]:
    from apps.expenses.models import Expense, ExpenseStatus
    from apps.reports import money

    position = money.position(organization_id=organization_id, as_of=as_of, branch_id=branch_id)
    opening = sum(
        (Decimal(position["assets"][key]) for key in ("cash", "bank", "in_transit")), ZERO
    )
    horizon_end = as_of + timedelta(days=max(HORIZONS))
    lines: list[dict[str, Any]] = []

    def add(day: date, direction: str, key: str, amount: Decimal, basis: str) -> None:
        if amount <= 0 or day > horizon_end:
            return
        lines.append(
            {
                "date": max(day, as_of).isoformat(),
                "direction": direction,
                "key": key,
                "amount": _money(amount),
                "basis": basis,
            }
        )

    # --- Kirim: ota-ona to'lovlari ---
    due_day = int(_decimal(_setting("finance.due_day", branch_id, 10), Decimal(10)))
    rate = _collection_rate(organization_id, branch_id, as_of)
    applied = rate if rate is not None else Decimal("1")
    rate_text = (
        gettext("oxirgi 3 oy yigʻish darajasi {rate}%").format(rate=f"{applied * 100:.1f}")
        if rate is not None
        else gettext("yigʻish tarixi yoʻq — 100% olindi")
    )
    due_now, collected_now = _month_collected(
        organization_id, branch_id, as_of.year, as_of.month, as_of
    )
    expected_now = max(due_now * applied - collected_now, ZERO)
    due_date = _day_of(as_of.year, as_of.month, due_day)
    add(
        due_date if due_date > as_of else as_of + timedelta(days=7),
        "in",
        "tuition",
        expected_now,
        gettext("{month:02d}.{year} fakturalari × {rate}, yigʻilgani ayirildi").format(
            month=as_of.month, year=as_of.year, rate=rate_text
        ),
    )
    roster_due = due_now
    if roster_due <= 0:
        previous = _shift(as_of.year, as_of.month, -1)
        roster_due, _ = _month_collected(organization_id, branch_id, *previous, as_of)
    for ahead in range(1, 4):
        year, month = _shift(as_of.year, as_of.month, ahead)
        add(
            _day_of(year, month, due_day),
            "in",
            "tuition",
            roster_due * applied,
            gettext("{month:02d}.{year}: joriy oy summasi × {rate}").format(
                month=month, year=year, rate=rate_text
            ),
        )

    # --- Chiqim: oylik va soliq ---
    pay_day = int(_decimal(_setting("forecast.pay_day", branch_id, 10), Decimal(10)))
    tax_day = int(_decimal(_setting("forecast.tax_day", branch_id, 15), Decimal(15)))
    unpaid = Decimal(position["liabilities"]["unpaid_payroll"])
    add(as_of, "out", "payroll", unpaid, gettext("Hisoblangan, hali toʻlanmagan oylik"))
    taxes = Decimal(position["liabilities"]["taxes"])
    next_tax = _day_of(as_of.year, as_of.month, tax_day)
    if next_tax < as_of:
        next_tax = _day_of(*_shift(as_of.year, as_of.month, 1), tax_day)
    add(next_tax, "out", "taxes", taxes, gettext("Hisoblangan, hali toʻlanmagan soliqlar"))

    from apps.payroll.models import PayrollRun, PayrollStatus

    run = _last_run(organization_id, branch_id, as_of)
    finished = set(
        _scoped(PayrollRun.objects, organization_id, branch_id)
        .filter(status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID])
        .values_list("period_year", "period_month")
    )
    for ahead in range(0, 4):
        year, month = _shift(as_of.year, as_of.month, ahead)
        period = _shift(year, month, -1)  # shu oy to'lanadigan oylik — o'tgan oyniki
        if period in finished:
            continue  # yuqorida "to'lanmagan" sifatida bor
        add(
            _day_of(year, month, pay_day),
            "out",
            "payroll",
            run["net"],
            gettext("{month:02d}.{year} oyligi — oxirgi hisob boʻyicha").format(
                month=period[1], year=period[0]
            ),
        )
        add(
            _day_of(year, month, tax_day),
            "out",
            "taxes",
            run["taxes"],
            gettext("{month:02d}.{year} oylik soliqlari — oxirgi hisob boʻyicha").format(
                month=period[1], year=period[0]
            ),
        )

    # --- Chiqim: nasiya ---
    credits = (
        _scoped(Expense.objects, organization_id, branch_id)
        .filter(
            on_credit=True,
            status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
            expense_date__lte=as_of,
        )
        .filter(Q(paid_on__isnull=True) | Q(paid_on__gt=as_of))
        .select_related("supplier")
    )
    for expense in credits:
        due = expense.due_date or expense.expense_date + timedelta(days=30)
        add(
            due,
            "out",
            "suppliers",
            expense.amount,
            gettext("Nasiya: {supplier}, muddati {due}").format(
                supplier=expense.supplier.name if expense.supplier else "—",
                due=due.strftime("%d.%m.%Y"),
            ),
        )

    # --- Chiqim: doimiy xarajatlar ---
    monthly = _recurring(organization_id, branch_id, as_of)
    for step in range(3):
        add(
            as_of + timedelta(days=15 + 30 * step),
            "out",
            "expenses",
            monthly,
            gettext("Xarajatlar — oxirgi 3 oy oʻrtachasi"),
        )

    lines.sort(key=lambda line: (line["date"], line["direction"]))
    buckets: list[dict[str, Any]] = []
    obligations = ZERO
    for days in HORIZONS:
        limit = (as_of + timedelta(days=days)).isoformat()
        inflows: dict[str, Decimal] = {"tuition": ZERO}
        outflows: dict[str, Decimal] = {
            "payroll": ZERO,
            "taxes": ZERO,
            "suppliers": ZERO,
            "expenses": ZERO,
        }
        for line in lines:
            if line["date"] > limit:
                continue
            bucket = inflows if line["direction"] == "in" else outflows
            bucket[line["key"]] = bucket.get(line["key"], ZERO) + Decimal(line["amount"])
        total_in = sum(inflows.values(), ZERO)
        total_out = sum(outflows.values(), ZERO)
        if days == HORIZONS[0]:
            obligations = total_out
        buckets.append(
            {
                "days": days,
                "until": limit,
                "inflows": {
                    **{k: _money(v) for k, v in inflows.items()},
                    "total": _money(total_in),
                },
                "outflows": {
                    **{k: _money(v) for k, v in outflows.items()},
                    "total": _money(total_out),
                },
                "closing": _money(opening + total_in - total_out),
            }
        )

    reserve_amount = _decimal(_setting("forecast.reserve_amount", branch_id, 0), ZERO)
    if reserve_amount > 0:
        reserve = reserve_amount
        reserve_basis = gettext("Sozlamadagi summa")
    else:
        months = _decimal(_setting("forecast.reserve_months", branch_id, "0.5"), Decimal("0.5"))
        reserve = (months * payroll_fund(organization_id, branch_id, as_of)).quantize(
            Decimal("0.01")
        )
        reserve_basis = gettext("{months} oylik ish haqi fondi").format(months=months.normalize())
    left = opening - obligations - reserve
    return {
        "as_of": as_of.isoformat(),
        "opening": _money(opening),
        "basis": {
            "collection_rate": f"{rate * 100:.1f}" if rate is not None else None,
            "recurring_monthly": _money(monthly),
            "payroll_net": _money(run["net"]),
            "excluded": gettext("Eski qarzlar va kreditlar jadvali kirimga qoʻshilmagan."),
        },
        "lines": lines,
        "buckets": buckets,
        "safe_withdrawal": {
            "money": _money(opening),
            "obligations_30": _money(obligations),
            "reserve": _money(reserve),
            "reserve_basis": reserve_basis,
            "amount": _money(max(left, ZERO)),
            "shortfall": _money(max(-left, ZERO)),
        },
    }
