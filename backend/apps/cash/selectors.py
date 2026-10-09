"""
Kassa o'qishlari (docs/03 §13a).

Bu yerda faqat O'QISH bor. Eng muhim qoida: **qoldiq hech qachon
saqlanmaydi** — u har safar `cash_movement` dan hisoblanadi. Keshlangan
qoldiq bir marta noto'g'ri bo'lsa, uni hech kim sezmay yillab
ko'rsatilaverardi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from apps.cash.models import CashAccount, CashMovement, MovementDirection

__all__ = ["account_balance", "account_balances", "total_balance", "movement_totals"]

ZERO = Value(Decimal("0"), output_field=DecimalField(max_digits=16, decimal_places=2))


def _signed_sum() -> Any:
    return Coalesce(Sum("amount", filter=Q(direction=MovementDirection.IN)), ZERO) - Coalesce(
        Sum("amount", filter=Q(direction=MovementDirection.OUT)), ZERO
    )


def account_balances(
    *,
    organization_id: Any,
    branch_id: Any = None,
    up_to: date | None = None,
) -> list[dict[str, Any]]:
    """Har bir qop bo'yicha qoldiq — nomi va turi bilan."""
    accounts = CashAccount.objects.filter(organization_id=organization_id, is_active=True)
    if branch_id:
        accounts = accounts.filter(branch_id=branch_id)

    movements = CashMovement.objects.filter(organization_id=organization_id)
    if branch_id:
        movements = movements.filter(branch_id=branch_id)
    if up_to is not None:
        movements = movements.filter(occurred_at__date__lte=up_to)

    totals = {
        row["cash_account"]: row["balance"]
        for row in movements.values("cash_account").annotate(balance=_signed_sum())
    }

    return [
        {
            "id": str(account.id),
            "name": account.name,
            "kind": account.kind,
            "branch_id": str(account.branch_id),
            "balance": f"{totals.get(account.id, Decimal('0')):.2f}",
        }
        for account in accounts.order_by("kind", "name")
    ]


def account_balance(*, account_id: Any) -> Decimal:
    """
    Bitta qopdagi pul — Σ kirim − Σ chiqim.

    `account_balances()` dan farqi: bu yerda bitta qop soʻraladi va
    javob — Decimal. U chiqim yozishdan OLDIN tekshirish uchun kerak
    (ADR-29), shuning uchun u imkon qadar arzon boʻlishi kerak.
    """
    return CashMovement.objects.filter(cash_account_id=account_id).aggregate(total=_signed_sum())[
        "total"
    ] or Decimal("0")


def total_balance(*, organization_id: Any, branch_id: Any = None) -> Decimal:
    """Barcha qoplardagi pul — bitta raqam."""
    movements = CashMovement.objects.filter(organization_id=organization_id)
    if branch_id:
        movements = movements.filter(branch_id=branch_id)
    return movements.aggregate(total=_signed_sum())["total"] or Decimal("0")


def movement_totals(
    *,
    organization_id: Any,
    date_from: date,
    date_to: date,
    branch_id: Any = None,
) -> list[dict[str, Any]]:
    """
    Davr ichida har bir qopga qancha kirgani va undan qancha chiqqani.

    "Sof foyda qaysi puldan yig'ilgan?" degan savolga shu javob beradi
    (docs/04 §14.2).
    """
    movements = CashMovement.objects.filter(
        organization_id=organization_id,
        occurred_at__date__gte=date_from,
        occurred_at__date__lte=date_to,
    )
    if branch_id:
        movements = movements.filter(branch_id=branch_id)

    rows = movements.values("cash_account", "cash_account__name", "cash_account__kind").annotate(
        inflow=Coalesce(Sum("amount", filter=Q(direction=MovementDirection.IN)), ZERO),
        outflow=Coalesce(Sum("amount", filter=Q(direction=MovementDirection.OUT)), ZERO),
    )
    return [
        {
            "id": str(row["cash_account"]),
            "name": row["cash_account__name"],
            "kind": row["cash_account__kind"],
            "inflow": f"{row['inflow']:.2f}",
            "outflow": f"{row['outflow']:.2f}",
            "net": f"{row['inflow'] - row['outflow']:.2f}",
        }
        for row in sorted(rows, key=lambda r: (r["cash_account__kind"], r["cash_account__name"]))
    ]
