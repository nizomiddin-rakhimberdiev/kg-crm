"""
Uch to'g'ri ko'rinish — bitta joyda (Bosqich 13.2d, brif §3.3–3.5).

* `profit_and_loss` — qaysi OYNING daromadi va xarajati (tegishli oy):
  faktura davri, chiqimning `period`i, oylik hisoblashning davri,
  investitsiyaning taqsimoti.
* `cash_flow` — pul QACHON harakatlangan: `cash_movement` sanasi, manba
  turi bo'yicha; o'tkazma tushum ham, chiqim ham emas.
* `position` — sanaga talablar va majburiyatlar: qoplar, yo'ldagi pul,
  ota-ona qarzi va avansi (bola jurnalidan), to'lanmagan oylik, nasiya,
  soliqlar, kreditlar.

Hech biri pulni qaytadan hisoblamaydi: hammasi mavjud jurnallar va
hujjatlardan o'qiydi (invariant 3, 12, 13). Bosqich 13.5 ning oylik
hisobot paketi shu funksiyalardan quriladi.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db.models import Case, DecimalField, Q, Sum, When
from django.db.models.functions import Coalesce, ExtractMonth, ExtractYear
from django.utils import timezone

__all__ = ["cash_flow", "data_completeness", "position", "profit_and_loss"]

ZERO = Decimal("0")
_DEC: DecimalField[Decimal, Decimal] = DecimalField(max_digits=16, decimal_places=2)


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)
    return start, end


def _end_of(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time.max))


def _scoped(queryset: Any, organization_id: Any, branch_id: Any) -> Any:
    queryset = queryset.filter(organization_id=organization_id)
    return queryset.filter(branch_id=branch_id) if branch_id else queryset


def _months_between(start: tuple[int, int], end: tuple[int, int]) -> int:
    return (end[0] - start[0]) * 12 + (end[1] - start[1])


# --- Foyda-zarar ---


def _expenses_for(organization_id: Any, branch_id: Any) -> Any:
    from apps.expenses.models import Expense, ExpenseStatus

    return (
        _scoped(Expense.objects, organization_id, branch_id)
        .filter(status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID])
        .annotate(
            p_year=Coalesce("period_year", ExtractYear("expense_date")),
            p_month=Coalesce("period_month", ExtractMonth("expense_date")),
        )
    )


def _amortization(organization_id: Any, branch_id: Any, year: int, month: int) -> Decimal:
    """
    Taqsimlangan investitsiyaning shu oyga tushgan ulushi.

    Ulush yaxlit so'mda; oxirgi oy qoldiqni oladi — N oy yig'indisi
    summaning o'ziga tiyinigacha teng.
    """
    total = ZERO
    for expense in _expenses_for(organization_id, branch_id).filter(
        is_capex=True, amortize_months__isnull=False
    ):
        index = _months_between((expense.p_year, expense.p_month), (year, month))
        months = expense.amortize_months
        if not 0 <= index < months:
            continue
        share = (expense.amount / months).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        total += expense.amount - share * (months - 1) if index == months - 1 else share
    return total


def profit_and_loss(
    *, organization_id: Any, year: int, month: int, branch_id: Any = None
) -> dict[str, Any]:
    """Oy uchun foyda-zarar — tegishli oy bo'yicha."""
    from apps.cash.models import MoneyOperation, OperationKind
    from apps.finance.models import Invoice, InvoiceStatus
    from apps.payroll.models import PayrollItem, PayrollStatus

    tuition = (
        _scoped(Invoice.objects, organization_id, branch_id)
        .filter(period_year=year, period_month=month)
        .exclude(status=InvoiceStatus.CANCELLED)
        .aggregate(total=Sum("amount_due"))["total"]
        or ZERO
    )
    operations = _scoped(MoneyOperation.objects, organization_id, branch_id)
    other_income = (
        operations.filter(
            kind=OperationKind.OTHER_INCOME, period_year=year, period_month=month
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    expenses = _expenses_for(organization_id, branch_id).filter(p_year=year, p_month=month)
    opex_rows = (
        expenses.filter(is_capex=False)
        .annotate(
            group=Coalesce("category__parent__name", "category__name"),
        )
        .values("group")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    operating_expenses = sum((row["total"] for row in opex_rows), ZERO)
    capex = (
        expenses.filter(is_capex=True, amortize_months__isnull=True).aggregate(total=Sum("amount"))[
            "total"
        ]
        or ZERO
    )
    amortization = _amortization(organization_id, branch_id, year, month)

    # Oylik — hisoblangan oyga: yalpi + ish beruvchi ijtimoiy soliq. Qoralama
    # hali hisoblanmagan, shuning uchun faqat yakunlangan va to'langan.
    payroll_rows = _scoped(PayrollItem.objects, organization_id, branch_id).filter(
        payroll_run__period_year=year,
        payroll_run__period_month=month,
        payroll_run__status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
    )
    payroll_totals = payroll_rows.aggregate(gross=Sum("gross"), social=Sum("tax_social"))
    payroll = (payroll_totals["gross"] or ZERO) + (payroll_totals["social"] or ZERO)

    start, end = _month_bounds(year, month)
    owner_draws = (
        operations.filter(
            kind=OperationKind.OWNER_DRAW, occurred_on__gte=start, occurred_on__lte=end
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    revenue = tuition + other_income
    operating_profit = revenue - operating_expenses - payroll - amortization
    return {
        "period": f"{year}-{month:02d}",
        "revenue": {
            "tuition": _money(tuition),
            "other": _money(other_income),
            "total": _money(revenue),
        },
        "operating_expenses": _money(operating_expenses),
        "expenses_by_category": [
            {"category": row["group"], "total": _money(row["total"])} for row in opex_rows
        ],
        "payroll": _money(payroll),
        "amortization": _money(amortization),
        "operating_profit": _money(operating_profit),
        "margin": f"{operating_profit / revenue * 100:.1f}" if revenue else None,
        # Foydaga kirmaydi — alohida qatorlar (brif §3.4, §5.3-9).
        "capex": _money(capex),
        "owner_draws": _money(owner_draws),
    }


# --- Pul oqimi ---

_OPERATION_FLOW = {
    "other_income": ("inflows", "other_income"),
    "owner_contribution": ("inflows", "owner_contributions"),
    "loan_in": ("inflows", "loans"),
    "owner_draw": ("outflows", "owner_draws"),
    "loan_repay": ("outflows", "loan_repayments"),
    "tax_payment": ("outflows", "taxes"),
}


def _signed(queryset: Any) -> Decimal:
    totals = queryset.aggregate(
        inn=Sum("amount", filter=Q(direction="in")), out=Sum("amount", filter=Q(direction="out"))
    )
    return (totals["inn"] or ZERO) - (totals["out"] or ZERO)


def cash_flow(
    *, organization_id: Any, year: int, month: int, branch_id: Any = None
) -> dict[str, Any]:
    """
    Oyning pul oqimi: boshlang'ich qoldiq + kirim − chiqim ± o'tkazma =
    oxirgi qoldiq. O'tkazma (inkassa, bankdan yechish) kirimga ham,
    chiqimga ham kirmaydi.
    """
    from apps.cash.models import CashMovement, MoneyOperation
    from apps.expenses.models import Expense

    start, end = _month_bounds(year, month)
    movements = _scoped(CashMovement.objects, organization_id, branch_id)
    opening = _signed(movements.filter(occurred_at__lt=_end_of(start - timedelta(days=1))))
    closing = _signed(movements.filter(occurred_at__lte=_end_of(end)))
    month_rows = list(
        movements.filter(
            occurred_at__gt=_end_of(start - timedelta(days=1)), occurred_at__lte=_end_of(end)
        ).values("source_type", "source_id", "direction", "amount", "transfer_group")
    )
    # Filiallar orasidagi o'tkazma (Bosqich 13.6, test 18): ikki oyog'i
    # boshqa-boshqa filialda. Filial uchun bu haqiqiy pul harakati;
    # konsolidatsiyada esa tashkilot pul topmaydi ham, yo'qotmaydi ham —
    # chiqarib tashlanadi.
    groups = {row["transfer_group"] for row in month_rows if row["source_type"] == "transfer"}
    legs: dict[Any, set[Any]] = {}
    for group, branch in CashMovement.objects.filter(
        organization_id=organization_id, transfer_group__in=groups - {None}
    ).values_list("transfer_group", "branch_id"):
        legs.setdefault(group, set()).add(branch)
    inter_branch = {group for group, branches in legs.items() if len(branches) > 1}

    capex_ids = set(
        Expense.objects.filter(
            pk__in=[row["source_id"] for row in month_rows if row["source_type"] == "expense"],
            is_capex=True,
        ).values_list("pk", flat=True)
    )
    operation_kinds = dict(
        MoneyOperation.objects.filter(
            pk__in=[row["source_id"] for row in month_rows if row["source_type"] == "operation"]
        ).values_list("pk", "kind")
    )

    inflows: dict[str, Decimal] = {}
    outflows: dict[str, Decimal] = {}
    transfers = {
        "in": ZERO,
        "out": ZERO,
        "inter_branch_in": ZERO,
        "inter_branch_out": ZERO,
        "eliminated": ZERO,
    }
    for row in month_rows:
        source, incoming, amount = row["source_type"], row["direction"] == "in", row["amount"]
        if source == "transfer":
            if row["transfer_group"] not in inter_branch:
                transfers["in" if incoming else "out"] += amount
            elif branch_id:
                transfers["inter_branch_in" if incoming else "inter_branch_out"] += amount
            elif incoming:
                transfers["eliminated"] += amount
            continue
        if source == "payment":
            key = "tuition"
        elif source == "payment_reversal":
            key = "reversals"
        elif source == "refund":
            key = "refunds"
        elif source == "expense":
            key = "capex" if row["source_id"] in capex_ids else "expenses"
        elif source in ("payroll", "advance"):
            key = "payroll"
        elif source == "operation":
            key = _OPERATION_FLOW.get(operation_kinds.get(row["source_id"], ""), ("", "other"))[1]
        else:  # opening, manual, count — tuzatishlar
            key = "adjustments"
        bucket = inflows if incoming else outflows
        bucket[key] = bucket.get(key, ZERO) + amount

    def finish(bucket: dict[str, Decimal], keys: tuple[str, ...]) -> dict[str, str]:
        out = {key: _money(bucket.get(key, ZERO)) for key in keys}
        for key, value in bucket.items():
            out.setdefault(key, _money(value))
        out["total"] = _money(sum(bucket.values(), ZERO))
        return out

    inflow_total = sum(inflows.values(), ZERO)
    outflow_total = sum(outflows.values(), ZERO)
    bridged = (
        opening
        + inflow_total
        - outflow_total
        + transfers["in"]
        - transfers["out"]
        + transfers["inter_branch_in"]
        - transfers["inter_branch_out"]
    )
    return {
        "period": f"{year}-{month:02d}",
        "opening": _money(opening),
        "inflows": finish(
            inflows, ("tuition", "other_income", "owner_contributions", "loans", "adjustments")
        ),
        "outflows": finish(
            outflows,
            (
                "expenses",
                "capex",
                "payroll",
                "refunds",
                "reversals",
                "owner_draws",
                "loan_repayments",
                "taxes",
                "adjustments",
            ),
        ),
        "transfers": {key: _money(value) for key, value in transfers.items()},
        "closing": _money(closing),
        "check": {"ok": bridged == closing, "bridged": _money(bridged)},
    }


# --- Holat (soddalashtirilgan balans) ---


def position(*, organization_id: Any, as_of: date, branch_id: Any = None) -> dict[str, Any]:
    """Sana oxiridagi talablar va majburiyatlar."""
    from apps.cash.models import CashMovement, MoneyOperation, OperationKind
    from apps.expenses.models import Expense, ExpenseStatus
    from apps.finance.models import ChildLedgerEntry
    from apps.finance.selectors import in_transit
    from apps.payroll.models import PayrollItem, PayrollPayout, PayrollStatus

    moment = _end_of(as_of)
    movements = _scoped(CashMovement.objects, organization_id, branch_id).filter(
        occurred_at__lte=moment
    )
    cash_total = _signed(movements.filter(cash_account__kind="cash"))
    bank_total = _signed(movements.exclude(cash_account__kind="cash"))
    transit = sum(
        (
            Decimal(row["expected_amount"])
            for row in in_transit(organization_id=organization_id, branch_id=branch_id, as_of=as_of)
        ),
        ZERO,
    )

    # Bola jurnali: musbat qoldiq — qarz, manfiy — avans (oila oldidagi majburiyat).
    balances = (
        _scoped(ChildLedgerEntry.objects, organization_id, branch_id)
        .filter(occurred_at__lte=moment)
        .values("child")
        .annotate(
            balance=Sum(Case(When(direction="debit", then="amount"), default=0, output_field=_DEC))
            - Sum(Case(When(direction="credit", then="amount"), default=0, output_field=_DEC))
        )
    )
    debts = sum((Decimal(row["balance"]) for row in balances if row["balance"] > 0), ZERO)
    advances = sum((-Decimal(row["balance"]) for row in balances if row["balance"] < 0), ZERO)

    # To'lanmagan oylik: tugagan oylarning hisoblangan sof oyligi − to'langani.
    finished = [PayrollStatus.FINALIZED, PayrollStatus.PAID]
    items = (
        _scoped(PayrollItem.objects, organization_id, branch_id)
        .filter(payroll_run__status__in=finished)
        .filter(
            Q(payroll_run__period_year__lt=as_of.year)
            | Q(payroll_run__period_year=as_of.year, payroll_run__period_month__lte=as_of.month)
        )
    )
    accrued_net = items.aggregate(total=Sum("net"))["total"] or ZERO
    paid_net = (
        _scoped(PayrollPayout.objects, organization_id, branch_id)
        .filter(payroll_run__in=items.values("payroll_run"), paid_on__lte=as_of)
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    unpaid_payroll = max(accrued_net - paid_net, ZERO)

    suppliers = (
        _scoped(Expense.objects, organization_id, branch_id)
        .filter(
            on_credit=True,
            status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
            expense_date__lte=as_of,
        )
        .filter(Q(paid_on__isnull=True) | Q(paid_on__gt=as_of))
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    operations = _scoped(MoneyOperation.objects, organization_id, branch_id).filter(
        occurred_on__lte=as_of
    )

    def op_sum(**filters: Any) -> Decimal:
        return operations.filter(**filters).aggregate(total=Sum("amount"))["total"] or ZERO

    dividend_tax = (
        operations.filter(kind=OperationKind.OWNER_DRAW).aggregate(total=Sum("tax_amount"))["total"]
        or ZERO
    ) - op_sum(kind=OperationKind.TAX_PAYMENT, subtype="dividend_tax")
    payroll_taxes = (
        items.aggregate(total=Sum("tax_income") + Sum("tax_pension") + Sum("tax_social"))["total"]
        or ZERO
    )
    payroll_taxes -= op_sum(
        kind=OperationKind.TAX_PAYMENT, subtype__in=["income_tax", "social_tax"]
    )
    taxes = max(dividend_tax, ZERO) + max(payroll_taxes, ZERO)
    loans = max(op_sum(kind=OperationKind.LOAN_IN) - op_sum(kind=OperationKind.LOAN_REPAY), ZERO)

    assets = {
        "cash": cash_total,
        "bank": bank_total - transit,
        "in_transit": transit,
        "parent_debts": debts,
    }
    liabilities = {
        "advances": advances,
        "unpaid_payroll": unpaid_payroll,
        "suppliers": suppliers,
        "taxes": taxes,
        "loans": loans,
    }
    total_assets = sum(assets.values(), ZERO)
    total_liabilities = sum(liabilities.values(), ZERO)
    return {
        "as_of": as_of.isoformat(),
        "assets": {**{k: _money(v) for k, v in assets.items()}, "total": _money(total_assets)},
        "liabilities": {
            **{k: _money(v) for k, v in liabilities.items()},
            "total": _money(total_liabilities),
        },
        "net": _money(total_assets - total_liabilities),
    }


# --- Ma'lumot to'liqligi (Bosqich 13.3e) ---


def data_completeness(
    *, organization_id: Any, year: int, month: int, branch_id: Any = None
) -> dict[str, Any]:
    """
    Hisobot qanchalik to'liq ma'lumotga tayanadi (brif §4).

    * xarajatlarning necha foizida chek bor (bank komissiyasi — avtomatik,
      sanalmaydi);
    * naqd kassada pul harakatlangan kunlar va ularning nechtasi sanoq
      bilan yopilgan;
    * bank ko'chirmasi oy oxirigacha yuklanganmi, moslashtirilmagan qatorlar.
    """
    from apps.cash.models import BankStatement, BankStatementLine, CashCount, CashMovement
    from apps.expenses.models import Expense, ExpenseStatus

    start, end = _month_bounds(year, month)
    expenses = _scoped(Expense.objects, organization_id, branch_id).filter(
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
        expense_date__gte=start,
        expense_date__lte=end,
        payment__isnull=True,
    )
    total = expenses.count()
    with_receipt = expenses.exclude(receipt="").count()

    active_days = (
        _scoped(CashMovement.objects, organization_id, branch_id)
        .filter(
            cash_account__kind="cash",
            occurred_at__gt=_end_of(start - timedelta(days=1)),
            occurred_at__lte=_end_of(end),
        )
        .exclude(source_type__in=["opening", "count"])
        .dates("occurred_at", "day")
        .count()
    )
    closed_days = (
        _scoped(CashCount.objects, organization_id, branch_id)
        .filter(cash_account__kind="cash", counted_on__gte=start, counted_on__lte=end)
        .values("counted_on")
        .distinct()
        .count()
    )
    statements = _scoped(BankStatement.objects, organization_id, branch_id)
    last = statements.order_by("-period_to").values_list("period_to", flat=True).first()
    unmatched = (
        _scoped(BankStatementLine.objects, organization_id, branch_id)
        .filter(status="unmatched", booked_on__lte=end)
        .count()
    )
    return {
        "period": f"{year}-{month:02d}",
        "expenses": {
            "total": total,
            "with_receipt": with_receipt,
            "percent": round(with_receipt * 100 / total) if total else None,
        },
        "cash": {"active_days": active_days, "closed_days": closed_days},
        "bank": {
            # Oxirgi uch kungacha yetgan ko'chirma — oy "yuklangan".
            "statement_uploaded": bool(last and last >= end - timedelta(days=3)),
            "last_statement_on": last.isoformat() if last else None,
            "unmatched_lines": unmatched,
        },
    }
