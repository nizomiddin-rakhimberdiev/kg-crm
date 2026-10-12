"""
Dashboard KPI to'plami (docs/04 §14.1).

Dashboard har bir kirishda ochiladi, shuning uchun u keshlanadi. Kesh
bilan bog'liq YAGONA muhim qoida shu faylda: **kalit tashkilot va filial
bilan boshlanadi.** Umumiy kalit boshqa bog'chaning daromadini ko'rsatib
qo'yardi — so'rov to'g'ri bo'lsa ham. Bu ma'lumotlar bazasidan sizib
chiqish emas, lekin ekranda ko'rgan odam uchun farqi yo'q.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from apps.finance.models import Payment
from apps.inventory.services import low_stock_products
from apps.reports import selectors

__all__ = [
    "dashboard_kpis",
    "invalidate_dashboard",
    "invalidate_dashboard_on_commit",
    "DASHBOARD_SECTIONS",
    "DASHBOARD_TTL",
]

# Qisqa TTL ataylab: dashboard "hozir nima bo'lyapti" degan savolga javob
# beradi, va bir soatlik eski raqam bu savolga javob emas. Uzun TTL
# hisoblashni tejaydi, lekin foydalanuvchi to'lov qabul qilib, keyin uni
# ekranda ko'rmasa — keshga emas, tizimga ishonchi yo'qoladi.
DASHBOARD_TTL = 120

# Dashboard bo'laklari va ularning ruxsatlari (docs/02 §11.2).
#
# Har bir bo'lak O'Z ruxsatini talab qiladi, chunki dashboard —
# boshqa joyda ko'rsa bo'ladigan ma'lumotning qisqartmasi, yangi
# kirish yo'li emas. Ruxsati yo'q bo'lakni frontendda yashirish
# yetarli emasdi: javobda u baribir ko'rinib turardi.
DASHBOARD_SECTIONS: dict[str, tuple[str, ...]] = {
    "children": ("children.read",),
    "attendance": ("attendance.read",),
    "inventory": ("inventory.read",),
    # Pul ko'rsatkichlari — to'lov yoki qarzdorlikni ko'rishga haqli rollarga.
    "finance": ("payments.read", "debtors.read"),
    # Kassa qoldig'i uchastalarning HAMMASI kerak: u tushum, chiqim va
    # oylik maoshni bitta raqamga yig'adi, ya'ni uchtasidan birortasiga
    # ruxsati yo'q odam undan qolganini chiqarib olardi.
    "cash": ("payments.read", "expenses.read", "payroll.read"),
    # Qaysi yo'l bilan qancha pul kelgani — faqat to'lov ma'lumoti,
    # shuning uchun bitta ruxsat yetarli (PLAN 7.3).
    "income_by_method": ("payments.read",),
}


def _version(organization_id: Any) -> int:
    """
    Kesh kalitidagi avlod raqami.

    Bo'laklar to'plami ruxsatga qarab o'zgargani uchun bitta tashkilotda
    o'nlab kalit bo'lishi mumkin — hammasini nomma-nom o'chirib
    bo'lmaydi. Raqamni oshirish esa eskilarini bir zarbada yaroqsiz
    qiladi va ular TTL bilan o'z-o'zidan yo'qoladi.
    """
    key = f"dashboard:ver:{organization_id}"
    version = cache.get(key)
    if version is None:
        version = 1
        cache.set(key, version, None)
    return int(version)


def _cache_key(*, organization_id: Any, branch_id: Any, sections: frozenset[str]) -> str:
    # Kalit tashkilot bilan BOSHLANADI: umumiy kalit boshqa bog'chaning
    # daromadini ko'rsatib qo'yardi — so'rov to'g'ri bo'lsa ham.
    parts = "+".join(sorted(sections)) or "none"
    return (
        f"dashboard:v3:{organization_id}:{_version(organization_id)}:{branch_id or 'all'}:{parts}"
    )


def invalidate_dashboard(*, organization_id: Any, branch_id: Any = None) -> None:
    """To'lov, chiqim yoki oylik yozilganda keshni bekor qiladi."""
    # `branch_id` ATAYLAB e'tiborga olinmaydi: filial ichidagi o'zgarish
    # tashkilot bo'yicha yig'indini ham o'zgartiradi, ya'ni ikkalasi ham
    # eskiradi. Avlod raqami ikkalasini ham bir yo'la yopadi.
    key = f"dashboard:ver:{organization_id}"
    try:
        cache.incr(key)
    except ValueError:
        # Kalit hali yo'q (yoki kesh tozalangan) — birinchi avloddan boshlaymiz.
        cache.set(key, 1, None)


def invalidate_dashboard_on_commit(*, organization_id: Any) -> None:
    """
    Pul, stok yoki davomat yozilganda keshni TRANZAKSIYA tugagach bekor qiladi.

    `invalidate_dashboard()` avval mavjud edi, lekin uni hech kim
    chaqirmasdi: to'lov yoki qaytarishdan keyin 120 soniya davomida
    dashboard eski qarzni, qarzdorlar ro'yxati esa yangisini ko'rsatardi.
    Endi u har bir ledger yozish nuqtasidan chaqiriladi — yangi endpoint
    uni "unutib" qo'ya olmaydi.

    `on_commit` — commit'dan OLDIN bekor qilinsa, parallel so'rov eski
    qiymatni qayta hisoblab yana keshga yozib qo'yishi mumkin edi.
    Tranzaksiyadan tashqarida darhol bajariladi.
    """
    from django.db import transaction

    transaction.on_commit(lambda: invalidate_dashboard(organization_id=organization_id))


def dashboard_kpis(
    *,
    organization_id: Any,
    branch_id: Any = None,
    sections: frozenset[str] | None = None,
) -> dict[str, Any]:
    """
    Bir ekranga sig'adigan KPI to'plami.

    `sections` — foydalanuvchi ko'rishga haqli bo'laklar
    (`DASHBOARD_SECTIONS` kalitlari). `None` = hammasi. Ruxsati yo'q
    bo'lak javobga UMUMAN qo'shilmaydi, frontendda yashirilmaydi:
    yashirish faqat ekranni tozalaydi, javobni emas.
    """
    allowed = frozenset(DASHBOARD_SECTIONS) if sections is None else frozenset(sections)
    key = _cache_key(organization_id=organization_id, branch_id=branch_id, sections=allowed)
    cached = cache.get(key)
    if cached is not None:
        return dict(cached, cached=True)

    today = timezone.localdate()
    month_start = today.replace(day=1)

    result: dict[str, Any] = {"date": today.isoformat(), "cached": False}

    if "children" in allowed:
        result["active_children"] = selectors.active_children_count(
            organization_id=organization_id, branch_id=branch_id
        )

    if "attendance" in allowed:
        attendance = selectors.attendance_report(
            organization_id=organization_id, year=today.year, month=today.month
        )
        result["attendance_month_pct"] = attendance["attendance_rate"]

    if "inventory" in allowed:
        result["low_stock_count"] = len(
            low_stock_products(organization_id=organization_id, branch_id=branch_id)
        )

    if "finance" in allowed:
        # Qaytarilgan to'lov tushum emas (`revenue_report` dagi izoh).
        payments = Payment.objects.filter(
            organization_id=organization_id,
            paid_at__date__gte=month_start,
            paid_at__date__lte=today,
            reversed_at__isnull=True,
        )
        if branch_id:
            payments = payments.filter(branch_id=branch_id)
        month_revenue = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")

        debtors = selectors.debtor_report(organization_id=organization_id, branch_id=branch_id)
        recent = (
            Payment.objects.filter(organization_id=organization_id, reversed_at__isnull=True)
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

    if "cash" in allowed:
        # "Ayni paytda qo'limizda qancha pul bor" — mijozning birinchi
        # savoli, va u dashboardda hech qayerda yo'q edi.
        result["cash"] = selectors.cash_position(
            organization_id=organization_id, branch_id=branch_id
        )

    if "income_by_method" in allowed:
        # "Qaysi yo'l bilan qancha pul kelgan" — shu oy kesimida
        # (PLAN 7.3). Ilgari bu faqat Hisobotlar sahifasida edi, mijoz
        # esa uni har kuni ochadigan ekranda ko'rishni so'radi.
        # Manba Hisobotlar bilan BIR XIL (`revenue_report`), aks holda
        # ikki ekran bir savolga ikki xil javob berardi.
        result["income_by_method"] = selectors.revenue_report(
            organization_id=organization_id,
            date_from=month_start,
            date_to=today,
            branch_id=branch_id,
        )["by_method"]

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


# --- Eksport fayllarini tozalash (PLAN 11.9) --------------------------


def purge_old_exports(*, days: int = 30, apply: bool = False) -> dict[str, Any]:
    """
    Eskirgan va yetim qolgan eksport fayllarini topadi (va oʻchiradi).

    **Nega kerak.** Eksport — vaqtinchalik hujjat: foydalanuvchi uni
    yuklab oladi va unutadi. Lekin uni hech narsa oʻchirmasdi, yaʼni
    `debtors-20260923-1001.csv` — oilalarning ismi va qarzi bilan —
    serverda cheksiz yotaverardi.

    Ikki xil axlat bor va ikkalasi ham tozalanadi:

    * **eskirgan** — `days` dan katta yoshdagi qator (fayli bilan);
    * **yetim** — `exports/` ichidagi, birorta qator ishora qilmaydigan
      fayl. Ular paydo boʻladi, chunki Django `queryset.delete()`
      `FileField` blobini OʻCHIRMAYDI: tashkilot tozalanganda qatorlar
      ketadi, fayl esa diskda qoladi. Bunday faylni ilova orqali hech
      kim yuklab ololmaydi — lekin u maʼlumotligicha qolaveradi.

    `apply=False` — faqat sanaydi.
    """
    from django.core.files.storage import default_storage

    from apps.core.tenancy import organization_context, platform_context
    from apps.organizations.models import Organization
    from apps.reports.models import ReportExport

    cutoff = timezone.now() - timedelta(days=days)

    with platform_context():
        organizations = list(Organization.objects.all())

    stale: list[Any] = []
    live_files: set[str] = set()
    for organization in organizations:
        with organization_context(organization.id):
            stale.extend(ReportExport.objects.filter(created_at__lt=cutoff))
            live_files.update(
                name for name in ReportExport.objects.values_list("file", flat=True) if name
            )

    doomed = {export.file.name for export in stale if export.file}
    orphans = sorted(_export_files(default_storage) - live_files - doomed)

    removed_files = 0
    if apply:
        for export in stale:
            with organization_context(export.organization_id):
                if export.file:
                    export.file.delete(save=False)
                    removed_files += 1
                export.delete()
        for name in orphans:
            default_storage.delete(name)
            removed_files += 1

    return {
        "rows": [
            {
                "created": export.created_at.date().isoformat(),
                "type": export.report_type,
                "file": export.file.name or "—",
            }
            for export in stale
        ],
        "orphans": orphans,
        "removed_rows": len(stale) if apply else 0,
        "removed_files": removed_files,
    }


def _export_files(storage: Any) -> set[str]:
    """`exports/` ichidagi barcha fayllar — papkalar boʻylab."""
    found: set[str] = set()
    stack = ["exports"]
    while stack:
        folder = stack.pop()
        try:
            subfolders, files = storage.listdir(folder)
        except (FileNotFoundError, NotImplementedError):
            continue
        stack.extend(f"{folder}/{sub}" for sub in subfolders)
        found.update(f"{folder}/{name}" for name in files)
    return found
