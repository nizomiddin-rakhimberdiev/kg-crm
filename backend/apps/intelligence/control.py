"""
Nazorat reyestri: tekshiruvlar va "Diqqat" (Bosqich 13.4, brif §7, ADR-14).

Har qoida — deterministik funksiya: tashkilot, filial, davr → natija va
DALIL. Bashorat yo'q, LLM yo'q (ADR-14). Chegaralar sozlamada
(`control.*`); matn — bitta joyda, foydalanuvchi tilida.

* **Tekshiruv** (`checks`) — yashil / qizil / tegishli emas, tafsilot bilan.
* **Diqqat** (`attention`) — g'ayrioddiy holat: kim, qancha, qachon.

Hisobot paketi (13.5), bosh sahifa va Telegram xulosasi aynan shu ikki
funksiyani o'qiydi — bitta raqam ikki joyda ikki xil chiqmasin.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy

__all__ = ["checks", "attention", "CHECK_TITLES", "RULE_TITLES"]

ZERO = Decimal("0")


def _setting(key: str, default: Any, branch: Any = None) -> Any:
    from apps.settings_app.services import get_setting

    value = get_setting(key=key, branch=branch)
    return default if value in (None, "") else value


def _som(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", " ")


def _bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    return start, date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)


def _scoped(queryset: Any, organization_id: Any, branch_id: Any) -> Any:
    queryset = queryset.filter(organization_id=organization_id)
    return queryset.filter(branch_id=branch_id) if branch_id else queryset


def _expenses(organization_id: Any, branch_id: Any, start: date, end: date) -> Any:
    from apps.expenses.models import Expense, ExpenseStatus

    return _scoped(Expense.objects, organization_id, branch_id).filter(
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
        expense_date__gte=start,
        expense_date__lte=end,
        payment__isnull=True,  # bank komissiyasi — tizim yozuvi
    )


# --- Tekshiruvlar ---

CHECK_TITLES = {
    "revenue_equation": gettext_lazy("Daromad tengligi"),
    "cash_bridge": gettext_lazy("Hisoblar mosligi"),
    "negative_balance": gettext_lazy("Manfiy qoldiq yoʻq"),
    "transit_on_time": gettext_lazy("Yoʻldagi pul oʻz vaqtida tushgan"),
    "no_future_dates": gettext_lazy("Kelajak sanali yozuv yoʻq"),
    "benefits_have_reason": gettext_lazy("Har imtiyozda sabab bor"),
    "big_expense_documents": gettext_lazy("Katta xarajatlarda hujjat bor"),
    "cash_counts": gettext_lazy("Kassa sanoqlari"),
    "bank_statement": gettext_lazy("Bank koʻchirmasi bilan mos"),
    "month_closed": gettext_lazy("Oy yopilgan"),
    "fiscal_receipts": gettext_lazy("Naqd va karta toʻlovlarida fiskal chek bor"),
}


def _check(key: str, ok: bool | None, detail: str = "", link: str = "") -> dict[str, Any]:
    return {
        "id": key,
        "title": str(CHECK_TITLES[key]),
        "status": "na" if ok is None else ("ok" if ok else "fail"),
        "detail": detail,
        "link": link,
    }


def checks(
    *, organization_id: Any, year: int, month: int, branch_id: Any = None
) -> list[dict[str, Any]]:
    from apps.cash.models import BankStatement
    from apps.cash.selectors import account_balances
    from apps.expenses.models import Expense
    from apps.finance.models import Discount, MonthClose, Payment
    from apps.finance.selectors import in_transit, monthly_summary
    from apps.reports.money import cash_flow, data_completeness

    start, end = _bounds(year, month)
    today = timezone.localdate()
    rows: list[dict[str, Any]] = []

    summary = monthly_summary(
        organization_id=organization_id, year=year, month=month, branch_id=branch_id
    )
    # Izoh — odam tilida, xom formula emas (audit, 2026-10-21). Ekranda
    # "5100000.00 + (0.00) + (-1159000.00)" turardi va bu tekshiruvning
    # butun ma'nosini — "raqamlar bir-biriga mos" — yashirardi.
    parts = summary["check"]["parts"]
    rows.append(
        _check(
            "revenue_equation",
            summary["check"]["ok"],
            gettext(
                "Hisoblangan {charged}, imtiyoz {benefits}, qayta hisob {recalculated} → "
                "yigʻilgan {collected} + qarz {outstanding}"
            ).format(
                charged=_som(Decimal(parts["charged"])),
                benefits=_som(Decimal(parts["benefits"])),
                recalculated=_som(Decimal(parts["recalculated"])),
                collected=_som(Decimal(parts["collected"])),
                outstanding=_som(Decimal(parts["outstanding"])),
            ),
            "/reports",
        )
    )

    flow = cash_flow(organization_id=organization_id, year=year, month=month, branch_id=branch_id)
    rows.append(_check("cash_bridge", flow["check"]["ok"], "", "/cash"))

    negatives = [
        row
        for row in account_balances(organization_id=organization_id, branch_id=branch_id)
        if Decimal(row["balance"]) < 0
    ]
    rows.append(
        _check(
            "negative_balance",
            not negatives,
            ", ".join(f"{row['name']}: {_som(Decimal(row['balance']))}" for row in negatives),
            "/cash",
        )
    )

    overdue = [
        row
        for row in in_transit(organization_id=organization_id, branch_id=branch_id)
        if row["overdue"]
    ]
    rows.append(
        _check(
            "transit_on_time",
            not overdue,
            gettext("{n} ta toʻlov kechikkan").format(n=len(overdue)) if overdue else "",
            "/cash",
        )
    )

    future = (
        _scoped(Payment.objects, organization_id, branch_id).filter(paid_at__date__gt=today).count()
        + _scoped(Expense.objects, organization_id, branch_id)
        .filter(expense_date__gt=today)
        .count()
    )
    rows.append(_check("no_future_dates", future == 0, str(future) if future else ""))

    unexplained = (
        _scoped(Discount.objects, organization_id, branch_id)
        .filter(is_active=True)
        .filter(Q(reason="") | Q(reason__isnull=True))
        .count()
    )
    rows.append(
        _check(
            "benefits_have_reason",
            unexplained == 0,
            gettext("{n} ta imtiyozda sabab yoʻq").format(n=unexplained) if unexplained else "",
        )
    )

    threshold = Decimal(str(_setting("control.document_threshold", 1000000)))
    missing = _expenses(organization_id, branch_id, start, end).filter(
        amount__gte=threshold, receipt=""
    )
    count = missing.count()
    rows.append(
        _check(
            "big_expense_documents",
            count == 0,
            gettext("{n} ta xarajatda chek yoʻq").format(n=count) if count else "",
            "/expenses",
        )
    )

    completeness = data_completeness(
        organization_id=organization_id, year=year, month=month, branch_id=branch_id
    )
    active, closed = completeness["cash"]["active_days"], completeness["cash"]["closed_days"]
    rows.append(
        _check(
            "cash_counts",
            None if active == 0 else closed >= active,
            gettext("{closed} / {active} kun yopilgan").format(closed=closed, active=active),
            "/cash",
        )
    )

    statements = _scoped(BankStatement.objects, organization_id, branch_id).filter(
        period_to__gte=start, period_from__lte=end
    )
    differing = [
        statement
        for statement in statements
        if statement.closing_balance is not None
        and statement.system_balance is not None
        and statement.closing_balance != statement.system_balance
    ]
    rows.append(
        _check(
            "bank_statement",
            None if not statements.exists() else not differing,
            ", ".join(
                f"{row.file_name}: {_som(row.closing_balance - row.system_balance)}"
                for row in differing
            ),
            "/cash",
        )
    )

    finished = end < today
    closed_month = (
        _scoped(MonthClose.objects, organization_id, branch_id)
        .filter(period_year=year, period_month=month)
        .exists()
    )
    rows.append(_check("month_closed", closed_month if finished else None, "", "/reports"))

    # Fiskal chek (13.8, test 13): nazorat yoqilgan sanadan; Click/Payme
    # chekini to'lov tizimi beradi, ular bu yerga tushmaydi.
    from apps.finance import fiscal

    if fiscal.control_from(branch_id) is None:
        rows.append(_check("fiscal_receipts", None))
    else:
        cover = fiscal.coverage(
            organization_id=organization_id, start=start, end=end, branch_id=branch_id
        )
        rows.append(
            _check(
                "fiscal_receipts",
                cover["covered"] == cover["required"] if cover["required"] else True,
                f"{cover['covered']}/{cover['required']}" if cover["required"] else "",
                "/payments",
            )
        )
    return rows


# --- Diqqat ---

RULE_TITLES = {
    "category_jump": gettext_lazy("Xarajat keskin oʻzgardi"),
    "expense_without_document": gettext_lazy("Hujjatsiz katta xarajat"),
    "split_expenses": gettext_lazy("Bir kunda bir toifaga bir nechta mayda xarajat"),
    "duplicate_expense": gettext_lazy("Takrorlangan xarajat"),
    "new_benefit": gettext_lazy("Yangi imtiyoz"),
    "write_off": gettext_lazy("Qarz hisobdan chiqarildi"),
    "reversal": gettext_lazy("Toʻlov bekor qilindi"),
    "refund": gettext_lazy("Ota-onaga pul qaytarildi"),
    "backdated_payment": gettext_lazy("Orqa sana bilan toʻlov"),
    "manual_allocation": gettext_lazy("Toʻlov qoʻlda boshqa oyga taqsimlandi"),
    "closed_month_correction": gettext_lazy("Yopilgan oyga tuzatish"),
    "cash_difference": gettext_lazy("Kassa farqi"),
    "attendance_without_invoice": gettext_lazy("Davomatda bor, fakturasi 0 yoki ketgan"),
    "active_without_attendance": gettext_lazy("Faol, lekin davomati yoʻq"),
    "staff_child_unpaid": gettext_lazy("Xodim farzandi toʻlamagan"),
    "payment_without_fiscal": gettext_lazy("Fiskal cheksiz naqd yoki karta toʻlovi"),
}


def _item(
    rule: str,
    severity: str,
    message: str,
    *,
    amount: Decimal | None = None,
    subject: dict[str, Any] | None = None,
    link: str = "",
    at: Any = None,
) -> dict[str, Any]:
    return {
        "rule": rule,
        "title": str(RULE_TITLES[rule]),
        "severity": severity,
        "message": message,
        "amount": f"{amount:.2f}" if amount is not None else None,
        "subject": subject,
        "link": link,
        "at": at.isoformat() if hasattr(at, "isoformat") else at,
    }


def _expense_rules(organization_id: Any, branch_id: Any, start: date, end: date) -> list[dict]:
    from apps.expenses.models import Expense, ExpenseStatus

    items: list[dict[str, Any]] = []
    threshold = Decimal(str(_setting("control.document_threshold", 1000000)))
    change = Decimal(str(_setting("control.change_percent", 15)))
    month_expenses = _expenses(organization_id, branch_id, start, end).select_related("category")

    for expense in month_expenses.filter(amount__gt=threshold, receipt=""):
        items.append(
            _item(
                "expense_without_document",
                "warning",
                gettext("{category}: {amount} soʻm, chek yoʻq").format(
                    category=expense.category.name, amount=_som(expense.amount)
                ),
                amount=expense.amount,
                subject={"type": "expense", "id": str(expense.id)},
                link="/expenses",
                at=expense.expense_date,
            )
        )

    groups: dict[tuple[Any, date], list[Any]] = defaultdict(list)
    seen: dict[tuple[Any, date, Decimal], int] = defaultdict(int)
    for expense in month_expenses:
        groups[(expense.category_id, expense.expense_date)].append(expense)
        seen[(expense.category_id, expense.expense_date, expense.amount)] += 1
    for (_category, day), rows in groups.items():
        small = [row for row in rows if row.amount < threshold]
        total = sum((row.amount for row in small), ZERO)
        if len(small) >= 2 and total > threshold:
            items.append(
                _item(
                    "split_expenses",
                    "warning",
                    gettext("{category}, {day}: {n} ta xarajat, jami {amount} soʻm").format(
                        category=small[0].category.name,
                        day=day.strftime("%d.%m"),
                        n=len(small),
                        amount=_som(total),
                    ),
                    amount=total,
                    link="/expenses",
                    at=day,
                )
            )
    for (category_id, day, amount), n in seen.items():
        if n >= 2:
            name = groups[(category_id, day)][0].category.name
            items.append(
                _item(
                    "duplicate_expense",
                    "warning",
                    gettext("{category}, {day}: {amount} soʻm × {n}").format(
                        category=name, day=day.strftime("%d.%m"), amount=_som(amount), n=n
                    ),
                    amount=amount * n,
                    link="/expenses",
                    at=day,
                )
            )

    # Toifa bo'yicha keskin o'zgarish — o'tgan oy va 3 oylik o'rtachaga nisbatan.
    def by_category(first: date, last: date) -> dict[str, Decimal]:
        return {
            row["category__name"]: row["total"]
            for row in _scoped(Expense.objects, organization_id, branch_id)
            .filter(
                status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
                expense_date__gte=first,
                expense_date__lte=last,
                payment__isnull=True,
                is_capex=False,
            )
            .values("category__name")
            .annotate(total=Sum("amount"))
        }

    current = by_category(start, end)
    prev_start = (start - timedelta(days=1)).replace(day=1)
    previous = by_category(prev_start, start - timedelta(days=1))
    floor = threshold / 2
    for name, total in current.items():
        before = previous.get(name, ZERO)
        if before >= floor and abs(total - before) * 100 > before * change:
            percent = (total - before) * 100 / before
            items.append(
                _item(
                    "category_jump",
                    "info",
                    gettext("{category}: {before} → {after} soʻm ({percent:+.0f}%)").format(
                        category=name,
                        before=_som(before),
                        after=_som(total),
                        percent=percent,
                    ),
                    amount=total - before,
                    link="/expenses",
                )
            )
    return items


def _fiscal_rules(organization_id: Any, branch_id: Any, start: date, end: date) -> list[dict]:
    """Bitta band — oy bo'yicha jami; har to'lovga alohida band ro'yxatni ko'mib yuborardi."""
    from apps.finance import fiscal

    rows = fiscal.missing(
        organization_id=organization_id, start=start, end=end, branch_id=branch_id
    )
    total = rows.aggregate(total=Sum("amount"))["total"]
    count = rows.count()
    if not count:
        return []
    return [
        _item(
            "payment_without_fiscal",
            "warning",
            gettext("{n} ta toʻlovda chek yoʻq, jami {amount} soʻm").format(
                n=count, amount=_som(total)
            ),
            amount=total,
            link="/payments",
        )
    ]


def _money_rules(organization_id: Any, branch_id: Any, start: date, end: date) -> list[dict]:
    from apps.cash.models import CashCount
    from apps.finance.models import (
        Discount,
        InvoiceLine,
        InvoiceWriteOff,
        Payment,
        Refund,
    )

    items: list[dict[str, Any]] = []
    for benefit in (
        _scoped(Discount.objects, organization_id, branch_id)
        .filter(created_at__date__gte=start, created_at__date__lte=end)
        .exclude(kind="sibling")
        .select_related("child", "created_by")
    ):
        items.append(
            _item(
                "new_benefit",
                "info",
                gettext("{child}: {kind} — {reason} ({who})").format(
                    child=benefit.child.full_name,
                    kind=benefit.get_kind_display(),
                    reason=benefit.reason,
                    who=benefit.created_by.full_name if benefit.created_by_id else "—",
                ),
                subject={"type": "child", "id": str(benefit.child_id)},
                at=benefit.created_at,
            )
        )
    for row in (
        _scoped(InvoiceWriteOff.objects, organization_id, branch_id)
        .filter(created_at__date__gte=start, created_at__date__lte=end)
        .select_related("invoice__child", "created_by")
    ):
        items.append(
            _item(
                "write_off",
                "warning",
                gettext("{child}: {amount} soʻm — {reason} ({who})").format(
                    child=row.invoice.child.full_name,
                    amount=_som(row.amount),
                    reason=row.reason,
                    who=row.created_by.full_name if row.created_by_id else "—",
                ),
                amount=row.amount,
                subject={"type": "child", "id": str(row.invoice.child_id)},
                at=row.created_at,
            )
        )
    payments = _scoped(Payment.objects, organization_id, branch_id).select_related("child")
    for payment in payments.filter(reversed_at__date__gte=start, reversed_at__date__lte=end):
        items.append(
            _item(
                "reversal",
                "warning",
                gettext("{child}: {amount} soʻm — {reason}").format(
                    child=payment.child.full_name,
                    amount=_som(payment.amount),
                    reason=payment.reversal_reason or "—",
                ),
                amount=payment.amount,
                subject={"type": "payment", "id": str(payment.id)},
                at=payment.reversed_at,
            )
        )
    for refund in (
        _scoped(Refund.objects, organization_id, branch_id)
        .filter(refunded_on__gte=start, refunded_on__lte=end)
        .select_related("child")
    ):
        items.append(
            _item(
                "refund",
                "info",
                gettext("{child}: {amount} soʻm — {reason}").format(
                    child=refund.child.full_name, amount=_som(refund.amount), reason=refund.reason
                ),
                amount=refund.amount,
                at=refund.refunded_on,
            )
        )
    month_payments = payments.filter(created_at__date__gte=start, created_at__date__lte=end)
    for payment in month_payments.exclude(backdate_reason=""):
        items.append(
            _item(
                "backdated_payment",
                "info",
                gettext("{child}: {amount} soʻm, sana {day} — {reason}").format(
                    child=payment.child.full_name,
                    amount=_som(payment.amount),
                    day=timezone.localtime(payment.paid_at).strftime("%d.%m.%Y"),
                    reason=payment.backdate_reason,
                ),
                amount=payment.amount,
                at=payment.created_at,
            )
        )
    for payment in month_payments.exclude(allocation_reason=""):
        items.append(
            _item(
                "manual_allocation",
                "info",
                gettext("{child}: {amount} soʻm — {reason}").format(
                    child=payment.child.full_name,
                    amount=_som(payment.amount),
                    reason=payment.allocation_reason,
                ),
                amount=payment.amount,
                at=payment.created_at,
            )
        )
    # Yopilgan (o'tgan) oyning qayta hisobi keyingi fakturaga tushgan qator —
    # arizaning oyi fakturaning oyidan farq qiladi (Bosqich 12.6).
    corrections = InvoiceLine.objects.filter(
        invoice__organization_id=organization_id,
        kind="credit",
        absence_claim__isnull=False,
        invoice__period_year=start.year,
        invoice__period_month=start.month,
    ).select_related("invoice__child", "absence_claim")
    if branch_id:
        corrections = corrections.filter(invoice__branch_id=branch_id)
    for line in corrections:
        claim = line.absence_claim
        if claim is None:
            continue
        claimed = claim.date_from
        if (claimed.year, claimed.month) == (start.year, start.month):
            continue
        items.append(
            _item(
                "closed_month_correction",
                "info",
                f"{line.invoice.child.full_name}: {line.description}",
                amount=line.line_total,
            )
        )
    for count in (
        _scoped(CashCount.objects, organization_id, branch_id)
        .filter(counted_on__gte=start, counted_on__lte=end)
        .exclude(difference=0)
        .select_related("created_by")
    ):
        items.append(
            _item(
                "cash_difference",
                "critical" if count.difference < 0 else "warning",
                gettext("{day}: {amount} soʻm — {reason}").format(
                    day=count.counted_on.strftime("%d.%m"),
                    amount=_som(count.difference),
                    reason=count.reason,
                ),
                amount=count.difference,
                link="/cash",
                at=count.counted_on,
            )
        )
    return items


def _children_rules(organization_id: Any, branch_id: Any, start: date, end: date) -> list[dict]:
    from apps.attendance.models import AttendanceRecord
    from apps.children.models import Child, EnrollmentStatus
    from apps.children.services import ENROLLED_STATUSES
    from apps.finance.models import Discount, Invoice, InvoiceStatus

    items: list[dict[str, Any]] = []
    present = (
        _scoped(AttendanceRecord.objects, organization_id, branch_id)
        .filter(attendance_date__gte=start, attendance_date__lte=end, status="present")
        .values("child")
        .annotate(days=Count("id"))
    )
    present_days = {row["child"]: row["days"] for row in present}
    if not present_days:
        return items
    invoices = {
        invoice.child_id: invoice
        for invoice in _scoped(Invoice.objects, organization_id, branch_id)
        .filter(period_year=start.year, period_month=start.month)
        .exclude(status=InvoiceStatus.CANCELLED)
        .prefetch_related("lines")
    }
    children = Child.objects.filter(pk__in=present_days).only(
        "id", "first_name", "last_name", "enrollment_status"
    )
    for child in children:
        invoice = invoices.get(child.id)
        gone = child.enrollment_status in (EnrollmentStatus.WITHDRAWN, EnrollmentStatus.GRADUATED)
        paused = invoice is not None and any(line.kind == "pause" for line in invoice.lines.all())
        zero = invoice is not None and invoice.amount_due <= 0 and not paused
        if gone or zero or (invoice is None and invoices):
            items.append(
                _item(
                    "attendance_without_invoice",
                    "warning",
                    gettext("{child}: {days} kun kelgan — {why}").format(
                        child=child.full_name,
                        days=present_days[child.id],
                        why=gettext("holati: ketgan")
                        if gone
                        else gettext("faktura 0")
                        if zero
                        else gettext("faktura yoʻq"),
                    ),
                    subject={"type": "child", "id": str(child.id)},
                    link=f"/children/{child.id}",
                )
            )

    active = (
        _scoped(Child.objects, organization_id, branch_id)
        .filter(is_active=True, enrollment_status__in=ENROLLED_STATUSES)
        .filter(Q(enrolled_on__isnull=True) | Q(enrolled_on__lt=start))
    )
    for child in active.exclude(pk__in=present_days).only("id", "first_name", "last_name")[:50]:
        items.append(
            _item(
                "active_without_attendance",
                "info",
                gettext("{child}: oy davomida bironta kelgan kuni yoʻq").format(
                    child=child.full_name
                ),
                subject={"type": "child", "id": str(child.id)},
                link=f"/children/{child.id}",
            )
        )

    staff_children = Discount.objects.filter(
        organization_id=organization_id, kind="staff_child", is_active=True
    ).values_list("child_id", flat=True)
    for invoice in invoices.values():
        if invoice.child_id in set(staff_children) and invoice.amount_due > invoice.amount_paid:
            items.append(
                _item(
                    "staff_child_unpaid",
                    "info",
                    gettext("{child}: {amount} soʻm qarz").format(
                        child=invoice.child.full_name,
                        amount=_som(invoice.amount_due - invoice.amount_paid),
                    ),
                    amount=invoice.amount_due - invoice.amount_paid,
                    subject={"type": "child", "id": str(invoice.child_id)},
                )
            )
    return items


def attention(
    *, organization_id: Any, year: int, month: int, branch_id: Any = None
) -> list[dict[str, Any]]:
    """Oyning "Diqqat" ro'yxati — avval jiddiylari."""
    start, end = _bounds(year, month)
    items = (
        _expense_rules(organization_id, branch_id, start, end)
        + _money_rules(organization_id, branch_id, start, end)
        + _fiscal_rules(organization_id, branch_id, start, end)
        + _children_rules(organization_id, branch_id, start, end)
    )
    order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(items, key=lambda item: order[item["severity"]])
