"""Chiqim tasdiqlash oqimi (docs/03 §16.2)."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext

from apps.cash import services as cash
from apps.cash.models import MovementDirection, MovementSource
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
def approve_expense(
    *,
    expense: Expense,
    approved_by: Any,
    note: str = "",
    cash_account: Any = None,
) -> Expense:
    """
    Chiqimni tasdiqlaydi va pulni kassadan CHIQARADI (ADR-17).

    Nega pul aynan shu yerda chiqadi, `mark-paid` da emas: hisobotlar
    (`expense_summary`, foyda-zarar) boshidan beri `approved` ni ham
    xarajat deb sanaydi. Kassa esa faqat `paid` da kamaysa, ikkita
    ekran bir xil savolga ikki xil javob berardi — va ko'p bog'cha
    "to'landi" tugmasini umuman bosmaydi. Mijozning o'z so'zi ham shu
    edi: "chiqim kiritayotgan paytda qaysi puldan ketayotgani hisobga
    olinishi kerak".

    `mark_expense_paid()` shundan keyin faqat bayroqni o'zgartiradi —
    pul ikkinchi marta chiqmaydi.
    """
    _assert_pending(expense, "tasdiqlash")

    account = cash_account or expense.cash_account
    if account is None:
        # Qop ko'rsatilmasa naqd kassa: bog'chada odatiy hol, va
        # tasdiqlashni "sozlama to'liq emas" deb to'xtatish noto'g'ri
        # nosozlik bo'lardi.
        account = cash.account_for_method(branch=expense.branch, method="cash")
    if account.organization_id != expense.organization_id:
        raise BusinessRuleViolation(gettext("Kassa hisobi boshqa tashkilotga tegishli."))

    expense.status = ExpenseStatus.APPROVED
    expense.approved_by = approved_by
    expense.decided_at = timezone.now()
    expense.decision_note = note[:255]
    expense.cash_account = account
    expense.save(
        update_fields=[
            "status",
            "approved_by",
            "decided_at",
            "decision_note",
            "cash_account",
            "updated_at",
        ]
    )

    cash.post_movement(
        account=account,
        direction=MovementDirection.OUT,
        amount=expense.amount,
        source_type=MovementSource.EXPENSE,
        source_id=expense.id,
        description=f"{expense.category.name}: {expense.description}"[:255],
        occurred_at=timezone.make_aware(datetime.combine(expense.expense_date, time.min)),
        created_by=approved_by,
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
def mark_expense_paid(
    *, expense: Expense, cash_account: Any = None, created_by: Any = None
) -> Expense:
    """
    Chiqimni "to'langan" deb belgilaydi — BAYROQ, pul harakati emas.

    Pul tasdiqlash paytida allaqachon kassadan chiqqan
    (`approve_expense`). Bu yerda uni ikkinchi marta chiqarish qoldiqni
    ikki barobar kamaytirardi. Qop ko'rsatilsa — faqat to'g'rilanadi.
    """
    if expense.status != ExpenseStatus.APPROVED:
        raise BusinessRuleViolation(
            gettext("Faqat tasdiqlangan chiqimni to'langan deb belgilash mumkin.")
        )

    fields = ["status", "updated_at"]
    expense.status = ExpenseStatus.PAID
    if cash_account is not None:
        if cash_account.organization_id != expense.organization_id:
            raise BusinessRuleViolation(gettext("Kassa hisobi boshqa tashkilotga tegishli."))
        # Qop o'zgarsa, pul harakati ham o'sha qopga ko'chiriladi:
        # eskisiga qarshi yozuv, yangisiga chiqim.
        if expense.cash_account_id != cash_account.id:
            cash.reverse_movements_for(
                source_type=MovementSource.EXPENSE,
                source_id=expense.id,
                description=gettext("qop o'zgartirildi"),
                created_by=created_by,
            )
            cash.post_movement(
                account=cash_account,
                direction=MovementDirection.OUT,
                amount=expense.amount,
                source_type=MovementSource.EXPENSE,
                source_id=expense.id,
                description=f"{expense.category.name}: {expense.description}"[:255],
                occurred_at=timezone.make_aware(datetime.combine(expense.expense_date, time.min)),
                created_by=created_by,
            )
        expense.cash_account = cash_account
        fields.insert(1, "cash_account")

    expense.save(update_fields=fields)
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
