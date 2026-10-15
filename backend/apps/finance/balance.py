"""
Bolaning balansi — YAGONA hisob (PLAN 1.1).

**Nega bu fayl bor.** 2026-09-30 auditida bitta bola To'lovlar doskasida
1 500 000, Qarzdorlar ro'yxatida esa 130 000 qarzdor ko'rindi. Ikkala
raqam ham to'g'ri hisoblangan edi — faqat ular ikki xil formuladan
kelardi: biri ledger'dan (`Σ debet − Σ kredit`), ikkinchisi faktura
keshidan (`amount_due − amount_paid`). Formula ikkita bo'lsa, ular
ertami-kechmi ajraladi; va pul haqidagi ekranlarda bu shunchaki xato
emas, ishonchning yo'qolishi.

Shuning uchun formula shu yerda va FAQAT shu yerda yashaydi. Doska,
to'lov oynasi, qarzdorlar, bosh sahifa, brifing, bola kartasi, hisobot
va eksport — hammasi shu fayldan o'qiydi.

Uchta raqam va ularning farqi:

| Raqam | Savol | Formula |
|---|---|---|
| `balance` | Oila bizga qancha qarz? | `Σ debet − Σ kredit` (ledger) |
| `advance` | Qo'limizda uning qancha puli bor? | `Σ to'lov − Σ taqsimot` |
| `outstanding` | Ochiq hujjatlarda qancha qoldi? | `Σ (amount_due − amount_paid)` |

Ular BIR XIL raqam emas va bo'lishi ham shart emas: bolada bir vaqtning
o'zida yopilmagan sentabr fakturasi ham, oktabr uchun oldindan berilgan
pul ham bo'lishi mumkin. Ekran qaysi savolga javob berayotganini bilishi
kerak — shuning uchun uchalasi ham nomlangan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Case, DecimalField, F, OuterRef, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.finance.models import (
    ChildLedgerEntry,
    Direction,
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentAllocation,
)

__all__ = [
    "ChildBalance",
    "MONEY",
    "ZERO",
    "OPEN_STATUSES",
    "ledger_balance_subquery",
    "advance_subquery",
    "overdue_subquery",
    "oldest_overdue_subquery",
    "with_balance",
    "child_balance",
    "open_months",
]

MONEY: DecimalField = DecimalField(max_digits=14, decimal_places=2)
ZERO = Value(Decimal("0"), output_field=MONEY)

#: Pul hali to'liq qoplamagan hujjat.
OPEN_STATUSES = (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE)


# --- Subquery'lar -----------------------------------------------------
#
# ⚠️ Hammasi `Subquery`, `annotate(Sum(...))` EMAS.
#
# Bitta `annotate()` ichida ikkita KO'P QIYMATLI bog'lanish bo'yicha
# agregat yozilsa, SQL ularni bir-biriga ko'paytiradi: N ta ledger
# qatori × M ta faktura = N×M qator va `Sum` M barobar oshib ketadi.
# Loyihada bu bir marta bo'lgan — 4 oylik tarixi bor bolaning qarzi
# TO'RT BAROBAR ko'ringan va ota-onaga to'rt barobar ko'p summa haqida
# SMS ketishiga bir qadam qolgan edi. Testlar ko'rmagan, chunki har
# birida bolaga bitta faktura bor edi va ko'paytuvchi 1 ga teng edi.


def ledger_balance_subquery() -> Any:
    """`Σ debet − Σ kredit` — musbat bo'lsa oila qarzdor."""
    return (
        ChildLedgerEntry.objects.filter(child=OuterRef("pk"))
        .values("child")
        .annotate(
            total=Sum(
                Case(
                    When(direction=Direction.DEBIT, then=F("amount")),
                    default=-F("amount"),
                    output_field=MONEY,
                )
            )
        )
        .values("total")
    )


def advance_subquery() -> Any:
    """
    Taqsimlanmagan pul — `Σ to'lov − Σ taqsimot`.

    Ikki manba bitta `annotate()` da bo'lgani uchun ikkalasi ham alohida
    `Subquery` bo'lishi SHART (yuqoridagi izoh).
    """
    paid = (
        Payment.objects.filter(child=OuterRef("pk"), reversed_at__isnull=True)
        .values("child")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    allocated = (
        PaymentAllocation.objects.filter(payment__child=OuterRef("pk"), released_at__isnull=True)
        .values("payment__child")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    return Coalesce(Subquery(paid, output_field=MONEY), ZERO) - Coalesce(
        Subquery(allocated, output_field=MONEY), ZERO
    )


def overdue_subquery(*, today: date | None = None) -> Any:
    """Muddati o'tgan ochiq hujjatlardagi qoldiq."""
    today = today or timezone.localdate()
    return (
        Invoice.objects.filter(child=OuterRef("pk"), status__in=OPEN_STATUSES, due_date__lt=today)
        .values("child")
        .annotate(total=Sum(F("amount_due") - F("amount_paid"), output_field=MONEY))
        .values("total")
    )


def oldest_overdue_subquery(*, today: date | None = None) -> Any:
    """Eng eski o'tib ketgan muddat — "necha kun kechikdi" shundan chiqadi."""
    today = today or timezone.localdate()
    return (
        Invoice.objects.filter(child=OuterRef("pk"), status__in=OPEN_STATUSES, due_date__lt=today)
        .order_by("due_date")
        .values("due_date")[:1]
    )


def with_balance(queryset: Any, *, today: date | None = None) -> Any:
    """
    Bolalar queryset'iga standart pul maydonlarini qo'shadi.

    Har bir ro'yxat ekrani shu funksiyadan o'tadi — shuning uchun
    "qarz" ustuni qayerda bo'lsa ham bitta formuladan keladi.
    """
    return queryset.annotate(
        ledger_balance=Coalesce(Subquery(ledger_balance_subquery(), output_field=MONEY), ZERO),
        advance=advance_subquery(),
        overdue_amount=Coalesce(Subquery(overdue_subquery(today=today), output_field=MONEY), ZERO),
        oldest_overdue_date=Subquery(oldest_overdue_subquery(today=today)),
    )


# --- Bitta bola -------------------------------------------------------


@dataclass(frozen=True)
class ChildBalance:
    """Bitta bolaning puli — bola kartasi va to'lov oynasi uchun."""

    child_id: str
    charged: Decimal
    credited: Decimal
    paid: Decimal
    allocated: Decimal
    advance: Decimal
    balance: Decimal
    overdue_amount: Decimal
    oldest_overdue_date: date | None
    open_invoices: int

    @property
    def outstanding(self) -> Decimal:
        """Qarz — manfiy balans qarz emas, u avans."""
        return max(self.balance, Decimal("0.00"))

    @property
    def overdue_days(self) -> int:
        if self.oldest_overdue_date is None:
            return 0
        return (timezone.localdate() - self.oldest_overdue_date).days

    def as_dict(self) -> dict[str, Any]:
        return {
            "child_id": self.child_id,
            "charged": f"{self.charged:.2f}",
            "credited": f"{self.credited:.2f}",
            "paid": f"{self.paid:.2f}",
            "allocated": f"{self.allocated:.2f}",
            "advance": f"{self.advance:.2f}",
            "balance": f"{self.balance:.2f}",
            "outstanding": f"{self.outstanding:.2f}",
            "overdue_amount": f"{self.overdue_amount:.2f}",
            "overdue_days": self.overdue_days,
            "oldest_overdue_date": (
                self.oldest_overdue_date.isoformat() if self.oldest_overdue_date else None
            ),
            "open_invoices": self.open_invoices,
        }


def child_balance(child: Any, *, today: date | None = None) -> ChildBalance:
    """Bitta bolaning to'liq moliyaviy manzarasi — bitta joydan."""
    today = today or timezone.localdate()

    charged = ChildLedgerEntry.objects.filter(child=child, direction=Direction.DEBIT).aggregate(
        total=Coalesce(Sum("amount"), ZERO)
    )["total"]
    credited = ChildLedgerEntry.objects.filter(child=child, direction=Direction.CREDIT).aggregate(
        total=Coalesce(Sum("amount"), ZERO)
    )["total"]
    paid = Payment.objects.filter(child=child, reversed_at__isnull=True).aggregate(
        total=Coalesce(Sum("amount"), ZERO)
    )["total"]
    allocated = PaymentAllocation.objects.filter(
        payment__child=child, released_at__isnull=True
    ).aggregate(total=Coalesce(Sum("amount"), ZERO))["total"]

    open_invoices = Invoice.objects.filter(child=child, status__in=OPEN_STATUSES)
    overdue = open_invoices.filter(due_date__lt=today).aggregate(
        total=Coalesce(Sum(F("amount_due") - F("amount_paid"), output_field=MONEY), ZERO)
    )["total"]
    oldest = (
        open_invoices.filter(due_date__lt=today)
        .order_by("due_date")
        .values_list("due_date", flat=True)
        .first()
    )

    return ChildBalance(
        child_id=str(child.id),
        charged=charged,
        credited=credited,
        paid=paid,
        allocated=allocated,
        advance=paid - allocated,
        balance=charged - credited,
        overdue_amount=overdue,
        oldest_overdue_date=oldest,
        open_invoices=open_invoices.count(),
    )


def open_months(child: Any) -> list[dict[str, Any]]:
    """
    Qarz oyma-oy — bola kartasi uchun (Bosqich 12.3, brif §3).

    "Jami qarz 5 100 000" yetarli emas: mudira va ota-ona "qaysi oylar
    uchun?" deb so'raydi. Har bir ochiq hujjatning qoldig'i — xuddi shu
    fayldagi boshqa formulalar kabi `amount_due − amount_paid`.
    """
    rows = (
        Invoice.objects.filter(child=child, status__in=OPEN_STATUSES)
        .order_by("period_year", "period_month")
        .values(
            "id", "number", "period_year", "period_month", "amount_due", "amount_paid", "due_date"
        )
    )
    return [
        {
            "invoice_id": str(row["id"]),
            "number": row["number"],
            "period": f"{row['period_year']}-{row['period_month']:02d}",
            "amount_due": f"{row['amount_due']:.2f}",
            "paid": f"{row['amount_paid']:.2f}",
            "outstanding": f"{row['amount_due'] - row['amount_paid']:.2f}",
            "due_date": row["due_date"].isoformat(),
        }
        for row in rows
    ]
