"""Chiqim tasdiqlash oqimi (docs/03 §16.2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.expenses.models import Expense, ExpenseStatus

__all__ = ["approve_expense", "reject_expense", "mark_expense_paid", "expense_summary"]


def _assert_pending(expense: Expense, action: str) -> None:
    if expense.status != ExpenseStatus.PENDING:
        raise BusinessRuleViolation(
            gettext("Chiqim '{status}' holatida — {action} mumkin emas.").format(
                status=expense.get_status_display(), action=action
            )
        )


@transaction.atomic
def approve_expense(*, expense: Expense, approved_by: Any, note: str = "") -> Expense:
    _assert_pending(expense, "tasdiqlash")
    expense.status = ExpenseStatus.APPROVED
    expense.approved_by = approved_by
    expense.decided_at = timezone.now()
    expense.decision_note = note[:255]
    expense.save(
        update_fields=["status", "approved_by", "decided_at", "decision_note", "updated_at"]
    )
    return expense


@transaction.atomic
def reject_expense(*, expense: Expense, approved_by: Any, note: str = "") -> Expense:
    """
    Rad etilgan chiqim O'CHIRILMAYDI.

    U nima so'ralgani va nega rad etilgani haqidagi yozuv bo'lib qoladi —
    aks holda "men buni so'ragan edim" degan bahsga javob bo'lmasdi.
    """
    _assert_pending(expense, "rad etish")
    expense.status = ExpenseStatus.REJECTED
    expense.approved_by = approved_by
    expense.decided_at = timezone.now()
    expense.decision_note = note[:255]
    expense.save(
        update_fields=["status", "approved_by", "decided_at", "decision_note", "updated_at"]
    )
    return expense


@transaction.atomic
def mark_expense_paid(*, expense: Expense) -> Expense:
    if expense.status != ExpenseStatus.APPROVED:
        raise BusinessRuleViolation(
            gettext("Faqat tasdiqlangan chiqimni to'langan deb belgilash mumkin.")
        )
    expense.status = ExpenseStatus.PAID
    expense.save(update_fields=["status", "updated_at"])
    return expense


def expense_summary(
    *, organization_id: Any, date_from: date, date_to: date, branch_id: Any = None
) -> dict[str, Any]:
    """
    Davr bo'yicha kategoriya kesimida yig'ma.

    Faqat `approved`/`paid` hisobga olinadi — kutilayotgan so'rov hali
    xarajat emas, va uni P&L ga qo'shish sarfni oshirib ko'rsatardi.
    """
    queryset = Expense.objects.filter(
        expense_date__gte=date_from,
        expense_date__lte=date_to,
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    rows = queryset.values("category__name").annotate(total=Sum("amount")).order_by("-total")
    total = queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total": str(total),
        "by_category": [
            {"category": row["category__name"], "total": str(row["total"])} for row in rows
        ],
    }
