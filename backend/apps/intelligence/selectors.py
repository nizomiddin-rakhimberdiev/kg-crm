"""
Radix Intelligence o'qish qatlami (docs/07 §11).

Bu yerda faqat AGREGAT so'rovlar: qoidalar uchun kirish ma'lumoti va
brifingning jonli tekshiruvlari. Hech qanday yozish yo'q. Tenant
konteksti chaqiruvchining ishi (vazifa `organization_context` ni o'zi
ochadi, view'ga DRF beradi) — bu yerda hamma so'rov tenant menejeri
ortida va RLS ostida ishlaydi.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from apps.attendance.models import AttendanceRecord
from apps.children.models import Enrollment, EnrollmentState
from apps.finance.models import Invoice
from apps.finance.selectors import debtor_queryset
from apps.intelligence.rules import OverdueChild
from apps.intelligence.thresholds import WORKING_DAYS
from apps.reports.selectors import active_children_count

__all__ = [
    "OPEN_INVOICE_STATUSES",
    "branch_ids_for",
    "overdue_children",
    "active_children",
    "attendance_completeness",
    "is_working_day",
]

# `overdue` ATAYLAB yo'q emas — u ham ochiq. Lekin qoida `status` ga
# tayanmaydi: `due_date` ga qaraydi (docs/07 §4, §13.1 — beat ishlamagan
# stekda 7 ta avgust fakturasi hali `issued` edi).
OPEN_INVOICE_STATUSES = ("issued", "partially_paid", "overdue")


def active_children(*, organization_id: Any, branch_id: Any) -> int:
    """Reports bilan BIR XIL ta'rif — ikki xil "faol" bo'lmasin."""
    return active_children_count(organization_id=organization_id, branch_id=branch_id)


def overdue_children(*, branch_id: Any, as_of: date, overdue_days: int) -> list[OverdueChild]:
    """
    Har bir bola bo'yicha: muddati `overdue_days` dan ko'p o'tgan va hali
    yopilmagan faktura qismlari yig'indisi, eng eskisi bo'yicha kechikish.

    Ikki manba, ikkita rol:

    * **Qarz bormi — LEDGER aytadi** (`debtor_queryset`, Debtors sahifasi
      bilan bir xil so'rov). Faktura `status`/`amount_paid` yetarli emas:
      kassir to'lovni fakturaga bog'lamasdan kiritsa (avans, "hammasiga"),
      faktura `issued` ligicha qoladi, ledger esa 0 ga tushadi. Faqat
      fakturaga qarab to'lab bo'lgan bolani "qarzdor" deb chiqarish —
      eng xijolatli false positive.
    * **Qancha kechikkan — FAKTURA aytadi.** Fakturaga bog'lanmagan pul
      FIFO bilan eng eskisiga yotqiziladi: 3 mln (avgust+sentabr) qarzdan
      1.5 mln to'langan bo'lsa, avgust yopilgan, sentabr 10 kun kechikkan —
      40 emas.

    Deep link Debtors'ga boradi — bu ro'yxat o'sha sahifaning qism
    to'plami bo'lishi SHART, aks holda "24 dedingiz, 20 ko'rinyapti".
    """
    cutoff = as_of - timedelta(days=overdue_days)

    balances: dict[Any, Decimal] = dict(
        debtor_queryset().filter(branch_id=branch_id).values_list("id", "ledger_balance")
    )
    if not balances:
        return []

    invoices: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for row in (
        Invoice.objects.filter(child_id__in=balances, status__in=OPEN_INVOICE_STATUSES)
        .order_by("due_date", "created_at")
        .values("child_id", "due_date", "amount_due", "amount_paid")
    ):
        invoices[row["child_id"]].append(row)

    child_ids = list(invoices)
    group_by_child: dict[Any, Any] = dict(
        Enrollment.objects.filter(
            child_id__in=child_ids, status=EnrollmentState.ACTIVE, end_date__isnull=True
        ).values_list("child_id", "group_id")
    )

    result: list[OverdueChild] = []
    for child_id, rows in invoices.items():
        outstanding = sum((r["amount_due"] - r["amount_paid"] for r in rows), Decimal("0"))
        # Fakturalar "qarz" deganidan ledger kamroq desa — farqi fakturasiz
        # to'langan pul. Uni eng eski fakturadan boshlab yopamiz.
        unallocated = max(outstanding - balances[child_id], Decimal("0"))
        overdue_amount = Decimal("0")
        oldest_due: date | None = None
        count = 0
        for r in rows:
            remaining = r["amount_due"] - r["amount_paid"]
            if unallocated >= remaining:
                unallocated -= remaining
                continue
            remaining -= unallocated
            unallocated = Decimal("0")
            if r["due_date"] < cutoff:
                overdue_amount += remaining
                count += 1
                oldest_due = oldest_due or r["due_date"]
        if count and oldest_due is not None:
            result.append(
                OverdueChild(
                    child_id=child_id,
                    group_id=group_by_child.get(child_id),
                    overdue_amount=overdue_amount,
                    days_overdue=(as_of - oldest_due).days,
                    invoices=count,
                )
            )
    return result


def is_working_day(day: date) -> bool:
    return day.weekday() in WORKING_DAYS


def attendance_completeness(*, branch_id: Any, day: date) -> dict[str, Any] | None:
    """
    Bugungi davomat BOLA darajasida: `recorded / expected`.

    `attendance_record` da `UNIQUE (child, attendance_date)` bor — bir bola,
    bir kun, bir qator baza kafolati. Shuning uchun bu nisbat aniq; guruh
    darajasidagi "bitta yozuv bormi" tekshiruvi esa yolg'on yashil berardi
    (docs/07 §11).

    Ish kuni bo'lmasa yoki faol bola bo'lmasa — `None` (tekshiruv
    yashiriladi), 0/0 emas.
    """
    if not is_working_day(day):
        return None

    expected_ids = set(
        Enrollment.objects.filter(
            child__branch_id=branch_id,
            child__is_active=True,
            status=EnrollmentState.ACTIVE,
            end_date__isnull=True,
        ).values_list("child_id", flat=True)
    )
    if not expected_ids:
        return None

    recorded = AttendanceRecord.objects.filter(
        attendance_date=day, child_id__in=expected_ids
    ).count()
    expected = len(expected_ids)
    return {
        "expected": expected,
        "recorded": recorded,
        "percent": round(recorded * 100 / expected),
        "complete": recorded >= expected,
    }


def branch_ids_for(organization_id: Any) -> list[Any]:
    """Tashkilotning faol filiallari — vazifa har biri uchun alohida yuradi."""
    from apps.branches.models import Branch

    return list(
        Branch.objects.filter(organization_id=organization_id, is_active=True)
        .order_by("created_at")
        .values_list("id", flat=True)
    )
