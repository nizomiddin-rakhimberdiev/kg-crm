"""
Hisobot agregatsiyalari (docs/04 §14.2).

Bu yerda faqat O'QISH bor: hisobot hech narsani o'zgartirmaydi. Har bir
funksiya tenant bilan cheklangan menejerlar orqali ishlaydi
(`Model.objects`), shuning uchun tashkilot chegarasi bu yerda ham
avtomatik — hisobot uni chetlab o'tadigan yagona joy bo'lib qolmasligi
kerak.

**Xom SQL ishlatilmaydi.** Materiallashgan ko'rinish (docs/03 §25) bu
hajmda hali foyda bermaydi, lekin `organization_id` ni qo'lda yozishni
talab qilardi — ya'ni tenant chegarasini ORM'dan tashqariga chiqarardi.
Ma'lumot o'sganda MV qo'shiladi, lekin u ham shu qatlam ortida qoladi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth

from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.children.models import Child
from apps.expenses.models import Expense, ExpenseStatus
from apps.finance.models import Payment
from apps.finance.selectors import debtor_queryset
from apps.payroll.models import PayrollRun, PayrollStatus

__all__ = [
    "revenue_report",
    "expense_report",
    "payroll_report",
    "attendance_report",
    "debtor_report",
    "profit_loss",
]

ZERO = Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=2))

# Hisobotlar KASSA usulida: daromad — qabul qilingan to'lov, yozilgan
# hisob-faktura emas. Ikkalasi ham "daromad" deb ataladi va ular BIR XIL
# EMAS: yozilgan, lekin to'lanmagan hisob-faktura qarzdorlikda ko'rinadi,
# daromadda emas. Javobda `basis` maydoni shuning uchun bor — o'qiyotgan
# odam qaysi ma'noni ko'rayotganini taxmin qilmasin.
BASIS = "cash"


def _money(value: Any) -> str:
    return f"{Decimal(value or 0):.2f}"


def revenue_report(
    *,
    organization_id: Any,
    date_from: date,
    date_to: date,
    branch_id: Any = None,
) -> dict[str, Any]:
    """Oylik kesimda qabul qilingan to'lovlar."""
    queryset = Payment.objects.filter(
        organization_id=organization_id,
        paid_at__date__gte=date_from,
        paid_at__date__lte=date_to,
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    by_month = (
        queryset.annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(total=Coalesce(Sum("amount"), ZERO), count=Count("id"))
        .order_by("month")
    )
    by_method = (
        queryset.values("method")
        .annotate(total=Coalesce(Sum("amount"), ZERO), count=Count("id"))
        .order_by("-total")
    )

    return {
        "basis": BASIS,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total": _money(queryset.aggregate(t=Coalesce(Sum("amount"), ZERO))["t"]),
        "payment_count": queryset.count(),
        "by_month": [
            {
                "month": row["month"].date().isoformat()[:7],
                "total": _money(row["total"]),
                "count": row["count"],
            }
            for row in by_month
        ],
        "by_method": [
            {"method": row["method"], "total": _money(row["total"]), "count": row["count"]}
            for row in by_method
        ],
    }


def expense_report(
    *,
    organization_id: Any,
    date_from: date,
    date_to: date,
    branch_id: Any = None,
) -> dict[str, Any]:
    """
    Chiqimlar — faqat tasdiqlangan va to'langan.

    Kutilayotgan so'rov hali xarajat emas: uni qo'shish sarfni oshirib
    ko'rsatardi va byudjet qarorini buzardi (Sprint 7 bilan bir xil qoida).
    """
    queryset = Expense.objects.filter(
        organization_id=organization_id,
        expense_date__gte=date_from,
        expense_date__lte=date_to,
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    by_month = (
        queryset.annotate(month=TruncMonth("expense_date"))
        .values("month")
        .annotate(total=Coalesce(Sum("amount"), ZERO))
        .order_by("month")
    )
    by_category = (
        queryset.values("category__name")
        .annotate(total=Coalesce(Sum("amount"), ZERO))
        .order_by("-total")
    )

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total": _money(queryset.aggregate(t=Coalesce(Sum("amount"), ZERO))["t"]),
        "by_month": [
            {"month": row["month"].isoformat()[:7], "total": _money(row["total"])}
            for row in by_month
        ],
        "by_category": [
            {"category": row["category__name"] or "—", "total": _money(row["total"])}
            for row in by_category
        ],
    }


def payroll_report(
    *,
    organization_id: Any,
    year: int,
    branch_id: Any = None,
) -> dict[str, Any]:
    """
    Oylik maosh — faqat YAKUNLANGAN yoki to'langan davrlar.

    Qoralama davr hali xarajat emas: uning summasi tahrirlanishi mumkin
    va uni hisobotga qo'shish tasdiqlanmagan raqamni fakt sifatida
    ko'rsatardi.
    """
    queryset = PayrollRun.objects.filter(
        organization_id=organization_id,
        period_year=year,
        status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    rows = (
        queryset.values("period_month")
        .annotate(
            gross=Coalesce(Sum("total_gross"), ZERO),
            deductions=Coalesce(Sum("total_deductions"), ZERO),
            net=Coalesce(Sum("total_net"), ZERO),
        )
        .order_by("period_month")
    )

    totals = queryset.aggregate(
        gross=Coalesce(Sum("total_gross"), ZERO),
        deductions=Coalesce(Sum("total_deductions"), ZERO),
        net=Coalesce(Sum("total_net"), ZERO),
    )

    return {
        "year": year,
        "total_gross": _money(totals["gross"]),
        "total_deductions": _money(totals["deductions"]),
        "total_net": _money(totals["net"]),
        "by_month": [
            {
                "month": f"{year}-{row['period_month']:02d}",
                "gross": _money(row["gross"]),
                "deductions": _money(row["deductions"]),
                "net": _money(row["net"]),
            }
            for row in rows
        ],
    }


def attendance_report(
    *,
    organization_id: Any,
    year: int,
    month: int,
    group_id: Any = None,
) -> dict[str, Any]:
    """Oylik davomat: guruh kesimida foizlar."""
    queryset = AttendanceRecord.objects.filter(
        organization_id=organization_id,
        attendance_date__year=year,
        attendance_date__month=month,
    )
    if group_id:
        queryset = queryset.filter(group_id=group_id)

    rows = (
        queryset.values("group_id", "group__name")
        .annotate(
            present=Count("id", filter=Q(status=AttendanceStatus.PRESENT)),
            absent=Count("id", filter=Q(status=AttendanceStatus.ABSENT)),
            excused=Count("id", filter=Q(status=AttendanceStatus.EXCUSED)),
            total=Count("id"),
        )
        .order_by("group__name")
    )

    groups = [
        {
            "group_id": str(row["group_id"]) if row["group_id"] else None,
            "group": row["group__name"] or "—",
            "present": row["present"],
            "absent": row["absent"],
            "excused": row["excused"],
            "total": row["total"],
            "attendance_rate": (
                round(row["present"] / row["total"] * 100, 1) if row["total"] else 0.0
            ),
        }
        for row in rows
    ]

    marked = sum(row["total"] for row in groups)
    attended = sum(row["present"] for row in groups)

    return {
        "year": year,
        "month": month,
        "marked_records": marked,
        "attendance_rate": round(attended / marked * 100, 1) if marked else 0.0,
        "by_group": groups,
    }


def debtor_report(*, organization_id: Any, branch_id: Any = None) -> dict[str, Any]:
    """
    Qarzdorlik kesimi — LEDGER'dan hisoblanadi, saqlangan jadvaldan emas.

    `organization_id` argument sifatida olinadi, lekin `debtor_queryset`
    baribir tenant menejeri ortida ishlaydi — bu ikki qavatli himoya
    ataylab.
    """
    queryset = debtor_queryset().filter(organization_id=organization_id)
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    rows = list(queryset.values("id", "first_name", "last_name", "ledger_balance")[:500])
    total = sum((row["ledger_balance"] or Decimal("0")) for row in rows)

    return {
        "debtor_count": len(rows),
        "total_outstanding": _money(total),
        "rows": [
            {
                "child_id": str(row["id"]),
                "full_name": f"{row['last_name']} {row['first_name']}",
                "balance": _money(row["ledger_balance"]),
            }
            for row in rows
        ],
    }


def profit_loss(
    *,
    organization_id: Any,
    date_from: date,
    date_to: date,
    branch_id: Any = None,
) -> dict[str, Any]:
    """
    Foyda va zarar: daromad − chiqim − oylik.

    Bu **kassa usuli** (`basis: "cash"`): qabul qilingan pul minus
    to'langan/tasdiqlangan xarajat. Hisoblash usuli (accrual) boshqa
    raqam berardi va u buxgalteriya qarori — mijoz bilan kelishilishi
    kerak, taxmin qilinmasligi.
    """
    revenue = revenue_report(
        organization_id=organization_id,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
    )
    expenses = expense_report(
        organization_id=organization_id,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
    )

    payroll_queryset = PayrollRun.objects.filter(
        organization_id=organization_id,
        status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
        period_year__gte=date_from.year,
        period_year__lte=date_to.year,
    )
    if branch_id:
        payroll_queryset = payroll_queryset.filter(branch_id=branch_id)

    payroll_by_month: dict[str, Decimal] = {}
    for run in payroll_queryset.values("period_year", "period_month", "total_gross"):
        period = date(run["period_year"], run["period_month"], 1)
        if date_from.replace(day=1) <= period <= date_to:
            key = period.isoformat()[:7]
            payroll_by_month[key] = payroll_by_month.get(key, Decimal("0")) + run["total_gross"]

    revenue_by_month = {row["month"]: Decimal(row["total"]) for row in revenue["by_month"]}
    expense_by_month = {row["month"]: Decimal(row["total"]) for row in expenses["by_month"]}
    months = sorted(set(revenue_by_month) | set(expense_by_month) | set(payroll_by_month))

    payroll_total = sum(payroll_by_month.values(), Decimal("0"))
    net = Decimal(revenue["total"]) - Decimal(expenses["total"]) - payroll_total

    return {
        "basis": BASIS,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "revenue": revenue["total"],
        "expenses": expenses["total"],
        "payroll": _money(payroll_total),
        "net": _money(net),
        "by_month": [
            {
                "month": month,
                "revenue": _money(revenue_by_month.get(month, Decimal("0"))),
                "expenses": _money(expense_by_month.get(month, Decimal("0"))),
                "payroll": _money(payroll_by_month.get(month, Decimal("0"))),
                "net": _money(
                    revenue_by_month.get(month, Decimal("0"))
                    - expense_by_month.get(month, Decimal("0"))
                    - payroll_by_month.get(month, Decimal("0"))
                ),
            }
            for month in months
        ],
    }


def active_children_count(*, organization_id: Any, branch_id: Any = None) -> int:
    """
    Ro'yxatdagi faol bolalar soni.

    Ta'rif ataylab GURUHGA BOG'LIQ EMAS. Avval bu yerda "faol a'zolik"
    talab qilingan edi va CSV import qilingan, lekin hali guruhga
    biriktirilmagan bolalar hisobga tushmasdi: direktor 60 ta bola
    kiritib, dashboard'da `0` ko'rardi. Guruhga biriktirish keyin
    bo'ladigan ish, bola esa allaqachon bog'chaniki.

    ⚠️ Bu **hisob-kitob uchun mo'ljallangan raqam emas.** Obuna qancha
    bolaga hisoblanishi (ADR-11, `v_org_billable_children`) alohida
    savol va u Sprint 10 da narx qoidalari bilan birga hal qilinadi —
    u yerda "guruhga biriktirilganmi" muhim bo'lishi mumkin. Ikki
    ta'rif bir xil nom ostida yashirin qolmasligi uchun shu izoh.
    """
    queryset = Child.objects.filter(organization_id=organization_id, is_active=True)
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)
    return queryset.count()
