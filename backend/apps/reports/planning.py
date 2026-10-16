"""
Reja va fakt, ko'rsatkichlar, 12 oylik trend, yillik hisobot (Bosqich 13.7,
brif §5.3-12, §6).

Fakt hech qachon shu yerda qayta hisoblanmaydi: `money.profit_and_loss`,
`money.cash_flow`, `money.position` va oylik paket (`pack.build`) — o'sha
raqamlar, o'sha formulalar. Reja esa faqat kiritilgan son.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.db.models import Q, Sum
from django.utils.translation import gettext, gettext_lazy

from apps.core.exceptions import BusinessRuleViolation
from apps.reports.models import BudgetKind, BudgetLine

__all__ = [
    "KPI_DEFINITIONS",
    "annual",
    "budget",
    "copy_budget",
    "kpis",
    "save_budget",
    "trends",
]

ZERO = Decimal("0")


def _m(value: Any) -> str:
    return f"{Decimal(value or 0).quantize(Decimal('0.01')):.2f}"


def _pct(part: Decimal, whole: Decimal) -> str | None:
    return f"{part * 100 / whole:.1f}" if whole else None


def _shift(year: int, month: int, by: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + by
    return index // 12, index % 12 + 1


def _month_end(year: int, month: int) -> date:
    year2, month2 = _shift(year, month, 1)
    return date(year2, month2, 1) - timedelta(days=1)


def _lines(organization_id: Any, branch_id: Any, year: int, month: int) -> Any:
    return BudgetLine.objects.filter(
        organization_id=organization_id, branch_id=branch_id, period_year=year, period_month=month
    ).select_related("category")


# --- Reja va fakt ---


def _category_actual(
    organization_id: Any, branch_id: Any, year: int, month: int, category_id: Any
) -> Decimal:
    from apps.reports.money import _expenses_for

    return (
        _expenses_for(organization_id, branch_id)
        .filter(p_year=year, p_month=month, is_capex=False)
        .filter(Q(category_id=category_id) | Q(category__parent_id=category_id))
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )


def budget(*, organization_id: Any, year: int, month: int, branch_id: Any = None) -> dict[str, Any]:
    """Reja qatorlari fakt bilan yonma-yon; fakt `profit_and_loss` dan."""
    from apps.reports import money

    pnl = money.profit_and_loss(
        organization_id=organization_id, year=year, month=month, branch_id=branch_id
    )
    plans = {
        (row.kind, row.category_id): row for row in _lines(organization_id, branch_id, year, month)
    }

    def row(kind: str, label: str, plan: Decimal, actual: Decimal, **extra: Any) -> dict[str, Any]:
        difference = actual - plan
        return {
            "kind": kind,
            "label": label,
            "plan": _m(plan),
            "actual": _m(actual),
            "difference": _m(difference),
            "percent": _pct(actual, plan),
            **extra,
        }

    def planned(kind: str, category: Any = None) -> Decimal:
        line = plans.get((kind, category))
        return line.amount if line else ZERO

    rows = [
        row(
            BudgetKind.REVENUE,
            gettext("Daromad (toʻlovlar)"),
            planned(BudgetKind.REVENUE),
            Decimal(pnl["revenue"]["tuition"]),
        ),
        row(
            BudgetKind.OTHER_INCOME,
            gettext("Boshqa daromad"),
            planned(BudgetKind.OTHER_INCOME),
            Decimal(pnl["revenue"]["other"]),
        ),
        row(
            BudgetKind.PAYROLL,
            gettext("Ish haqi (ijtimoiy soliq bilan)"),
            planned(BudgetKind.PAYROLL),
            Decimal(pnl["payroll"]),
        ),
    ]
    category_rows = []
    for (kind, category_id), line in plans.items():
        if kind != BudgetKind.CATEGORY:
            continue
        category_rows.append(
            row(
                BudgetKind.CATEGORY,
                line.category.name if line.category else "—",
                line.amount,
                _category_actual(organization_id, branch_id, year, month, category_id),
                category_id=str(category_id),
            )
        )
    category_rows.sort(key=lambda item: item["label"])
    rows += category_rows

    planned_expenses = sum(
        (Decimal(item["plan"]) for item in rows if item["kind"] in ("payroll", "category")), ZERO
    )
    planned_income = Decimal(rows[0]["plan"]) + Decimal(rows[1]["plan"])
    actual_expenses = Decimal(pnl["operating_expenses"]) + Decimal(pnl["payroll"])
    return {
        "period": f"{year}-{month:02d}",
        "has_plan": bool(plans),
        "lines": rows,
        "totals": {
            "income": {"plan": _m(planned_income), "actual": pnl["revenue"]["total"]},
            "expenses": {"plan": _m(planned_expenses), "actual": _m(actual_expenses)},
            "result": {
                "plan": _m(planned_income - planned_expenses),
                "actual": _m(Decimal(pnl["revenue"]["total"]) - actual_expenses),
            },
        },
    }


def _amount(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise BusinessRuleViolation(
            gettext("Summa notoʻgʻri: {value}").format(value=value)
        ) from exc
    if amount < 0 or not amount.is_finite():
        raise BusinessRuleViolation(gettext("Reja summasi manfiy boʻlmaydi."))
    return amount.quantize(Decimal("0.01"))


def save_budget(
    *,
    organization: Any,
    year: int,
    month: int,
    branch_id: Any,
    lines: list[dict[str, Any]],
    user: Any,
) -> None:
    """Oyning rejasini butunlay almashtiradi. Begona toifa — `404` (RLS)."""
    from django.http import Http404

    from apps.expenses.models import ExpenseCategory

    rows: dict[tuple[str, Any], Decimal] = {}
    for item in lines:
        kind = str(item.get("kind") or "")
        if kind not in BudgetKind.values:
            raise BusinessRuleViolation(
                gettext("Reja qatori turi notoʻgʻri: {kind}").format(kind=kind)
            )
        category = None
        if kind == BudgetKind.CATEGORY:
            category = ExpenseCategory.objects.filter(pk=item.get("category_id")).first()
            if category is None:
                raise Http404
        rows[(kind, category.pk if category else None)] = _amount(item.get("amount"))
    with transaction.atomic():
        _lines(organization.id, branch_id, year, month).delete()
        BudgetLine.objects.bulk_create(
            [
                BudgetLine(
                    organization=organization,
                    branch_id=branch_id,
                    period_year=year,
                    period_month=month,
                    kind=kind,
                    category_id=category_id,
                    amount=amount,
                    updated_by=user,
                )
                for (kind, category_id), amount in rows.items()
            ]
        )


def copy_budget(
    *,
    organization: Any,
    branch_id: Any,
    source: tuple[int, int],
    target: tuple[int, int],
    user: Any,
) -> int:
    lines = list(_lines(organization.id, branch_id, *source))
    if not lines:
        raise BusinessRuleViolation(gettext("Koʻchiriladigan oyda reja yoʻq."))
    save_budget(
        organization=organization,
        year=target[0],
        month=target[1],
        branch_id=branch_id,
        lines=[
            {"kind": line.kind, "category_id": line.category_id, "amount": line.amount}
            for line in lines
        ],
        user=user,
    )
    return len(lines)


# --- Ko'rsatkichlar (brif §6: (i) belgisidagi matn) ---

KPI_DEFINITIONS: dict[str, tuple[Any, Any]] = {
    "occupancy": (
        gettext_lazy("Bandlik"),
        gettext_lazy("Faol bolalar ÷ guruhlar sigʻimi."),
    ),
    "average_per_child": (
        gettext_lazy("Bir boladan oʻrtacha daromad"),
        gettext_lazy("Toʻlanishi kerak boʻlgan summa ÷ faol bolalar."),
    ),
    "benefit_share": (
        gettext_lazy("Imtiyoz ulushi"),
        gettext_lazy("(Toʻliq narxdagi summa − imtiyozdan keyingi summa) ÷ toʻliq narxdagi summa."),
    ),
    "collection_rate": (
        gettext_lazy("Yigʻish darajasi"),
        gettext_lazy("Oy uchun yigʻilgan ÷ toʻlanishi kerak boʻlgan summa."),
    ),
    "payroll_share": (
        gettext_lazy("Ish haqi ulushi"),
        gettext_lazy("Shu oy ish haqi xarajati (ijtimoiy soliq bilan) ÷ daromad."),
    ),
    "food_per_child_day": (
        gettext_lazy("Bir bola-kunga oziq-ovqat"),
        gettext_lazy("Oziq-ovqat xarajati ÷ davomat boʻyicha bola-kunlar."),
    ),
    "operating_margin": (
        gettext_lazy("Operatsion marja"),
        gettext_lazy("Operatsion foyda ÷ daromad."),
    ),
    "break_even_children": (
        gettext_lazy("Zararsizlik nuqtasi (bola soni)"),
        gettext_lazy(
            "Doimiy xarajatlar ÷ (bir boladan oʻrtacha daromad − bir boladagi oʻzgaruvchan "
            "xarajat). Doimiy — ish haqi va oziq-ovqatdan boshqa xarajatlar; oʻzgaruvchan — "
            "oziq-ovqat."
        ),
    ),
    "churn_rate": (
        gettext_lazy("Ketish darajasi"),
        gettext_lazy("Oy davomida ketganlar ÷ oy boshidagi bolalar."),
    ),
    "average_stay_months": (
        gettext_lazy("Oʻrtacha qolish muddati (oy)"),
        gettext_lazy(
            "Hamma qabullar boʻyicha: ketganlar — kelgan kunidan ketgan kunigacha, "
            "qolganlar — oy oxirigacha."
        ),
    ),
    "marketing_per_new_child": (
        gettext_lazy("Bir yangi bolaga marketing xarajati"),
        gettext_lazy("Marketing toifasidagi xarajat ÷ oy davomida kelgan bolalar."),
    ),
    "safe_withdrawal": (
        gettext_lazy("Xavfsiz olish summasi"),
        gettext_lazy(
            "Kassa + bank + yoʻldagi pul − kelgusi 30 kun majburiyatlari − zaxira. "
            "Zaxira sozlanadi, sukut — 0,5 oylik ish haqi fondi."
        ),
    ),
}


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    return next(section for section in data["sections"] if section["key"] == key)


def _average_stay(organization_id: Any, branch_id: Any, as_of: date) -> str | None:
    from apps.children.models import Enrollment

    rows = Enrollment.objects.filter(organization_id=organization_id, start_date__lte=as_of)
    if branch_id:
        rows = rows.filter(branch_id=branch_id)
    spans = [
        ((min(end or as_of, as_of) - start).days) / Decimal("30.4375")
        for start, end in rows.values_list("start_date", "end_date")
    ]
    if not spans:
        return None
    return f"{sum(spans, ZERO) / len(spans):.1f}"


def _marketing(organization_id: Any, branch_id: Any, year: int, month: int) -> Decimal:
    from apps.reports.money import _expenses_for
    from apps.settings_app.services import get_setting

    name = str(get_setting(key="report.marketing_category", branch=branch_id) or "").strip()
    if not name:
        return ZERO
    return (
        _expenses_for(organization_id, branch_id)
        .filter(p_year=year, p_month=month)
        .filter(Q(category__name__iexact=name) | Q(category__parent__name__iexact=name))
        .aggregate(total=Sum("amount"))["total"]
        or ZERO
    )


def kpis(*, organization_id: Any, year: int, month: int, branch_id: Any = None) -> dict[str, Any]:
    """Oylik paketdagi o'sha raqamlar + ta'riflari."""
    from apps.reports import forecast, pack
    from apps.reports.network import _occupancy

    data = pack.build(organization_id=organization_id, year=year, month=month, branch_id=branch_id)
    revenue = _section(data, "revenue")
    children = _section(data, "children")
    expenses = _section(data, "expenses")
    pnl = _section(data, "pnl")["current"]

    roster = Decimal(children["movement"]["end"])
    average = Decimal(revenue["kpi"]["average_per_child"] or 0)
    food_total = sum(
        (
            Decimal(row["total"])
            for row in pnl.get("expenses_by_category", [])
            if str(row["category"]).strip().lower() == _food_name(branch_id).lower()
        ),
        ZERO,
    )
    fixed = Decimal(pnl["operating_expenses"]) + Decimal(pnl["payroll"]) - food_total
    variable = food_total / roster if roster else ZERO
    margin = average - variable
    break_even = f"{(fixed / margin):.1f}" if margin > 0 else None
    arrived = Decimal(children["movement"]["arrived"])
    marketing = _marketing(organization_id, branch_id, year, month)
    safe = forecast.forecast(
        organization_id=organization_id, as_of=_month_end(year, month), branch_id=branch_id
    )["safe_withdrawal"]

    values: dict[str, tuple[Any, str]] = {
        "occupancy": (_occupancy(children), "%"),
        "average_per_child": (revenue["kpi"]["average_per_child"], "som"),
        "benefit_share": (revenue["kpi"]["benefit_share"], "%"),
        "collection_rate": (revenue["kpi"]["collection_rate"], "%"),
        "payroll_share": (_section(data, "payroll")["share_of_revenue"], "%"),
        "food_per_child_day": (expenses["food_per_child_day"], "som"),
        "operating_margin": (pnl["margin"], "%"),
        "break_even_children": (break_even, "children"),
        "churn_rate": (children["churn_rate"], "%"),
        "average_stay_months": (
            _average_stay(organization_id, branch_id, _month_end(year, month)),
            "months",
        ),
        "marketing_per_new_child": (_m(marketing / arrived) if arrived else None, "som"),
        "safe_withdrawal": (safe["amount"], "som"),
    }
    return {
        "period": f"{year}-{month:02d}",
        "items": [
            {
                "id": key,
                "title": str(KPI_DEFINITIONS[key][0]),
                "definition": str(KPI_DEFINITIONS[key][1]),
                "value": value,
                "unit": unit,
            }
            for key, (value, unit) in values.items()
        ],
    }


def _food_name(branch_id: Any) -> str:
    from apps.settings_app.services import get_setting

    return str(get_setting(key="report.food_category", branch=branch_id) or "").strip()


# --- 12 oylik trend ---


def _month_row(organization_id: Any, branch_id: Any, year: int, month: int) -> dict[str, Any]:
    from apps.finance.models import Invoice, InvoiceStatus
    from apps.reports import money

    pnl = money.profit_and_loss(
        organization_id=organization_id, year=year, month=month, branch_id=branch_id
    )
    flow = money.cash_flow(
        organization_id=organization_id, year=year, month=month, branch_id=branch_id
    )
    position = money.position(
        organization_id=organization_id, as_of=_month_end(year, month), branch_id=branch_id
    )
    invoices = Invoice.objects.filter(
        organization_id=organization_id, period_year=year, period_month=month
    ).exclude(status=InvoiceStatus.CANCELLED)
    if branch_id:
        invoices = invoices.filter(branch_id=branch_id)
    totals = invoices.aggregate(due=Sum("amount_due"), paid=Sum("amount_paid"))
    due = totals["due"] or ZERO
    return {
        "period": f"{year}-{month:02d}",
        "revenue": pnl["revenue"]["total"],
        "receipts": flow["inflows"]["tuition"],
        "operating_expenses": pnl["operating_expenses"],
        "payroll": pnl["payroll"],
        "operating_profit": pnl["operating_profit"],
        "margin": pnl["margin"],
        "collection_rate": _pct(totals["paid"] or ZERO, due),
        "invoices": invoices.count(),
        "money_end": _m(
            sum(
                (Decimal(position["assets"][key]) for key in ("cash", "bank", "in_transit")),
                ZERO,
            )
        ),
        "capex": pnl["capex"],
        "owner_draws": pnl["owner_draws"],
    }


def trends(*, organization_id: Any, year: int, month: int, branch_id: Any = None) -> dict[str, Any]:
    """Shu oy bilan tugaydigan 12 oy — eng eskisi birinchi."""
    months = [_shift(year, month, -back) for back in range(11, -1, -1)]
    return {"months": [_month_row(organization_id, branch_id, y, m) for y, m in months]}


# --- Yillik hisobot ---


def annual(*, organization_id: Any, year: int, branch_id: Any = None) -> dict[str, Any]:
    """12 oy yig'indisi — pack bilan bir xil tuzilma: PDF/Excel shu JSON'dan."""
    from apps.reports import money

    rows = [_month_row(organization_id, branch_id, year, month) for month in range(1, 13)]
    pnls = [
        money.profit_and_loss(
            organization_id=organization_id, year=year, month=m, branch_id=branch_id
        )
        for m in range(1, 13)
    ]
    flows = [
        money.cash_flow(organization_id=organization_id, year=year, month=m, branch_id=branch_id)
        for m in range(1, 13)
    ]

    def total(values: list[Any]) -> str:
        return _m(sum((Decimal(value) for value in values), ZERO))

    revenue = total([pnl["revenue"]["total"] for pnl in pnls])
    profit = total([pnl["operating_profit"] for pnl in pnls])
    categories: dict[str, Decimal] = {}
    for pnl in pnls:
        for item in pnl["expenses_by_category"]:
            categories[item["category"]] = categories.get(item["category"], ZERO) + Decimal(
                item["total"]
            )
    inflow_keys = sorted({key for flow in flows for key in flow["inflows"] if key != "total"})
    outflow_keys = sorted({key for flow in flows for key in flow["outflows"] if key != "total"})
    sections = [
        {
            "key": "summary",
            "title": gettext("Xulosa"),
            "revenue": revenue,
            "operating_profit": profit,
            "margin": _pct(Decimal(profit), Decimal(revenue)),
            "money_start": flows[0]["opening"],
            "money_end": flows[-1]["closing"],
        },
        {
            "key": "pnl",
            "title": gettext("Foyda-zarar (yil)"),
            "total": {
                "revenue": revenue,
                "tuition": total([pnl["revenue"]["tuition"] for pnl in pnls]),
                "other_income": total([pnl["revenue"]["other"] for pnl in pnls]),
                "operating_expenses": total([pnl["operating_expenses"] for pnl in pnls]),
                "payroll": total([pnl["payroll"] for pnl in pnls]),
                "amortization": total([pnl["amortization"] for pnl in pnls]),
                "operating_profit": profit,
                "capex": total([pnl["capex"] for pnl in pnls]),
                "owner_draws": total([pnl["owner_draws"] for pnl in pnls]),
            },
        },
        {"key": "months", "title": gettext("Oylar boʻyicha"), "rows": rows},
        {
            "key": "expenses",
            "title": gettext("Xarajatlar toifalar boʻyicha"),
            "by_category": [
                {"category": name, "total": _m(amount)}
                for name, amount in sorted(categories.items(), key=lambda pair: -pair[1])
            ],
        },
        {
            "key": "cash_flow",
            "title": gettext("Pul oqimi (yil)"),
            "opening": flows[0]["opening"],
            "inflows": {
                key: total([f["inflows"].get(key, "0") for f in flows]) for key in inflow_keys
            },
            "outflows": {
                key: total([f["outflows"].get(key, "0") for f in flows]) for key in outflow_keys
            },
            "closing": flows[-1]["closing"],
        },
        {
            "key": "position",
            "title": gettext("Holat — yil oxiri"),
            **money.position(
                organization_id=organization_id, as_of=date(year, 12, 31), branch_id=branch_id
            ),
        },
    ]
    return {
        "period": str(year),
        "branch_id": str(branch_id) if branch_id else None,
        "sections": sections,
    }
