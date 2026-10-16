"""
Oylik moliyaviy hisobot paketi (Bosqich 13.5, brif §5.3).

Bitta deterministik funksiya: (tashkilot, filial, davr) → JSON. Web, PDF,
Excel va arxiv shu JSON'ni ko'rsatadi; hech bir raqam bu yerda qayta
hisoblanmaydi — hammasi modul selektorlaridan (`monthly_summary`,
`money.*`, `control.*`). Shu sabab "hisobotdagi raqam ekrandagiga teng"
qoidasi tuzilmaning o'zida (test 19).

Tuzilma har oy bir xil — 16 bo'lim, bir xil kalitlar. Raqamlar yonida
o'tgan oy va 3 oylik o'rtacha; asosiy raqamlarda manba kaliti (`source`)
— u `source_rows` orqali yozuvlar ro'yxatiga ochiladi.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Max, Q, Sum
from django.utils.translation import gettext

__all__ = ["build", "checksum", "diff", "source_rows", "SECTION_KEYS"]

ZERO = Decimal("0")
SECTION_KEYS = (
    "summary",
    "children",
    "revenue",
    "receipts",
    "debts",
    "expenses",
    "payroll",
    "cash_bank",
    "pnl",
    "profit_vs_cash",
    "position",
    "plan",
    "taxes",
    "checks",
    "attention",
    "appendix",
)


def _m(value: Any) -> str:
    return f"{Decimal(str(value or 0)):.2f}"


def _d(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    return start, date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)


def _shift(year: int, month: int, back: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) - back
    return index // 12, index % 12 + 1


def _scoped(queryset: Any, organization_id: Any, branch_id: Any) -> Any:
    queryset = queryset.filter(organization_id=organization_id)
    return queryset.filter(branch_id=branch_id) if branch_id else queryset


def _pct(part: Decimal, whole: Decimal) -> str | None:
    return f"{part * 100 / whole:.1f}" if whole else None


def _compare(current: Decimal, previous: Decimal, history: list[Decimal]) -> dict[str, Any]:
    average = sum(history, ZERO) / len(history) if history else ZERO
    delta = current - previous
    return {
        "value": _m(current),
        "prev": _m(previous),
        "avg3": _m(average.quantize(Decimal("0.01"))),
        "delta": _m(delta),
        "delta_pct": _pct(delta, previous) if previous else None,
    }


# --- Bo'limlar ---


def _children(org: Any, branch: Any, year: int, month: int) -> dict[str, Any]:
    from apps.attendance.models import AttendanceRecord
    from apps.children.models import Child, ChildPause, Enrollment, EnrollmentStatus, Group
    from apps.finance.selectors import monthly_summary

    start, end = _bounds(year, month)
    children = _scoped(Child.objects, org, branch).filter(is_active=True)
    closed = [EnrollmentStatus.WITHDRAWN, EnrollmentStatus.GRADUATED]
    at_start = children.filter(Q(enrolled_on__isnull=True) | Q(enrolled_on__lt=start)).exclude(
        enrollment_status__in=closed, status_changed_on__lt=start
    )
    arrived = children.filter(enrolled_on__gte=start, enrolled_on__lte=end).count()
    left = children.filter(
        enrollment_status__in=closed, status_changed_on__gte=start, status_changed_on__lte=end
    ).count()
    paused = (
        _scoped(ChildPause.objects, org, branch)
        .filter(month_from__lte=start, month_to__gte=start)
        .count()
    )
    begin = at_start.count()

    members = dict(
        _scoped(Enrollment.objects, org, branch)
        .filter(status="active", end_date__isnull=True)
        .values("group_id")
        .annotate(n=Count("id"))
        .values_list("group_id", "n")
    )
    groups = [
        {
            "id": str(group.id),
            "name": group.name,
            "children": members.get(group.id, 0),
            "capacity": group.capacity,
            "occupancy": _pct(Decimal(members.get(group.id, 0)), Decimal(group.capacity))
            if group.capacity
            else None,
        }
        for group in _scoped(Group.objects, org, branch).filter(is_active=True).order_by("name")
    ]
    records = (
        _scoped(AttendanceRecord.objects, org, branch)
        .filter(attendance_date__gte=start, attendance_date__lte=end)
        .aggregate(total=Count("id"), present=Count("id", filter=Q(status="present")))
    )
    summary = monthly_summary(organization_id=org, year=year, month=month, branch_id=branch)
    return {
        "movement": {
            "start": begin,
            "arrived": arrived,
            "left": left,
            "paused": paused,
            "end": begin + arrived - left,
        },
        "categories": summary["categories"],
        "groups": groups,
        "attendance_rate": _pct(Decimal(records["present"]), Decimal(records["total"])),
        "churn_rate": _pct(Decimal(left), Decimal(begin)),
    }


def _benefit_breakdown(org: Any, branch: Any, year: int, month: int) -> dict[str, Any]:
    from apps.finance.models import InvoiceLine

    lines = InvoiceLine.objects.filter(
        invoice__organization_id=org,
        invoice__period_year=year,
        invoice__period_month=month,
        kind="benefit",
    ).exclude(invoice__status="cancelled")
    if branch:
        lines = lines.filter(invoice__branch_id=branch)
    by_kind = [
        {"kind": row["benefit_kind"] or "custom", "total": _m(row["total"])}
        for row in lines.values("benefit_kind").annotate(total=Sum("line_total")).order_by("total")
    ]
    by_who = [
        {"who": row["discount__created_by__full_name"] or "—", "total": _m(row["total"])}
        for row in lines.values("discount__created_by__full_name")
        .annotate(total=Sum("line_total"))
        .order_by("total")
    ]
    return {"by_kind": by_kind, "by_who": by_who}


def _revenue(org: Any, branch: Any, year: int, month: int) -> dict[str, Any]:
    from apps.cash.models import MoneyOperation
    from apps.finance.selectors import monthly_summary

    summary = monthly_summary(organization_id=org, year=year, month=month, branch_id=branch)
    py, pm = _shift(year, month, 1)
    previous = monthly_summary(organization_id=org, year=py, month=pm, branch_id=branch)
    invoiced, collected = summary["invoiced"], summary["collected_for_month"]
    charged, benefits = _d(invoiced["charged"]), _d(invoiced["benefits"])
    recalcs, due = _d(invoiced["recalculations"]), _d(invoiced["amount_due"])
    roster = summary["roster"]

    # Farq omillarga (brif §5.3-3, test 15). Bolalar soni × o'rtacha narx
    # ajratiladi; imtiyoz va qayta hisob — o'z farqi bilan. Yig'indisi
    # ta'rifga ko'ra umumiy farqqa teng: hech qanday "qoldiq" qator yo'q.
    def invoiced_children(data: dict[str, Any]) -> int:
        return sum(row["children"] for row in data["categories"] if row["category"] != "no_invoice")

    n1, n0 = invoiced_children(summary), invoiced_children(previous)
    c0 = _d(previous["invoiced"]["charged"])
    avg0 = c0 / n0 if n0 else ZERO
    children_effect = (Decimal(n1 - n0) * avg0).quantize(Decimal("0.01"))
    price_effect = charged - c0 - children_effect
    benefit_effect = benefits - _d(previous["invoiced"]["benefits"])
    recalc_effect = recalcs - _d(previous["invoiced"]["recalculations"])
    total_change = due - _d(previous["invoiced"]["amount_due"])

    other = (
        _scoped(MoneyOperation.objects, org, branch)
        .filter(kind="other_income", period_year=year, period_month=month)
        .values("subtype")
        .annotate(total=Sum("amount"))
    )
    return {
        "chain": [
            {
                "id": "charged",
                "label": gettext("Toʻliq narxdagi summa"),
                "value": _m(charged),
                "source": "invoices:due",
            },
            {
                "id": "benefits",
                "label": gettext("Imtiyozlar"),
                "value": _m(benefits),
                "source": "lines:benefit",
            },
            {
                "id": "recalculations",
                "label": gettext("Qayta hisoblar"),
                "value": _m(recalcs),
                "source": "lines:recalculation",
            },
            {
                "id": "due",
                "label": gettext("Toʻlanishi kerak"),
                "value": _m(due),
                "source": "invoices:due",
            },
            {
                "id": "collected",
                "label": gettext("Yigʻilgan"),
                "value": collected["total"],
                "before": collected["before_month"],
                "in_month": collected["in_month"],
                "after": collected["after_month"],
                "source": "allocations:collected",
            },
            {
                "id": "debt",
                "label": gettext("Qarz"),
                "value": summary["outstanding"],
                "source": "invoices:open",
            },
        ],
        "benefits": _benefit_breakdown(org, branch, year, month),
        "recalculations": summary["recalculations"],
        "other_income": [{"subtype": row["subtype"], "total": _m(row["total"])} for row in other],
        "kpi": {
            "collection_rate": _pct(_d(collected["total"]), due),
            "benefit_share": _pct(-benefits, charged),
            "average_per_child": _m((due / roster).quantize(Decimal("0.01"))) if roster else None,
        },
        "factors": {
            "total_change": _m(total_change),
            "items": [
                {
                    "id": "children",
                    "label": gettext("Bolalar soni taʼsiri"),
                    "value": _m(children_effect),
                },
                {"id": "price", "label": gettext("Narx taʼsiri"), "value": _m(price_effect)},
                {
                    "id": "benefits",
                    "label": gettext("Imtiyoz taʼsiri"),
                    "value": _m(benefit_effect),
                },
                {
                    "id": "recalculations",
                    "label": gettext("Qayta hisob taʼsiri"),
                    "value": _m(recalc_effect),
                },
            ],
        },
        "_summary": summary,
    }


def _receipts(org: Any, branch: Any, year: int, month: int, due: Decimal) -> dict[str, Any]:
    from django.utils import timezone

    from apps.finance.models import Payment, PaymentAllocation

    start, end = _bounds(year, month)
    payments = _scoped(Payment.objects, org, branch).filter(
        reversed_at__isnull=True, paid_at__date__gte=start, paid_at__date__lte=end
    )
    matrix: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: ZERO))
    allocated: dict[Any, Decimal] = defaultdict(lambda: ZERO)
    for allocation in PaymentAllocation.objects.filter(
        payment__in=payments, released_at__isnull=True
    ).select_related("payment", "invoice"):
        invoice = allocation.invoice
        period = (invoice.period_year, invoice.period_month)
        if period < (year, month):
            column = f"{invoice.period_year}-{invoice.period_month:02d}"
        elif period == (year, month):
            column = "current"
        else:
            column = "future"
        matrix[allocation.payment.method][column] += allocation.amount
        allocated[allocation.payment_id] += allocation.amount
    daily: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for payment in payments:
        spare = payment.amount - allocated.get(payment.id, ZERO)
        if spare > 0:
            matrix[payment.method]["future"] += spare
        daily[timezone.localtime(payment.paid_at).date().isoformat()] += payment.amount

    # Yig'ish egri chizig'i: oy fakturalarini yopgan pul, N-kungacha kelgani.
    month_allocations = PaymentAllocation.objects.filter(
        invoice__organization_id=org,
        invoice__period_year=year,
        invoice__period_month=month,
        released_at__isnull=True,
    ).exclude(invoice__status="cancelled")
    if branch:
        month_allocations = month_allocations.filter(invoice__branch_id=branch)
    # Bitta so'rov: har to'lovning sanasi va summasi; egri chiziq Python'da.
    paid_days = list(month_allocations.values_list("payment__paid_at", "amount"))
    curve = {}
    for label, limit in (("5", 5), ("10", 10), ("15", 15), ("20", 20), ("end", end.day)):
        cutoff = date(year, month, limit)
        reached = sum(
            (
                amount
                for paid_at, amount in paid_days
                if timezone.localtime(paid_at).date() <= cutoff
            ),
            ZERO,
        )
        curve[label] = _pct(reached, due)
    return {
        "matrix": [
            {"method": method, **{column: _m(value) for column, value in columns.items()}}
            for method, columns in sorted(matrix.items())
        ],
        "daily": [{"day": day, "total": _m(total)} for day, total in sorted(daily.items())],
        "curve": curve,
        "total": _m(sum((p.amount for p in payments), ZERO)),
    }


def _debts(org: Any, branch: Any, year: int, month: int, summary: dict[str, Any]) -> dict[str, Any]:
    from apps.finance.models import Invoice, InvoiceWriteOff, Payment

    start, end = _bounds(year, month)
    open_invoices = (
        _scoped(Invoice.objects, org, branch)
        .filter(status__in=["issued", "partially_paid", "overdue"])
        .filter(Q(period_year__lt=year) | Q(period_year=year, period_month__lte=month))
        .select_related("child")
    )
    per_child: dict[Any, dict[str, Any]] = {}
    for invoice in open_invoices:
        row = per_child.setdefault(
            invoice.child_id,
            {"child": invoice.child.full_name, "amount": ZERO, "oldest_due": invoice.due_date},
        )
        row["amount"] += invoice.amount_due - invoice.amount_paid
        row["oldest_due"] = min(row["oldest_due"], invoice.due_date)
    last_paid = dict(
        _scoped(Payment.objects, org, branch)
        .filter(child_id__in=per_child, reversed_at__isnull=True)
        .values("child_id")
        .annotate(last=Max("paid_at"))
        .values_list("child_id", "last")
    )
    debtors = sorted(per_child.items(), key=lambda item: -item[1]["amount"])[:20]
    write_offs = (
        _scoped(InvoiceWriteOff.objects, org, branch)
        .filter(created_at__date__gte=start, created_at__date__lte=end)
        .select_related("invoice__child", "created_by")
    )
    return {
        "aging": summary["aging"],
        "debtors": [
            {
                "child": row["child"],
                "amount": _m(row["amount"]),
                "days": max((end - row["oldest_due"]).days, 0),
                "last_payment": last_paid[child_id].date().isoformat()
                if last_paid.get(child_id)
                else None,
            }
            for child_id, row in debtors
            if row["amount"] > 0
        ],
        "new_debt": summary["outstanding"],
        "write_offs": [
            {
                "child": row.invoice.child.full_name,
                "amount": _m(row.amount),
                "reason": row.reason,
                "by": row.created_by.full_name if row.created_by_id else "",
            }
            for row in write_offs
        ],
        "advances_for_later": summary["cash_received"]["advances_for_later"],
    }


def _expenses(
    org: Any, branch: Any, year: int, month: int, pnl_history: list[dict]
) -> dict[str, Any]:
    from apps.attendance.models import AttendanceRecord
    from apps.expenses.models import Expense, ExpenseStatus
    from apps.settings_app.services import get_setting

    start, end = _bounds(year, month)
    current, previous = pnl_history[0], pnl_history[1]
    history = pnl_history[1:4]

    def by_cat(data: dict[str, Any]) -> dict[str, Decimal]:
        return {row["category"]: _d(row["total"]) for row in data["expenses_by_category"]}

    categories = by_cat(current)
    past = [by_cat(data) for data in history]
    rows = [
        {
            "category": name,
            **_compare(total, past[0].get(name, ZERO), [p.get(name, ZERO) for p in past]),
        }
        for name, total in sorted(categories.items(), key=lambda item: -item[1])
    ]
    expenses = (
        _scoped(Expense.objects, org, branch)
        .filter(status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID])
        .filter(
            Q(period_year=year, period_month=month)
            | Q(period_year__isnull=True, expense_date__gte=start, expense_date__lte=end)
        )
        .select_related("category", "supplier")
    )
    top = [
        {
            "date": row.expense_date.isoformat(),
            "category": row.category.name,
            "amount": _m(row.amount),
            "description": row.description,
            "has_receipt": bool(row.receipt),
        }
        for row in expenses.order_by("-amount")[:10]
    ]
    suppliers = [
        {"supplier": row["supplier__name"], "total": _m(row["total"])}
        for row in expenses.exclude(supplier__isnull=True)
        .values("supplier__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    ]
    roster = current["_roster"]
    opex = _d(current["operating_expenses"])
    food_name = str(get_setting(key="report.food_category") or "Oziq-ovqat")
    food = (
        expenses.filter(
            Q(category__name=food_name) | Q(category__parent__name=food_name), is_capex=False
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    child_days = (
        _scoped(AttendanceRecord.objects, org, branch)
        .filter(attendance_date__gte=start, attendance_date__lte=end, status="present")
        .count()
    )
    return {
        "by_category": rows,
        "top": top,
        "suppliers": suppliers,
        "per_child": _m((opex / roster).quantize(Decimal("0.01"))) if roster else None,
        "food_per_child_day": _m((food / child_days).quantize(Decimal("0.01")))
        if child_days
        else None,
        "previous_total": previous["operating_expenses"],
    }


def _payroll(org: Any, branch: Any, year: int, month: int, revenue: Decimal) -> dict[str, Any]:
    from apps.payroll.models import PayrollItem, PayrollPayout

    _start, end = _bounds(year, month)
    items = _scoped(PayrollItem.objects, org, branch).filter(
        payroll_run__period_year=year,
        payroll_run__period_month=month,
        payroll_run__status__in=["finalized", "paid"],
    )
    totals = items.aggregate(
        gross=Sum("gross"),
        advance=Sum("advance"),
        tuition=Sum("tuition"),
        card=Sum("official_net"),
        cash=Sum("cash_net"),
        income=Sum("tax_income"),
        pension=Sum("tax_pension"),
        social=Sum("tax_social"),
        net=Sum("net"),
    )
    paid = (
        _scoped(PayrollPayout.objects, org, branch)
        .filter(payroll_run__period_year=year, payroll_run__period_month=month, paid_on__lte=end)
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    gross, social = _d(totals["gross"]), _d(totals["social"])
    return {
        "accrued": _m(gross),
        "advances": _m(totals["advance"]),
        "tuition_withheld": _m(totals["tuition"]),
        "card": _m(totals["card"]),
        "cash": _m(totals["cash"]),
        "withheld_taxes": _m(_d(totals["income"]) + _d(totals["pension"])),
        "social_tax": _m(social),
        "paid": _m(paid),
        "unpaid": _m(max(_d(totals["net"]) - paid, ZERO)),
        "share_of_revenue": _pct(gross + social, revenue),
    }


def _cash_bank(org: Any, branch: Any, year: int, month: int) -> dict[str, Any]:
    from datetime import datetime, time

    from django.utils import timezone

    from apps.cash.models import BankStatement, CashAccount, CashCount, CashMovement
    from apps.cash.selectors import custody
    from apps.finance.selectors import in_transit

    start, end = _bounds(year, month)
    before = timezone.make_aware(datetime.combine(start - timedelta(days=1), time.max))
    until = timezone.make_aware(datetime.combine(end, time.max))
    bridges = []
    for account in (
        _scoped(CashAccount.objects, org, branch).filter(is_active=True).order_by("kind")
    ):
        moves = CashMovement.objects.filter(cash_account=account)

        def total(queryset: Any, direction: str) -> Decimal:
            return queryset.filter(direction=direction).aggregate(t=Sum("amount"))["t"] or ZERO

        opening = total(moves.filter(occurred_at__lte=before), "in") - total(
            moves.filter(occurred_at__lte=before), "out"
        )
        month_moves = moves.filter(occurred_at__gt=before, occurred_at__lte=until)
        transfers = month_moves.filter(source_type="transfer")
        others = month_moves.exclude(source_type="transfer")
        inflow, outflow = total(others, "in"), total(others, "out")
        t_in, t_out = total(transfers, "in"), total(transfers, "out")
        closing = opening + inflow - outflow + t_in - t_out
        bridges.append(
            {
                "account": account.name,
                "kind": account.kind,
                "opening": _m(opening),
                "in": _m(inflow),
                "out": _m(outflow),
                "transfers_in": _m(t_in),
                "transfers_out": _m(t_out),
                "closing": _m(closing),
            }
        )
    counts = [
        {
            "day": row.counted_on.isoformat(),
            "account": row.cash_account.name,
            "difference": _m(row.difference),
            "reason": row.reason,
        }
        for row in _scoped(CashCount.objects, org, branch)
        .filter(counted_on__gte=start, counted_on__lte=end)
        .select_related("cash_account")
    ]
    statements = [
        {
            "file": row.file_name,
            "period_to": row.period_to.isoformat() if row.period_to else None,
            "closing_balance": _m(row.closing_balance) if row.closing_balance is not None else None,
            "system_balance": _m(row.system_balance) if row.system_balance is not None else None,
        }
        for row in _scoped(BankStatement.objects, org, branch).filter(
            period_to__gte=start, period_from__lte=end
        )
    ]
    transit = in_transit(organization_id=org, branch_id=branch, as_of=end)
    return {
        "bridges": bridges,
        "counts": counts,
        "statements": statements,
        "in_transit": _m(sum((Decimal(row["expected_amount"]) for row in transit), ZERO)),
        "custody": custody(organization_id=org, branch_id=branch),
    }


def _profit_vs_cash(pnl: dict[str, Any], flow: dict[str, Any]) -> dict[str, Any]:
    """
    "Foyda ≠ pul" sharsharasi (brif §5.3-10, test 10).

    Har qadam — hisobot raqami bilan pul oqimi orasidagi aniq farq; shuning
    uchun yig'indi pul (kassa + bank + yo'ldagi) o'zgarishiga TIYINIGACHA
    teng — "boshqa" degan yashirin qator yo'q, kutilmagan manba bo'lsa u
    nomi bilan chiqadi.
    """
    inflows = {key: _d(value) for key, value in flow["inflows"].items() if key != "total"}
    outflows = {key: _d(value) for key, value in flow["outflows"].items() if key != "total"}
    revenue_tuition = _d(pnl["revenue"]["tuition"])
    revenue_other = _d(pnl["revenue"]["other"])
    tuition_cash = (
        inflows.pop("tuition", ZERO)
        - outflows.pop("refunds", ZERO)
        - outflows.pop("reversals", ZERO)
    )
    steps = [
        ("receivables", gettext("Qarzlar va avanslar oʻzgarishi"), tuition_cash - revenue_tuition),
        (
            "other_income",
            gettext("Boshqa daromad: hisoblangan va kelgan farqi"),
            inflows.pop("other_income", ZERO) - revenue_other,
        ),
        (
            "payroll",
            gettext("Toʻlanmagan ish haqi oʻzgarishi"),
            _d(pnl["payroll"]) - outflows.pop("payroll", ZERO),
        ),
        (
            "payables",
            gettext("Nasiya va xarajat vaqti farqi"),
            _d(pnl["operating_expenses"]) - outflows.pop("expenses", ZERO),
        ),
        ("amortization", gettext("Amortizatsiya (pul emas)"), _d(pnl["amortization"])),
        ("capex", gettext("Kapital xarajat"), -outflows.pop("capex", ZERO)),
        ("owner_draws", gettext("Egasiga toʻlov"), -outflows.pop("owner_draws", ZERO)),
        ("contributions", gettext("Egadan kiritma"), inflows.pop("owner_contributions", ZERO)),
        (
            "loans",
            gettext("Kredit (olindi − qaytarildi)"),
            inflows.pop("loans", ZERO) - outflows.pop("loan_repayments", ZERO),
        ),
        ("taxes", gettext("Soliq toʻlovlari"), -outflows.pop("taxes", ZERO)),
        (
            "adjustments",
            gettext("Tuzatishlar (sanoq, boshlangʻich qoldiq)"),
            inflows.pop("adjustments", ZERO) - outflows.pop("adjustments", ZERO),
        ),
    ]
    leftover = sum(inflows.values(), ZERO) - sum(outflows.values(), ZERO)
    if leftover:
        steps.append(("other", gettext("Boshqa harakatlar"), leftover))
    transfers = _d(flow["transfers"]["in"]) - _d(flow["transfers"]["out"])
    if transfers:
        steps.append(("transfers", gettext("Oʻtkazmalar (filiallar orasida)"), transfers))
    operating_profit = _d(pnl["operating_profit"])
    change = _d(flow["closing"]) - _d(flow["opening"])
    total = operating_profit + sum((value for _key, _label, value in steps), ZERO)
    return {
        "operating_profit": _m(operating_profit),
        "steps": [{"id": key, "label": label, "value": _m(value)} for key, label, value in steps],
        "money_change": _m(change),
        "check": {"ok": total == change, "difference": _m(change - total)},
    }


def build(*, organization_id: Any, year: int, month: int, branch_id: Any = None) -> dict[str, Any]:
    """Paketning to'liq JSON'i — o'zgarmas tuzilma, 16 bo'lim."""
    from apps.intelligence import control
    from apps.reports import money

    org, branch = organization_id, branch_id
    start, end = _bounds(year, month)
    revenue = _revenue(org, branch, year, month)
    summary = revenue.pop("_summary")
    due = _d(summary["invoiced"]["amount_due"])

    pnl_history = []
    for back in range(4):
        y, m = _shift(year, month, back)
        data = money.profit_and_loss(organization_id=org, year=y, month=m, branch_id=branch)
        data["_roster"] = summary["roster"] if back == 0 else 0
        pnl_history.append(data)
    pnl = pnl_history[0]
    flow = money.cash_flow(organization_id=org, year=year, month=month, branch_id=branch)
    position_end = money.position(organization_id=org, as_of=end, branch_id=branch)
    position_prev = money.position(
        organization_id=org, as_of=start - timedelta(days=1), branch_id=branch
    )
    checks = control.checks(organization_id=org, year=year, month=month, branch_id=branch)
    attention = control.attention(organization_id=org, year=year, month=month, branch_id=branch)
    completeness = money.data_completeness(
        organization_id=org, year=year, month=month, branch_id=branch
    )
    children = _children(org, branch, year, month)
    receipts = _receipts(org, branch, year, month, due)
    payroll = _payroll(org, branch, year, month, due)

    profits = [_d(data["operating_profit"]) for data in pnl_history]
    revenues = [_d(data["revenue"]["total"]) for data in pnl_history]
    money_end = sum(
        (_d(position_end["assets"][key]) for key in ("cash", "bank", "in_transit")), ZERO
    )
    money_start = sum(
        (_d(position_prev["assets"][key]) for key in ("cash", "bank", "in_transit")), ZERO
    )
    figures = [
        {
            "id": "revenue",
            "label": gettext("Daromad"),
            **_compare(revenues[0], revenues[1], revenues[1:]),
        },
        {
            "id": "collected",
            "label": gettext("Oy uchun yigʻilgan"),
            **_compare(_d(summary["collected_for_month"]["total"]), ZERO, []),
        },
        {"id": "debt", "label": gettext("Qarz"), **_compare(_d(summary["outstanding"]), ZERO, [])},
        {
            "id": "operating_profit",
            "label": gettext("Operatsion foyda"),
            **_compare(profits[0], profits[1], profits[1:]),
        },
        {
            "id": "money",
            "label": gettext("Pul (kassa + bank + yoʻlda)"),
            **_compare(money_end, money_start, []),
        },
        {"id": "children", "label": gettext("Bolalar"), "value": str(children["movement"]["end"])},
    ]
    facts = [
        gettext("Daromad {value} soʻm, oʻtgan oyga nisbatan {delta} soʻm.").format(
            value=_m(revenues[0]), delta=_m(revenues[0] - revenues[1])
        ),
        gettext("Yigʻish darajasi {rate}%.").format(rate=revenue["kpi"]["collection_rate"] or "—"),
        gettext("Operatsion foyda {value} soʻm.").format(value=_m(profits[0])),
        gettext("{failing} ta tekshiruv qizil, {attention} ta Diqqat.").format(
            failing=sum(1 for row in checks if row["status"] == "fail"), attention=len(attention)
        ),
    ]
    position_section = {"end": position_end, "previous": position_prev}
    sections = {
        "summary": {
            "figures": figures,
            "facts": facts,
            "checks": {
                status: sum(1 for row in checks if row["status"] == status)
                for status in ("ok", "fail", "na")
            },
            "completeness": completeness,
            "attention_top": attention[:5],
        },
        "children": children,
        "revenue": revenue,
        "receipts": receipts,
        "debts": _debts(org, branch, year, month, summary),
        "expenses": _expenses(org, branch, year, month, pnl_history),
        "payroll": payroll,
        "cash_bank": _cash_bank(org, branch, year, month),
        "pnl": {
            "current": {k: v for k, v in pnl.items() if not k.startswith("_")},
            "previous": {k: v for k, v in pnl_history[1].items() if not k.startswith("_")},
            "avg3_operating_profit": _m(sum(profits[1:], ZERO) / 3),
        },
        "profit_vs_cash": _profit_vs_cash(pnl, flow),
        "position": position_section,
        "plan": {"available": False, "note": gettext("Reja va prognoz — Bosqich 13.7.")},
        "taxes": {
            "liability_end": position_end["liabilities"]["taxes"],
            "paid_in_month": flow["outflows"].get("taxes", "0.00"),
            "payroll_withheld": payroll["withheld_taxes"],
            "social_tax": payroll["social_tax"],
        },
        "checks": {"items": checks},
        "attention": {"items": attention},
        "appendix": _appendix(org, branch, start, end),
    }
    titles = {
        "summary": gettext("Xulosa"),
        "children": gettext("Bolalar va bandlik"),
        "revenue": gettext("Daromad"),
        "receipts": gettext("Tushum (pul)"),
        "debts": gettext("Qarzlar va avanslar"),
        "expenses": gettext("Xarajatlar"),
        "payroll": gettext("Ish haqi"),
        "cash_bank": gettext("Kassa va bank"),
        "pnl": gettext("Foyda-zarar"),
        "profit_vs_cash": gettext("Pul oqimi: foyda ≠ pul"),
        "position": gettext("Holat"),
        "plan": gettext("Reja va prognoz"),
        "taxes": gettext("Soliq va majburiy toʻlovlar"),
        "checks": gettext("Nazorat tekshiruvlari"),
        "attention": gettext("Diqqat"),
        "appendix": gettext("Ilovalar"),
    }
    return {
        "period": f"{year}-{month:02d}",
        "branch_id": str(branch) if branch else None,
        "sections": [{"key": key, "title": titles[key], **sections[key]} for key in SECTION_KEYS],
    }


def _appendix(org: Any, branch: Any, start: date, end: date) -> dict[str, Any]:
    from apps.cash.models import CashMovement
    from apps.expenses.models import Expense
    from apps.finance.models import Discount, Payment

    payments = _scoped(Payment.objects, org, branch).filter(
        paid_at__date__gte=start, paid_at__date__lte=end
    )
    expenses = _scoped(Expense.objects, org, branch).filter(
        expense_date__gte=start, expense_date__lte=end
    )
    transfers = _scoped(CashMovement.objects, org, branch).filter(
        source_type="transfer",
        direction="out",
        occurred_at__date__gte=start,
        occurred_at__date__lte=end,
    )
    benefits = _scoped(Discount.objects, org, branch).filter(
        created_at__date__gte=start, created_at__date__lte=end
    )
    return {
        "counts": {
            "payments": payments.count(),
            "expenses": expenses.count(),
            "transfers": transfers.count(),
            "benefits": benefits.count(),
        },
        "documents": {
            "expenses_with_receipt": expenses.exclude(receipt="").count(),
            "payments_with_reference": payments.exclude(reference="").count(),
        },
    }


# --- Manba yozuvlar (drill-down, test 19) ---


def source_rows(
    *, organization_id: Any, year: int, month: int, key: str, branch_id: Any = None
) -> list[dict[str, Any]]:
    from django.utils import timezone

    from apps.finance.models import Invoice, InvoiceLine, PaymentAllocation

    org, branch = organization_id, branch_id
    invoices = (
        _scoped(Invoice.objects, org, branch)
        .filter(period_year=year, period_month=month)
        .exclude(status="cancelled")
    )
    if key == "invoices:due":
        return [
            {
                "id": str(row.id),
                "child": row.child.full_name,
                "number": row.number,
                "amount": _m(row.amount_due),
            }
            for row in invoices.select_related("child")
        ]
    if key == "invoices:open":
        return [
            {
                "id": str(row.id),
                "child": row.child.full_name,
                "number": row.number,
                "amount": _m(row.amount_due - row.amount_paid),
            }
            for row in invoices.select_related("child")
            if row.amount_due > row.amount_paid
        ]
    if key == "allocations:collected":
        return [
            {
                "payment_id": str(row.payment_id),
                "child": row.payment.child.full_name,
                "method": row.payment.method,
                "date": timezone.localtime(row.payment.paid_at).date().isoformat(),
                "amount": _m(row.amount),
            }
            for row in PaymentAllocation.objects.filter(
                invoice__in=invoices, released_at__isnull=True
            )
            .select_related("payment__child")
            .order_by("payment__paid_at")
        ]
    if key in ("lines:benefit", "lines:recalculation"):
        lines = InvoiceLine.objects.filter(invoice__in=invoices).select_related("invoice__child")
        lines = (
            lines.filter(kind="benefit")
            if key == "lines:benefit"
            else lines.exclude(kind__in=["base", "benefit"])
        )
        return [
            {
                "child": row.invoice.child.full_name,
                "kind": row.kind,
                "description": row.description,
                "amount": _m(row.line_total),
            }
            for row in lines
        ]
    return []


# --- O'zgarmas nusxa va farq ---


def _canonical(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def checksum(data: dict[str, Any]) -> str:
    """Nazorat summasi — tuzilmaning kanonik JSON'idan (SHA-256)."""
    return hashlib.sha256(_canonical(data).encode()).hexdigest()


def _leaves(node: Any, path: str = "") -> dict[str, str]:
    """Raqamli barglar: `revenue.chain[collected].value` → "123.00"."""
    found: dict[str, str] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            found.update(_leaves(value, f"{path}.{key}" if path else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            label = index
            if isinstance(value, dict):
                label = next(
                    (
                        value[k]
                        for k in ("key", "id", "rule", "category", "method", "account", "child")
                        if k in value
                    ),
                    index,
                )
            found.update(_leaves(value, f"{path}[{label}]"))
    elif isinstance(node, (int, float, Decimal)) and not isinstance(node, bool):
        found[path] = str(node)
    elif isinstance(node, str):
        try:
            Decimal(node)
        except ArithmeticError:
            return found
        if node.replace(".", "", 1).replace("-", "", 1).isdigit():
            found[path] = node
    return found


def diff(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Raqamlar darajasidagi farq — ikki versiya orasida (test 16)."""
    old, new = _leaves(before), _leaves(after)
    changes = []
    for path in sorted(set(old) | set(new)):
        a, b = old.get(path), new.get(path)
        if a == b:
            continue
        try:
            delta = _m(_d(b) - _d(a))
        except ArithmeticError:
            delta = None
        changes.append({"path": path, "before": a, "after": b, "delta": delta})
    return changes
