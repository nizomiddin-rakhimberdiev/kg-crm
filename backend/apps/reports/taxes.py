"""
Soliq taqvimi (Bosqich 13.8, brif §9).

Majburiyat hujjatlardan kelib chiqadi:

* oylik hisobi (yakunlangan) → JShDS, INPS, ijtimoiy soliq;
* egaga dividend → dividend solig'i (`MoneyOperation.tax_amount`);
* aylanma rejimida → oy daromadi × `tax.turnover_percent`.

Muddat — keyingi oyning `forecast.tax_day` sanasi (sukut 15). To'lanmaguncha
summa hujjatlar bilan yangilanadi; to'langanda `tax_payment` operatsiyasi
(haqiqiy pul harakati, invariant 12) bilan qotadi.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.reports.models import TaxKind, TaxObligation

__all__ = ["calendar_for", "pay", "status_of", "sync"]

ZERO = Decimal("0")

#: Majburiyat → `tax_payment` operatsiyasining subtipi.
SUBTYPE = {
    TaxKind.INCOME_TAX: "income_tax",
    TaxKind.PENSION: "pension",
    TaxKind.SOCIAL_TAX: "social_tax",
    TaxKind.DIVIDEND_TAX: "dividend_tax",
    TaxKind.TURNOVER_TAX: "turnover_tax",
}


def _setting(key: str, default: Any) -> Any:
    from apps.settings_app.services import get_setting

    value = get_setting(key=key)
    return default if value in (None, "") else value


def _due(year: int, month: int) -> date:
    year2, month2 = (year + 1, 1) if month == 12 else (year, month + 1)
    try:
        day = int(_setting("forecast.tax_day", 15))
    except (TypeError, ValueError):
        day = 15
    return date(year2, month2, min(max(day, 1), calendar.monthrange(year2, month2)[1]))


def _expected(organization_id: Any, year: int, month: int) -> dict[str, Decimal]:
    from apps.cash.models import MoneyOperation, OperationKind
    from apps.payroll.models import PayrollItem, PayrollStatus
    from apps.reports import money

    totals = PayrollItem.objects.filter(
        organization_id=organization_id,
        payroll_run__period_year=year,
        payroll_run__period_month=month,
        payroll_run__status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
    ).aggregate(income=Sum("tax_income"), pension=Sum("tax_pension"), social=Sum("tax_social"))
    dividend = (
        MoneyOperation.objects.filter(
            organization_id=organization_id,
            kind=OperationKind.OWNER_DRAW,
            occurred_on__year=year,
            occurred_on__month=month,
        ).aggregate(total=Sum("tax_amount"))["total"]
        or ZERO
    )
    expected: dict[str, Decimal] = {
        TaxKind.INCOME_TAX: totals["income"] or ZERO,
        TaxKind.PENSION: totals["pension"] or ZERO,
        TaxKind.SOCIAL_TAX: totals["social"] or ZERO,
        TaxKind.DIVIDEND_TAX: dividend,
    }
    if str(_setting("tax.regime", "")) == "turnover":
        percent = Decimal(str(_setting("tax.turnover_percent", 0)))
        revenue = Decimal(
            money.profit_and_loss(organization_id=organization_id, year=year, month=month)[
                "revenue"
            ]["total"]
        )
        expected[TaxKind.TURNOVER_TAX] = (revenue * percent / 100).quantize(Decimal("0.01"))
    return expected


def sync(*, organization: Any, year: int, month: int) -> list[TaxObligation]:
    """Oyning majburiyatlarini hujjatlardan yangilaydi; to'langani o'zgarmaydi."""
    rows = []
    for kind, amount in _expected(organization.id, year, month).items():
        existing = TaxObligation.objects.filter(
            kind=kind, period_year=year, period_month=month, branch__isnull=True
        ).first()
        if existing is None:
            if amount <= 0:
                continue
            existing = TaxObligation.objects.create(
                organization=organization,
                kind=kind,
                period_year=year,
                period_month=month,
                due_date=_due(year, month),
                amount=amount,
            )
        elif existing.operation_id is None and existing.amount != amount:
            existing.amount = amount
            existing.save(update_fields=["amount", "updated_at"])
        rows.append(existing)
    return rows


def status_of(obligation: TaxObligation, today: date | None = None) -> str:
    today = today or timezone.localdate()
    if obligation.operation_id is not None or obligation.amount <= 0:
        return "paid"
    if obligation.due_date < today:
        return "overdue"
    if (obligation.due_date - today).days <= 3:
        return "due"
    return "upcoming"


def calendar_for(*, organization: Any, year: int) -> dict[str, Any]:
    today = timezone.localdate()
    last = 12 if year < today.year else today.month if year == today.year else 0
    for month in range(1, last + 1):
        sync(organization=organization, year=year, month=month)
    rows = TaxObligation.objects.filter(period_year=year).select_related("operation")
    items = [
        {
            "id": str(row.id),
            "kind": row.kind,
            "title": str(TaxKind(row.kind).label),
            "period": f"{row.period_year}-{row.period_month:02d}",
            "due_date": row.due_date.isoformat(),
            "amount": f"{row.amount:.2f}",
            "status": status_of(row, today),
            "paid_on": row.operation.occurred_on.isoformat() if row.operation else None,
        }
        for row in rows
    ]
    unpaid = sum((Decimal(item["amount"]) for item in items if item["status"] != "paid"), ZERO)
    return {"year": year, "items": items, "unpaid": f"{unpaid:.2f}"}


@transaction.atomic
def pay(
    *,
    obligation: TaxObligation,
    account: Any,
    user: Any = None,
    paid_on: date | None = None,
    allow_negative: bool = False,
) -> TaxObligation:
    """To'lash — `tax_payment` operatsiyasi; ADR-29 qopda yo'q pulni chiqarmaydi."""
    from apps.cash import services as cash
    from apps.cash.models import OperationKind

    obligation = TaxObligation.objects.select_for_update().get(pk=obligation.pk)
    if obligation.operation_id is not None:
        raise BusinessRuleViolation(gettext("Bu soliq allaqachon toʻlangan."))
    if obligation.amount <= 0:
        raise BusinessRuleViolation(gettext("Toʻlanadigan summa yoʻq."))
    operation = cash.record_operation(
        kind=OperationKind.TAX_PAYMENT,
        subtype=SUBTYPE[TaxKind(obligation.kind)],
        account=account,
        amount=obligation.amount,
        occurred_on=paid_on or timezone.localdate(),
        reason=gettext("{title}, {period}").format(
            title=TaxKind(obligation.kind).label,
            period=f"{obligation.period_month:02d}.{obligation.period_year}",
        ),
        period=(obligation.period_year, obligation.period_month),
        created_by=user,
        allow_negative=allow_negative,
    )
    obligation.operation = operation
    obligation.save(update_fields=["operation", "updated_at"])
    return obligation
