"""
Buxgalter jurnali — hisob kodlari bilan (Bosqich 13.8, brif §9).

Buxgalter o'z dasturiga ko'chiradigan "Dt — Kt — summa" qatorlari. Ikki manba:

* **Hisoblash** — pul yurmagan hodisalar: faktura (Dt 4010 Kt 9030), oylik
  (Dt xarajat Kt 6710; ushlangan soliq Dt 6710 Kt 6410; ijtimoiy soliq Dt
  xarajat Kt 6410), nasiya xarid (Dt xarajat Kt 6010), dividend solig'i.
* **Pul** — oyning HAR BIR `cash_movement` i aynan bir marta (o'tkazma —
  guruh bo'yicha bir qator). Shuning uchun kassa va bank hisoblarining
  aylanmasi qoplar harakatiga tiyinigacha teng — test shuni tekshiradi.

Hisob kodlari — sozlama (`accounts.*`), toifaning o'z kodi
(`expense_category.account_code`) ustun. Hammasi "buxgalter tasdiqlaydi".
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext

__all__ = ["ACCOUNT_KEYS", "build", "to_csv", "to_xlsx"]

ZERO = Decimal("0")

#: Sozlama kaliti → sukut kod (brif §9; qolganlari buxgalter tasdiqlaydi).
ACCOUNT_KEYS = {
    "cash": "5010",
    "bank": "5110",
    "receivables": "4010",
    "advances": "6310",
    "payroll": "6710",
    "budget": "6410",
    "revenue": "9030",
    "suppliers": "6010",
    "expenses": "9420",
    "payroll_expense": "9420",
    "fixed_assets": "0100",
    "other_income": "9390",
    "adjustments": "9390",
    "owner": "8710",
    "capital": "8330",
    "loans": "6810",
}


def _codes() -> dict[str, str]:
    from apps.settings_app.services import get_setting

    return {
        key: str(get_setting(key=f"accounts.{key}") or default)
        for key, default in ACCOUNT_KEYS.items()
    }


def _bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    end = date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)
    return start, end


def _aware(day: date, moment: time) -> datetime:
    return timezone.make_aware(datetime.combine(day, moment))


def build(*, organization_id: Any, year: int, month: int, branch_id: Any = None) -> dict:
    from apps.cash.models import CashMovement, MoneyOperation
    from apps.expenses.models import Expense, ExpenseStatus
    from apps.finance.models import Invoice, InvoiceStatus, Payment
    from apps.payroll.models import PayrollItem, PayrollStatus

    codes = _codes()
    start, end = _bounds(year, month)
    lines: list[dict[str, Any]] = []

    def scoped(queryset: Any) -> Any:
        queryset = queryset.filter(organization_id=organization_id)
        return queryset.filter(branch_id=branch_id) if branch_id else queryset

    def add(day: date, document: str, text: str, debit: str, credit: str, amount: Any) -> None:
        value = Decimal(amount or 0)
        if value <= 0:
            return
        lines.append(
            {
                "date": day.isoformat(),
                "document": document,
                "description": text[:255],
                "debit": debit,
                "credit": credit,
                "amount": f"{value:.2f}",
            }
        )

    def expense_account(expense: Any) -> str:
        if expense.is_capex:
            return codes["fixed_assets"]
        code = (expense.category.account_code or "") if expense.category_id else ""
        if not code and expense.category_id and expense.category.parent_id:
            code = expense.category.parent.account_code or ""
        return code or codes["expenses"]

    # --- Hisoblash ---
    for invoice in (
        scoped(Invoice.objects)
        .filter(period_year=year, period_month=month)
        .exclude(status=InvoiceStatus.CANCELLED)
        .select_related("child")
    ):
        add(
            start,
            invoice.number,
            gettext("Hisoblandi: {child}").format(child=invoice.child.full_name),
            codes["receivables"],
            codes["revenue"],
            invoice.amount_due,
        )

    payroll = (
        scoped(PayrollItem.objects)
        .filter(
            payroll_run__period_year=year,
            payroll_run__period_month=month,
            payroll_run__status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
        )
        .aggregate(
            gross=Sum("gross"),
            income=Sum("tax_income"),
            pension=Sum("tax_pension"),
            social=Sum("tax_social"),
        )
    )
    period = f"{month:02d}.{year}"
    add(
        end,
        gettext("Oylik {period}").format(period=period),
        gettext("Ish haqi hisoblandi"),
        codes["payroll_expense"],
        codes["payroll"],
        payroll["gross"],
    )
    add(
        end,
        gettext("Oylik {period}").format(period=period),
        gettext("JShDS va INPS ushlandi"),
        codes["payroll"],
        codes["budget"],
        (payroll["income"] or ZERO) + (payroll["pension"] or ZERO),
    )
    add(
        end,
        gettext("Oylik {period}").format(period=period),
        gettext("Ijtimoiy soliq hisoblandi"),
        codes["payroll_expense"],
        codes["budget"],
        payroll["social"],
    )

    expenses = scoped(Expense.objects).select_related("category", "category__parent", "supplier")
    for expense in expenses.filter(
        on_credit=True,
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
        expense_date__gte=start,
        expense_date__lte=end,
    ):
        add(
            expense.expense_date,
            gettext("Nasiya"),
            f"{expense.category.name if expense.category_id else ''} — "
            f"{expense.supplier.name if expense.supplier_id else ''}",
            expense_account(expense),
            codes["suppliers"],
            expense.amount,
        )

    operations = scoped(MoneyOperation.objects)
    for draw in operations.filter(
        kind="owner_draw", occurred_on__gte=start, occurred_on__lte=end, tax_amount__gt=0
    ):
        add(
            draw.occurred_on,
            gettext("Dividend"),
            gettext("Dividend soligʻi hisoblandi"),
            codes["owner"],
            codes["budget"],
            draw.tax_amount,
        )

    # --- Pul ---
    movements = list(
        scoped(CashMovement.objects)
        .filter(occurred_at__gte=_aware(start, time.min), occurred_at__lte=_aware(end, time.max))
        .select_related("cash_account")
        .order_by("occurred_at", "created_at")
    )
    payment_ids = [m.source_id for m in movements if m.source_type == "payment"]
    payments = {
        row.id: row
        for row in Payment.objects.filter(pk__in=payment_ids).prefetch_related(
            "allocations__invoice"
        )
    }
    expense_ids = [m.source_id for m in movements if m.source_type == "expense"]
    expense_rows = {row.id: row for row in expenses.filter(pk__in=expense_ids)}
    operation_kinds = dict(
        operations.filter(
            pk__in=[m.source_id for m in movements if m.source_type == "operation"]
        ).values_list("pk", "kind")
    )
    transfer_legs: dict[Any, dict[str, Any]] = {}
    for move in movements:
        if move.source_type == "transfer" and move.transfer_group:
            transfer_legs.setdefault(move.transfer_group, {})[move.direction] = move

    def pot(move: Any) -> str:
        return codes["cash"] if move.cash_account.kind == "cash" else codes["bank"]

    def post(move: Any, counter: str, text: str, document: str = "") -> None:
        day = timezone.localtime(move.occurred_at).date()
        if move.direction == "in":
            add(day, document, text, pot(move), counter, move.amount)
        else:
            add(day, document, text, counter, pot(move), move.amount)

    operation_accounts = {
        "other_income": codes["other_income"],
        "owner_draw": codes["owner"],
        "owner_contribution": codes["capital"],
        "loan_in": codes["loans"],
        "loan_repay": codes["loans"],
        "tax_payment": codes["budget"],
    }
    seen_groups: set[Any] = set()
    for move in movements:
        kind = move.source_type
        if kind == "transfer":
            group = move.transfer_group
            legs = transfer_legs.get(group, {})
            if group in seen_groups or "in" not in legs or "out" not in legs:
                if group not in seen_groups and len(legs) < 2:
                    # Ikkinchi oyog'i boshqa oyda yoki boshqa filialda.
                    post(move, codes["adjustments"], gettext("Oʻtkazma"))
                continue
            seen_groups.add(group)
            day = timezone.localtime(move.occurred_at).date()
            add(
                day,
                "",
                move.description or gettext("Hisoblar orasida oʻtkazma"),
                pot(legs["in"]),
                pot(legs["out"]),
                move.amount,
            )
        elif kind == "payment":
            payment = payments.get(move.source_id)
            if payment is None:
                post(move, codes["receivables"], gettext("Toʻlov"))
                continue
            paid = timezone.localtime(payment.paid_at).date()
            due = advance = ZERO
            for allocation in payment.allocations.all():
                if allocation.released_at is not None:
                    continue
                invoice = allocation.invoice
                if (invoice.period_year, invoice.period_month) > (paid.year, paid.month):
                    advance += allocation.amount
                else:
                    due += allocation.amount
            advance += max(move.amount - due - advance, ZERO)
            text = gettext("Toʻlov: {child}").format(child=payment.child.full_name)
            day = timezone.localtime(move.occurred_at).date()
            if move.direction == "in":
                add(day, payment.reference, text, pot(move), codes["receivables"], due)
                add(day, payment.reference, text, pot(move), codes["advances"], advance)
            else:
                post(move, codes["receivables"], text)
        elif kind == "payment_reversal":
            post(move, codes["receivables"], gettext("Toʻlov bekor qilindi"))
        elif kind == "refund":
            post(move, codes["advances"], gettext("Ota-onaga qaytarildi"))
        elif kind == "expense":
            expense = expense_rows.get(move.source_id)
            if expense is None:
                post(move, codes["expenses"], move.description or gettext("Xarajat"))
            elif expense.on_credit:
                post(move, codes["suppliers"], gettext("Nasiya toʻlandi"))
            else:
                post(move, expense_account(expense), move.description or expense.category.name)
        elif kind in ("payroll", "advance"):
            post(move, codes["payroll"], move.description or gettext("Ish haqi toʻlandi"))
        elif kind == "operation":
            account = operation_accounts.get(operation_kinds.get(move.source_id, ""))
            post(move, account or codes["adjustments"], move.description)
        else:  # opening, manual, count
            post(move, codes["adjustments"], move.description or gettext("Tuzatish"))

    lines.sort(key=lambda row: (row["date"], row["debit"], row["credit"]))
    turnover: dict[str, dict[str, Decimal]] = {}
    for row in lines:
        for side in ("debit", "credit"):
            totals = turnover.setdefault(str(row[side]), {"debit": ZERO, "credit": ZERO})
            totals[side] += Decimal(row["amount"])
    return {
        "period": f"{year}-{month:02d}",
        "accounts": codes,
        "note": gettext("Hisob kodlari — boshlangʻich; buxgalter tasdiqlashi kerak."),
        "lines": lines,
        "turnover": [
            {"account": key, "debit": f"{value['debit']:.2f}", "credit": f"{value['credit']:.2f}"}
            for key, value in sorted(turnover.items())
        ],
    }


_COLUMNS = ("date", "document", "description", "debit", "credit", "amount")


def to_csv(data: dict[str, Any]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [gettext("Sana"), gettext("Hujjat"), gettext("Mazmun"), "Dt", "Kt", gettext("Summa")]
    )
    for row in data["lines"]:
        writer.writerow([row[key] for key in _COLUMNS])
    # Excel kirillcha/oʻzbekcha harflarni toʻgʻri ochishi uchun BOM.
    return ("﻿" + buffer.getvalue()).encode("utf-8")


def to_xlsx(data: dict[str, Any]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = gettext("Jurnal")[:28]
    sheet.append(
        [gettext("Sana"), gettext("Hujjat"), gettext("Mazmun"), "Dt", "Kt", gettext("Summa")]
    )
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in data["lines"]:
        sheet.append([*(row[key] for key in _COLUMNS[:-1]), float(Decimal(row["amount"]))])
    totals = workbook.create_sheet(gettext("Aylanma")[:28])
    totals.append([gettext("Hisob"), "Dt", "Kt"])
    for row in data["turnover"]:
        totals.append([row["account"], float(Decimal(row["debit"])), float(Decimal(row["credit"]))])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
