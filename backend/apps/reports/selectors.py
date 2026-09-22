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

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import (
    Coalesce,
    TruncDay,
    TruncMonth,
    TruncQuarter,
    TruncWeek,
    TruncYear,
)
from django.utils.translation import gettext

from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.expenses.models import Expense, ExpenseStatus
from apps.finance.models import Payment
from apps.finance.selectors import debtor_queryset
from apps.payroll.models import PayrollRun, PayrollStatus

__all__ = [
    "GROUP_BY_CHOICES",
    "period_buckets",
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


# --- Davr kesimi ---
#
# Hisobot `group_by` bilan kun / hafta / oy / chorak / yil kesimida
# qaytadi (docs/04 §14.2). Bir xil davr uchun jami ko'rsatkichlar
# kesimga bog'liq EMAS — kesim faqat qatorlarni qanday bo'lishni
# belgilaydi. Shu sababli ikkalasi ham bitta queryset'dan hisoblanadi.
GROUP_BY_CHOICES: tuple[str, ...] = ("day", "week", "month", "quarter", "year")
DEFAULT_GROUP_BY = "month"

# Kunlik kesimda o'n yillik davr so'ralsa 3 650 qator qaytardi — bu
# grafik uchun ham, brauzer uchun ham ma'nosiz. Chegara ochiq xato
# beradi va yirikroq kesimni taklif qiladi.
MAX_BUCKETS = 400

_TRUNC = {
    "day": TruncDay,
    "week": TruncWeek,
    "month": TruncMonth,
    "quarter": TruncQuarter,
    "year": TruncYear,
}


def _validate_group_by(group_by: str) -> str:
    if group_by not in GROUP_BY_CHOICES:
        raise BusinessRuleViolation(
            gettext("`group_by` noto'g'ri: {group_by!r}. Mumkin: {join}.").format(
                group_by=group_by, join=", ".join(GROUP_BY_CHOICES)
            )
        )
    return group_by


def _add_months(value: date, months: int) -> date:
    total = value.year * 12 + (value.month - 1) + months
    return date(total // 12, total % 12 + 1, 1)


def _bucket_start(value: date, group_by: str) -> date:
    """Sana tushadigan davrning BOSHI — Postgres `date_trunc` bilan bir xil."""
    if group_by == "day":
        return value
    if group_by == "week":
        return value - timedelta(days=value.weekday())  # ISO: dushanba
    if group_by == "month":
        return value.replace(day=1)
    if group_by == "quarter":
        return date(value.year, 3 * ((value.month - 1) // 3) + 1, 1)
    return date(value.year, 1, 1)


def _next_bucket(start: date, group_by: str) -> date:
    if group_by == "day":
        return start + timedelta(days=1)
    if group_by == "week":
        return start + timedelta(days=7)
    if group_by == "month":
        return _add_months(start, 1)
    if group_by == "quarter":
        return _add_months(start, 3)
    return date(start.year + 1, 1, 1)


def period_buckets(date_from: date, date_to: date, group_by: str) -> list[date]:
    """
    `[date_from, date_to]` ni qamrab oladigan davr boshlari — UZLUKSIZ.

    Bo'sh davr ham qatorda turadi: to'lovsiz hafta grafikdan tushib
    qolsa, tushish o'sish bo'lib ko'rinardi — va bu eng noto'g'ri
    xulosaga olib keladigan turdagi xato.
    """
    group_by = _validate_group_by(group_by)
    if date_from > date_to:
        raise BusinessRuleViolation(gettext("Davr boshi oxiridan keyin bo'lishi mumkin emas."))

    buckets: list[date] = []
    cursor = _bucket_start(date_from, group_by)
    while cursor <= date_to:
        buckets.append(cursor)
        if len(buckets) > MAX_BUCKETS:
            raise BusinessRuleViolation(
                gettext(
                    "Bu davr {group_by!r} kesimida {MAX_BUCKETS} dan ortiq qator beradi — "
                    "yirikroq kesim tanlang."
                ).format(group_by=group_by, MAX_BUCKETS=MAX_BUCKETS)
            )
        cursor = _next_bucket(cursor, group_by)
    return buckets


def _as_date(value: Any) -> date:
    """`Trunc*` DateTimeField'da datetime, DateField'da date qaytaradi."""
    return value.date() if isinstance(value, datetime) else value


def _grouped_totals(queryset: Any, field: str, group_by: str, **aggregates: Any) -> dict[date, Any]:
    """Queryset'ni davr bo'yicha yig'adi: `{davr_boshi: {agregatlar}}`."""
    rows = (
        queryset.annotate(period=_TRUNC[group_by](field))
        .values("period")
        .annotate(**aggregates)
        .order_by("period")
    )
    return {_as_date(row["period"]): row for row in rows}


def revenue_report(
    *,
    organization_id: Any,
    date_from: date,
    date_to: date,
    branch_id: Any = None,
    group_by: str = DEFAULT_GROUP_BY,
) -> dict[str, Any]:
    """Davr kesimida (`group_by`) qabul qilingan to'lovlar."""
    buckets = period_buckets(date_from, date_to, group_by)
    queryset = Payment.objects.filter(
        organization_id=organization_id,
        paid_at__date__gte=date_from,
        paid_at__date__lte=date_to,
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    by_period = _grouped_totals(
        queryset, "paid_at", group_by, total=Coalesce(Sum("amount"), ZERO), count=Count("id")
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
        "group_by": group_by,
        "total": _money(queryset.aggregate(t=Coalesce(Sum("amount"), ZERO))["t"]),
        "payment_count": queryset.count(),
        "by_period": [
            {
                "period": bucket.isoformat(),
                "total": _money(by_period.get(bucket, {}).get("total")),
                "count": by_period.get(bucket, {}).get("count", 0),
            }
            for bucket in buckets
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
    group_by: str = DEFAULT_GROUP_BY,
) -> dict[str, Any]:
    """
    Chiqimlar — faqat tasdiqlangan va to'langan.

    Kutilayotgan so'rov hali xarajat emas: uni qo'shish sarfni oshirib
    ko'rsatardi va byudjet qarorini buzardi (Sprint 7 bilan bir xil qoida).
    """
    buckets = period_buckets(date_from, date_to, group_by)
    queryset = Expense.objects.filter(
        organization_id=organization_id,
        expense_date__gte=date_from,
        expense_date__lte=date_to,
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    by_period = _grouped_totals(
        queryset, "expense_date", group_by, total=Coalesce(Sum("amount"), ZERO)
    )
    by_category = (
        queryset.values("category__name")
        .annotate(total=Coalesce(Sum("amount"), ZERO))
        .order_by("-total")
    )

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "group_by": group_by,
        "total": _money(queryset.aggregate(t=Coalesce(Sum("amount"), ZERO))["t"]),
        "by_period": [
            {
                "period": bucket.isoformat(),
                "total": _money(by_period.get(bucket, {}).get("total")),
            }
            for bucket in buckets
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
    group_by: str = DEFAULT_GROUP_BY,
) -> dict[str, Any]:
    """
    Foyda va zarar: daromad − chiqim − oylik.

    Bu **kassa usuli** (`basis: "cash"`): qabul qilingan pul minus
    to'langan/tasdiqlangan xarajat. Hisoblash usuli (accrual) boshqa
    raqam berardi va u buxgalteriya qarori — mijoz bilan kelishilishi
    kerak, taxmin qilinmasligi.

    **Oylik maosh — oylik ko'rsatkich.** U davr oyi bo'yicha hisoblanadi
    (`period_year`/`period_month`) va oy, chorak, yil kesimida o'z
    davriga tushadi. Kun va hafta kesimida esa qatorlarga TAQSIMLANMAYDI
    (`payroll_in_periods: false`): bir oylik maoshni 30 kunga bo'lib
    yoki oyning birinchi kuniga yozib qo'yish ikkalasi ham o'ylab
    topilgan raqam bo'lardi. Davr bo'yicha jami (`payroll`, `net`) esa
    kesimdan qat'i nazar bir xil qoladi.
    """
    buckets = period_buckets(date_from, date_to, group_by)
    revenue = revenue_report(
        organization_id=organization_id,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
        group_by=group_by,
    )
    expenses = expense_report(
        organization_id=organization_id,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
        group_by=group_by,
    )

    payroll_queryset = PayrollRun.objects.filter(
        organization_id=organization_id,
        status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
        period_year__gte=date_from.year,
        period_year__lte=date_to.year,
    )
    if branch_id:
        payroll_queryset = payroll_queryset.filter(branch_id=branch_id)

    payroll_in_periods = group_by in ("month", "quarter", "year")
    payroll_total = Decimal("0")
    payroll_by_period: dict[date, Decimal] = {}
    for run in payroll_queryset.values("period_year", "period_month", "total_gross"):
        period = date(run["period_year"], run["period_month"], 1)
        if not date_from.replace(day=1) <= period <= date_to:
            continue
        payroll_total += run["total_gross"]
        if payroll_in_periods:
            key = _bucket_start(period, group_by)
            payroll_by_period[key] = payroll_by_period.get(key, Decimal("0")) + run["total_gross"]

    revenue_by_period = {
        date.fromisoformat(row["period"]): Decimal(row["total"]) for row in revenue["by_period"]
    }
    expense_by_period = {
        date.fromisoformat(row["period"]): Decimal(row["total"]) for row in expenses["by_period"]
    }

    net = Decimal(revenue["total"]) - Decimal(expenses["total"]) - payroll_total

    rows = []
    for bucket in buckets:
        row_revenue = revenue_by_period.get(bucket, Decimal("0"))
        row_expenses = expense_by_period.get(bucket, Decimal("0"))
        row_payroll = payroll_by_period.get(bucket, Decimal("0"))
        rows.append(
            {
                "period": bucket.isoformat(),
                "revenue": _money(row_revenue),
                "expenses": _money(row_expenses),
                "payroll": _money(row_payroll),
                "net": _money(row_revenue - row_expenses - row_payroll),
            }
        )

    return {
        "basis": BASIS,
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "group_by": group_by,
        "payroll_in_periods": payroll_in_periods,
        "revenue": revenue["total"],
        "expenses": expenses["total"],
        "payroll": _money(payroll_total),
        "net": _money(net),
        "by_period": rows,
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
