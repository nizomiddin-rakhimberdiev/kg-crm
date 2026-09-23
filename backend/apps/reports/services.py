"""
Dashboard KPI to'plami (docs/04 §14.1).

Dashboard har bir kirishda ochiladi, shuning uchun u keshlanadi. Kesh
bilan bog'liq YAGONA muhim qoida shu faylda: **kalit tashkilot va filial
bilan boshlanadi.** Umumiy kalit boshqa bog'chaning daromadini ko'rsatib
qo'yardi — so'rov to'g'ri bo'lsa ham. Bu ma'lumotlar bazasidan sizib
chiqish emas, lekin ekranda ko'rgan odam uchun farqi yo'q.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from apps.finance.models import Payment
from apps.inventory.services import low_stock_products
from apps.reports import selectors

__all__ = ["dashboard_kpis", "invalidate_dashboard", "DASHBOARD_TTL"]

# Qisqa TTL ataylab: dashboard "hozir nima bo'lyapti" degan savolga javob
# beradi, va bir soatlik eski raqam bu savolga javob emas. Uzun TTL
# hisoblashni tejaydi, lekin foydalanuvchi to'lov qabul qilib, keyin uni
# ekranda ko'rmasa — keshga emas, tizimga ishonchi yo'qoladi.
DASHBOARD_TTL = 120


def _cache_key(*, organization_id: Any, branch_id: Any, finance: bool = True) -> str:
    # Moliya bayrog'i kalitning BIR QISMI: aks holda egasi uchun hisoblangan
    # to'liq javob keshdan tarbiyachiga ham berilardi (va aksincha).
    return f"dashboard:v2:{organization_id}:{branch_id or 'all'}:{'fin' if finance else 'nofin'}"


def invalidate_dashboard(*, organization_id: Any, branch_id: Any = None) -> None:
    """To'lov yoki chiqim yozilganda keshni bekor qiladi."""
    for finance in (True, False):
        cache.delete(
            _cache_key(organization_id=organization_id, branch_id=branch_id, finance=finance)
        )
        if branch_id is not None:
            cache.delete(
                _cache_key(organization_id=organization_id, branch_id=None, finance=finance)
            )


def dashboard_kpis(
    *, organization_id: Any, branch_id: Any = None, include_finance: bool = True
) -> dict[str, Any]:
    """
    Bir ekranga sig'adigan KPI to'plami.

    `include_finance=False` — pul ko'rsatkichlari javobga UMUMAN qo'shilmaydi
    (docs/02 §11.2: Davomat menejeri "No finance"). Ularni frontendda
    yashirish yetarli emas: ruxsati yo'q odam javobni baribir ko'ra olardi.
    """
    key = _cache_key(organization_id=organization_id, branch_id=branch_id, finance=include_finance)
    cached = cache.get(key)
    if cached is not None:
        return dict(cached, cached=True)

    today = timezone.localdate()
    month_start = today.replace(day=1)

    attendance = selectors.attendance_report(
        organization_id=organization_id, year=today.year, month=today.month
    )

    result: dict[str, Any] = {
        "date": today.isoformat(),
        "active_children": selectors.active_children_count(
            organization_id=organization_id, branch_id=branch_id
        ),
        "attendance_month_pct": attendance["attendance_rate"],
        "low_stock_count": len(
            low_stock_products(organization_id=organization_id, branch_id=branch_id)
        ),
        "cached": False,
    }

    if include_finance:
        payments = Payment.objects.filter(
            organization_id=organization_id,
            paid_at__date__gte=month_start,
            paid_at__date__lte=today,
        )
        if branch_id:
            payments = payments.filter(branch_id=branch_id)
        month_revenue = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")

        debtors = selectors.debtor_report(organization_id=organization_id, branch_id=branch_id)
        recent = (
            Payment.objects.filter(organization_id=organization_id)
            .select_related("child")
            .order_by("-paid_at")[:5]
        )
        result |= {
            "month_revenue": f"{month_revenue:.2f}",
            "outstanding_debt": debtors["total_outstanding"],
            "debtor_count": debtors["debtor_count"],
            "recent_payments": [
                {
                    "child": payment.child.full_name if payment.child else "—",
                    "amount": f"{payment.amount:.2f}",
                    "paid_at": payment.paid_at.isoformat(),
                }
                for payment in recent
            ],
            "revenue_trend": _revenue_trend(organization_id=organization_id, branch_id=branch_id),
        }

    cache.set(key, result, DASHBOARD_TTL)
    return result


def _month_start(value: date, *, back: int = 0) -> date:
    """`back` oy oldingi oyning birinchi kuni.

    Kun ayirish bilan hisoblash (31 × oy) 30 kunlik oylarda bir oy
    sakrab ketardi va qatorda ortiqcha ustun paydo bo'lardi.
    """
    total = value.year * 12 + (value.month - 1) - back
    return date(total // 12, total % 12 + 1, 1)


def _revenue_trend(
    *, organization_id: Any, branch_id: Any, months: int = 6
) -> list[dict[str, Any]]:
    """Oxirgi olti oy daromadi — grafik uchun."""
    today = timezone.localdate()
    start = _month_start(today, back=months - 1)
    report = selectors.revenue_report(
        organization_id=organization_id,
        date_from=start,
        date_to=today,
        branch_id=branch_id,
        group_by="month",
    )

    # Bo'sh oylar ham qatorda turadi — selektor davrlarni uzluksiz
    # qaytaradi (`period_buckets`): grafikda "hech kim to'lamagan oy"
    # yo'q bo'lib ketsa, tushish o'sish bo'lib ko'rinardi.
    return [{"month": row["period"][:7], "total": row["total"]} for row in report["by_period"]]
