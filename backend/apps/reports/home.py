"""
"Bog'cha moliyasi bugun" — egasining oltita doimiy savoli (Bosqich 13.4,
brif §5.1) va kunlik ko'rinish (§5.2).

Har karta: raqam, solishtirma, holat (ok / warning / critical) va bir
qatorlik izoh. Raqamlar o'zlari hisoblamaydi — `money.position`,
`money.profit_and_loss`, `control.checks/attention` va mavjud
selektorlardan o'qiydi, shuning uchun karta va hisobot hech qachon ikki
xil raqam ko'rsatmaydi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Q, Sum
from django.utils.translation import gettext

__all__ = ["home", "daily"]

ZERO = Decimal("0")


def _som(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", " ")


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _scoped(queryset: Any, organization_id: Any, branch_id: Any) -> Any:
    queryset = queryset.filter(organization_id=organization_id)
    return queryset.filter(branch_id=branch_id) if branch_id else queryset


def _card(key: str, title: str, value: Any, status: str, note: str, **extra: Any) -> dict:
    return {"key": key, "title": title, "value": value, "status": status, "note": note, **extra}


def home(*, organization_id: Any, day: date, branch_id: Any = None) -> dict[str, Any]:
    from apps.cash.selectors import custody
    from apps.children.models import Child, EnrollmentStatus, Group
    from apps.expenses.models import Expense, ExpenseStatus
    from apps.finance.models import Payment
    from apps.intelligence import control
    from apps.reports import money

    month_start = day.replace(day=1)
    previous_end = month_start - timedelta(days=1)
    previous_same = min(day.day, previous_end.day)
    position = money.position(organization_id=organization_id, as_of=day, branch_id=branch_id)
    assets = {key: Decimal(value) for key, value in position["assets"].items()}

    # 1. Pul qancha keldi va qayerda turibdi?
    payments = _scoped(Payment.objects, organization_id, branch_id).filter(reversed_at__isnull=True)
    today_in = payments.filter(paid_at__date=day).aggregate(total=Sum("amount"))["total"] or ZERO
    month_in = (
        payments.filter(paid_at__date__gte=month_start, paid_at__date__lte=day).aggregate(
            total=Sum("amount")
        )["total"]
        or ZERO
    )
    previous_in = (
        payments.filter(
            paid_at__date__gte=previous_end.replace(day=1),
            paid_at__date__lte=previous_end.replace(day=previous_same),
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    holding = assets["cash"] + assets["bank"] + assets["in_transit"]
    checks = control.checks(
        organization_id=organization_id, year=day.year, month=day.month, branch_id=branch_id
    )
    failing = {row["id"] for row in checks if row["status"] == "fail"}
    money_status = (
        "critical"
        if "negative_balance" in failing
        else "warning"
        if "transit_on_time" in failing
        else "ok"
    )
    cards = [
        _card(
            "money",
            gettext("Pul qancha keldi va qayerda?"),
            _money(holding),
            money_status,
            gettext("Bugun {today}, oy boshidan {month} soʻm keldi").format(
                today=_som(today_in), month=_som(month_in)
            ),
            detail={
                "cash": _money(assets["cash"]),
                "bank": _money(assets["bank"]),
                "in_transit": _money(assets["in_transit"]),
                "custody": custody(organization_id=organization_id, branch_id=branch_id)[:5],
            },
            compare={
                "previous_month_same_day": _money(previous_in),
                "this_month": _money(month_in),
            },
        )
    ]

    # 2. Kim qancha qarz?
    debts = assets["parent_debts"]
    debts_before = Decimal(
        money.position(organization_id=organization_id, as_of=previous_end, branch_id=branch_id)[
            "assets"
        ]["parent_debts"]
    )
    cards.append(
        _card(
            "debts",
            gettext("Kim qancha qarz?"),
            _money(debts),
            "warning" if debts > debts_before and debts > 0 else "ok",
            gettext("Oy boshida {before} soʻm edi").format(before=_som(debts_before)),
            compare={"month_start": _money(debts_before)},
        )
    )

    # 3. Pul qayerga ketdi?
    expenses = _scoped(Expense.objects, organization_id, branch_id).filter(
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID]
    )
    spent = expenses.filter(expense_date__gte=month_start, expense_date__lte=day)
    spent_total = spent.aggregate(total=Sum("amount"))["total"] or ZERO
    spent_before = (
        expenses.filter(
            expense_date__gte=previous_end.replace(day=1),
            expense_date__lte=previous_end.replace(day=previous_same),
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    top = [
        {"category": row["category__name"], "total": _money(row["total"])}
        for row in spent.values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:3]
    ]
    attention = control.attention(
        organization_id=organization_id, year=day.year, month=day.month, branch_id=branch_id
    )
    spending_flags = [
        item
        for item in attention
        if item["rule"]
        in {"expense_without_document", "split_expenses", "duplicate_expense", "category_jump"}
    ]
    cards.append(
        _card(
            "spending",
            gettext("Pul qayerga ketdi?"),
            _money(spent_total),
            "warning" if spending_flags else "ok",
            gettext("Oʻtgan oyning shu kunigacha {before} soʻm").format(before=_som(spent_before)),
            top=top,
            compare={"previous_month_same_day": _money(spent_before)},
        )
    )

    # 4. Foyda qancha?
    pnl = money.profit_and_loss(
        organization_id=organization_id, year=day.year, month=day.month, branch_id=branch_id
    )
    profit = Decimal(pnl["operating_profit"])
    # "...va qancha pul olsam bo'ladi?" — xavfsiz olish summasi (13.7).
    from apps.reports import forecast

    safe = forecast.forecast(organization_id=organization_id, as_of=day, branch_id=branch_id)[
        "safe_withdrawal"
    ]
    cards.append(
        _card(
            "profit",
            gettext("Foyda qancha va qancha olsa boʻladi?"),
            _money(profit),
            "critical" if profit < 0 else "ok",
            gettext("Marja {margin}%; xavfsiz olish {safe} soʻm").format(
                margin=pnl["margin"] or "—", safe=_som(Decimal(safe["amount"]))
            ),
            margin=pnl["margin"],
            safe_withdrawal=safe,
        )
    )

    # 5. Hammasi joyidami?
    cards.append(
        _card(
            "checks",
            gettext("Hammasi joyidami?"),
            len(failing),
            "critical" if failing else ("warning" if attention else "ok"),
            gettext("{failing} ta tekshiruv qizil, {attention} ta Diqqat").format(
                failing=len(failing), attention=len(attention)
            ),
            attention=len(attention),
        )
    )

    # 6. Bog'cha o'syaptimi?
    children = _scoped(Child.objects, organization_id, branch_id).filter(is_active=True)
    active = children.filter(enrollment_status=EnrollmentStatus.ACTIVE).count()
    capacity = (
        _scoped(Group.objects, organization_id, branch_id)
        .filter(is_active=True)
        .aggregate(total=Sum("capacity"))["total"]
        or 0
    )
    arrived = children.filter(enrolled_on__gte=month_start, enrolled_on__lte=day).count()
    left = (
        _scoped(Child.objects, organization_id, branch_id)
        .filter(
            enrollment_status__in=[EnrollmentStatus.WITHDRAWN, EnrollmentStatus.GRADUATED],
            status_changed_on__gte=month_start,
            status_changed_on__lte=day,
        )
        .count()
    )
    cards.append(
        _card(
            "growth",
            gettext("Bogʻcha oʻsyaptimi?"),
            active,
            "warning" if left > arrived else "ok",
            gettext("Bu oy {arrived} ta keldi, {left} ta ketdi").format(arrived=arrived, left=left),
            occupancy=round(active * 100 / capacity) if capacity else None,
            capacity=capacity,
        )
    )
    return {
        "date": day.isoformat(),
        "cards": cards,
        "all_clear": all(card["status"] == "ok" for card in cards),
    }


def daily(*, organization_id: Any, day: date, branch_id: Any = None) -> dict[str, Any]:
    """Kunlik ko'rinish (§5.2): tushum usullar bo'yicha, xarajat, sanoq, topshirish, Diqqat."""
    from apps.cash.models import CashCount, CashHandover
    from apps.expenses.models import Expense, ExpenseStatus
    from apps.finance.models import Invoice, Payment
    from apps.intelligence import control

    receipts = (
        _scoped(Payment.objects, organization_id, branch_id)
        .filter(reversed_at__isnull=True, paid_at__date=day)
        .values("method")
        .annotate(total=Sum("amount"))
        .order_by("method")
    )
    expenses = (
        _scoped(Expense.objects, organization_id, branch_id)
        .filter(status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID], expense_date=day)
        .select_related("category", "cash_account")
    )
    counts = _scoped(CashCount.objects, organization_id, branch_id).filter(counted_on=day)
    handovers = (
        _scoped(CashHandover.objects, organization_id, branch_id)
        .filter(created_at__date=day)
        .select_related("from_user", "to_user")
    )
    new_debts = (
        _scoped(Invoice.objects, organization_id, branch_id)
        .filter(issued_date=day)
        .exclude(Q(status="cancelled") | Q(status="paid"))
    )
    attention = [
        item
        for item in control.attention(
            organization_id=organization_id, year=day.year, month=day.month, branch_id=branch_id
        )
        if str(item.get("at") or "").startswith(day.isoformat())
    ]
    return {
        "date": day.isoformat(),
        "receipts": {
            "total": _money(sum((row["total"] for row in receipts), ZERO)),
            "by_method": [
                {"method": row["method"], "total": _money(row["total"])} for row in receipts
            ],
        },
        "expenses": {
            "total": _money(sum((row.amount for row in expenses), ZERO)),
            "items": [
                {
                    "id": str(row.id),
                    "category": row.category.name,
                    "amount": _money(row.amount),
                    "description": row.description,
                    "pot": row.cash_account.name if row.cash_account_id else None,
                    "has_receipt": bool(row.receipt),
                }
                for row in expenses
            ],
        },
        "counts": [
            {
                "pot": count.cash_account.name,
                "counted": _money(count.counted),
                "difference": _money(count.difference),
                "reason": count.reason,
            }
            for count in counts.select_related("cash_account")
        ],
        "handovers": [
            {
                "from": row.from_user.full_name,
                "to": row.to_user.full_name,
                "amount": _money(row.amount),
                "status": row.status,
            }
            for row in handovers
        ],
        "new_debts": {
            "count": new_debts.count(),
            "total": _money(sum((row.amount_due - row.amount_paid for row in new_debts), ZERO)),
        },
        "attention": attention,
    }
