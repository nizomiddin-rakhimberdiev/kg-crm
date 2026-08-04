"""
Moliya o'qish funksiyalari — jumladan **Qarzdorlar** (ADR-7, docs/03 §13.7).

`debtor` jadvali YO'Q va bo'lmaydi. Qarzdor — bu ledger balansi musbat
bo'lgan bola, ya'ni hisoblangan holat. Alohida jadval saqlansa, u ertami
kechmi ledger bilan mos kelmay qoladi va "qaysi biri to'g'ri?" degan
javobsiz savol paydo bo'ladi. Hisoblangan ro'yxat esa hech qachon
haqiqatdan ajralmaydi.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Case, DecimalField, F, OuterRef, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.children.models import Child
from apps.finance.models import Direction, Invoice, InvoiceStatus

__all__ = ["debtor_queryset", "debtor_rows", "child_statement"]


def debtor_queryset(*, min_amount: Decimal | None = None, overdue_only: bool = False) -> Any:
    """
    Balansi musbat bolalar — bitta so'rovda, ledger'dan hisoblangan.

    Balans annotatsiya sifatida hisoblanadi (`child.balance` keshidan
    EMAS): kesh siljigan bo'lsa, qarzdorlar ro'yxati ham noto'g'ri
    bo'lardi va bu eng yomon joyda — pul talab qilishda — chiqardi.

    ⚠️ **`oldest_overdue_date` ataylab `Subquery`, `Min()` emas.**

    Bitta `annotate()` ichida ikkita KO'P QIYMATLI bog'lanish bo'yicha
    agregat yozilsa (`ledger_entries` va `invoices`), SQL ularni bir-biriga
    ko'paytiradi: N ta ledger qatori × M ta faktura = N×M qator, va
    `Sum` M barobar oshib ketadi. Avval shunday edi — 4 oylik tarixi
    bor bola qarzi TO'RT BAROBAR ko'rinardi, ya'ni ota-onaga to'rt
    barobar ko'p summa haqida SMS ketardi.

    Testlar buni ko'rmadi, chunki har birida bolaga bitta faktura bor
    edi va ko'paytuvchi 1 ga teng bo'lgan. Demo ma'lumoti (4 oy tarix)
    uni birinchi urinishdayoq ochib berdi.
    """
    money: DecimalField = DecimalField(max_digits=12, decimal_places=2)

    overdue_invoices = (
        Invoice.objects.filter(
            child=OuterRef("pk"),
            status__in=[
                InvoiceStatus.ISSUED,
                InvoiceStatus.PARTIALLY_PAID,
                InvoiceStatus.OVERDUE,
            ],
            due_date__lt=timezone.localdate(),
        )
        .order_by("due_date")
        .values("due_date")[:1]
    )

    queryset = (
        Child.objects.filter(is_active=True)
        .annotate(
            ledger_balance=Coalesce(
                Sum(
                    Case(
                        When(
                            ledger_entries__direction=Direction.DEBIT,
                            then=F("ledger_entries__amount"),
                        ),
                        When(
                            ledger_entries__direction=Direction.CREDIT,
                            then=-1 * F("ledger_entries__amount"),
                        ),
                        output_field=money,
                    )
                ),
                Value(Decimal("0"), output_field=money),
            ),
            oldest_overdue_date=Subquery(overdue_invoices),
        )
        .filter(ledger_balance__gt=Decimal("0"))
    )

    if min_amount is not None:
        queryset = queryset.filter(ledger_balance__gte=min_amount)
    if overdue_only:
        queryset = queryset.filter(oldest_overdue_date__isnull=False)

    return queryset.order_by("-ledger_balance")


def debtor_rows(
    *, min_amount: Decimal | None = None, overdue_only: bool = False
) -> list[dict[str, Any]]:
    """Qarzdorlar ro'yxati — API javobiga tayyor shaklda (docs/04 §10)."""
    children = debtor_queryset(min_amount=min_amount, overdue_only=overdue_only).prefetch_related(
        "guardian_links__guardian", "enrollments__group"
    )

    rows: list[dict[str, Any]] = []
    for child in children:
        primary = next(
            (link for link in child.guardian_links.all() if link.is_primary),
            next(iter(child.guardian_links.all()), None),
        )
        group = next(
            (
                enrollment.group
                for enrollment in child.enrollments.all()
                if enrollment.end_date is None and enrollment.status == "active"
            ),
            None,
        )
        rows.append(
            {
                "child": {
                    "id": str(child.id),
                    "full_name": child.full_name,
                    "group": group.name if group else None,
                },
                "balance": str(child.ledger_balance),
                "oldest_overdue_date": (
                    child.oldest_overdue_date.isoformat() if child.oldest_overdue_date else None
                ),
                "primary_guardian": (
                    {
                        "full_name": primary.guardian.full_name,
                        "phone": primary.guardian.phone,
                    }
                    if primary
                    else None
                ),
            }
        )
    return rows


def child_statement(*, child: Child, limit: int = 100) -> dict[str, Any]:
    """
    Bolaning moliyaviy ko'chirmasi — ledger yozuvlari va yugurib boruvchi balans.

    Yugurib boruvchi balans eng eskisidan boshlab hisoblanadi: ota-ona
    "qayerdan bunday summa chiqdi?" deb so'raganda javob shu ro'yxatda
    ko'rinishi kerak.
    """
    entries = list(child.ledger_entries.order_by("occurred_at", "created_at")[:limit])

    running = Decimal("0")
    lines: list[dict[str, Any]] = []
    for entry in entries:
        running += entry.signed_amount
        lines.append(
            {
                "id": str(entry.id),
                "occurred_at": entry.occurred_at.isoformat(),
                "entry_type": entry.entry_type,
                "direction": entry.direction,
                "amount": str(entry.amount),
                "description": entry.description,
                "running_balance": str(running),
            }
        )

    open_invoices = list(
        Invoice.objects.filter(child=child)
        .exclude(status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED])
        .values("id", "number", "amount_due", "amount_paid", "due_date", "status")
    )

    return {
        "child": {"id": str(child.id), "full_name": child.full_name},
        "balance": str(running),
        "entries": lines,
        "open_invoices": [
            {
                **row,
                "id": str(row["id"]),
                "amount_due": str(row["amount_due"]),
                "amount_paid": str(row["amount_paid"]),
                "due_date": row["due_date"].isoformat(),
            }
            for row in open_invoices
        ],
    }
