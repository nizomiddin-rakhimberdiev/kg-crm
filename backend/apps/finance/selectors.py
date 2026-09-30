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

from django.db.models import (
    DecimalField,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from apps.children.models import (
    Child,
    Enrollment,
    EnrollmentState,
    EnrollmentStatus,
)
from apps.finance import balance
from apps.finance.models import Invoice, InvoiceStatus

__all__ = [
    "debtor_queryset",
    "debtor_rows",
    "child_statement",
    "board_children",
    "month_board_queryset",
    "month_board_summary",
    "board_row",
    "BOARD_STATUSES",
]


def debtor_queryset(*, min_amount: Decimal | None = None, overdue_only: bool = False) -> Any:
    """
    Balansi musbat bolalar — bitta so'rovda.

    Formula BU YERDA EMAS: u `apps/finance/balance.py` da va u yerdan
    doska, bola kartasi, bosh sahifa va hisobotlar ham o'qiydi. Ikkita
    formula ertami-kechmi ajraladi — auditda aynan shunday bo'lgan
    (`docs/big-update/PLAN.md` §2).

    Balans annotatsiya sifatida hisoblanadi (`child.balance` keshidan
    EMAS): kesh siljigan bo'lsa, qarzdorlar ro'yxati ham noto'g'ri
    bo'lardi va bu eng yomon joyda — pul talab qilishda — chiqardi.
    """
    queryset = balance.with_balance(Child.objects.filter(is_active=True)).filter(
        ledger_balance__gt=Decimal("0")
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


# --- To'lov qabul qilish ekrani (docs/04 §9.7) ---
#
# Kassirning bitta ekrani: "shu oyda qaysi bola qancha to'lashi kerak".
#
# Nega alohida selektor kerak bo'ldi: ekran hisob-fakturalar ro'yxatiga
# tayanardi va u ikki sababdan noto'g'ri ishlardi. Birinchidan, faqat
# hisob-faktura CHIQARILGAN bolalar ko'rinardi. Ikkinchidan — va bu
# jiddiyroq — ro'yxat `page_size` siz so'ralar, ya'ni serverdan atigi
# 25 qator kelardi va sahifalash tugmasi ham yo'q edi: 41 bolali
# bog'chada 16 bola ekranda UMUMAN ko'rinmasdi va ulardan pul qabul
# qilib bo'lmasdi.
#
# Shuning uchun manba — BOLALAR ro'yxati, hisob-faktura esa unga
# chap tomondan qo'shiladi. Qidiruv, filtr va sahifalash serverda,
# ya'ni ekran bog'chaning kattaligiga bog'liq emas.

BOARD_STATUSES = ("debtor", "paid", "no_invoice")


def board_children(*, organization_id: Any, branch_id: Any = None) -> Any:
    """
    Ekranda ko'rinadigan bolalar — ro'yxat va yig'indi uchun BIR MANBA.

    Chiqib ketgan va bitirganlar chiqarib tashlanadi: ular endi pul
    to'lamaydi va kassirning ro'yxatini shovqinga to'ldirardi.
    """
    queryset = Child.objects.filter(organization_id=organization_id, is_active=True).exclude(
        enrollment_status__in=[EnrollmentStatus.WITHDRAWN, EnrollmentStatus.GRADUATED]
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)
    return queryset


def month_board_queryset(
    *,
    organization_id: Any,
    period_year: int,
    period_month: int,
    branch_id: Any = None,
    search: str = "",
    status: str = "",
) -> Any:
    """Bolalar + o'sha oyning hisob-fakturasi, bitta so'rovda."""
    money: DecimalField = DecimalField(max_digits=12, decimal_places=2)

    # ⚠️ Hammasi `Subquery` — `annotate()` ichida ikkita KO'P QIYMATLI
    # bog'lanish bo'yicha agregat yozilsa, SQL ularni bir-biriga
    # ko'paytiradi (`debtor_queryset` dagi izoh: qarz to'rt barobar
    # ko'rinib ketgan edi).
    invoices = (
        Invoice.objects.filter(
            child=OuterRef("pk"), period_year=period_year, period_month=period_month
        )
        .exclude(status=InvoiceStatus.CANCELLED)
        .order_by("-issued_date")
    )
    groups = Enrollment.objects.filter(
        child=OuterRef("pk"), status=EnrollmentState.ACTIVE
    ).order_by("-start_date")

    zero = Value(Decimal("0"), output_field=money)
    # Ledger balansi va avans — `balance.py` dagi YAGONA formuladan.
    queryset = (
        balance.with_balance(board_children(organization_id=organization_id, branch_id=branch_id))
        .annotate(
            invoice_id=Subquery(invoices.values("id")[:1]),
            invoice_number=Subquery(invoices.values("number")[:1]),
            invoice_status=Subquery(invoices.values("status")[:1]),
            charged=Coalesce(Subquery(invoices.values("amount_due")[:1], output_field=money), zero),
            paid=Coalesce(Subquery(invoices.values("amount_paid")[:1], output_field=money), zero),
            group_name=Subquery(groups.values("group__name")[:1]),
        )
        .annotate(outstanding=F("charged") - F("paid"))
    )

    if search:
        # Ism va familiya bo'yicha — kassir bolaning ismini yozadi,
        # hisob-faktura raqamini emas.
        queryset = queryset.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search))

    if status == "debtor":
        queryset = queryset.filter(outstanding__gt=0)
    elif status == "paid":
        queryset = queryset.filter(invoice_id__isnull=False, outstanding__lte=0)
    elif status == "no_invoice":
        queryset = queryset.filter(invoice_id__isnull=True)

    return queryset.order_by("last_name", "first_name")


def board_row(child: Any) -> dict[str, Any]:
    """Annotatsiyalangan bolani ekran kutadigan shaklga o'giradi."""
    outstanding = child.outstanding
    if child.invoice_id is None:
        state = "no_invoice"
    elif outstanding <= 0:
        state = "paid"
    elif child.paid > 0:
        state = "partial"
    else:
        state = "unpaid"

    return {
        "child_id": str(child.id),
        "child_name": child.full_name,
        "group_name": child.group_name or "",
        "invoice_id": str(child.invoice_id) if child.invoice_id else None,
        "invoice_number": child.invoice_number or "",
        "charged": f"{child.charged:.2f}",
        "paid": f"{child.paid:.2f}",
        "outstanding": f"{max(outstanding, Decimal('0')):.2f}",
        "state": state,
        # Manfiy balans — bog'cha oilaga qarzdor, ya'ni avans bor.
        # Kassir buni to'lov qabul qilishdan OLDIN ko'rishi kerak.
        "balance": f"{child.ledger_balance:.2f}",
        # Taqsimlanmagan pul — "bu bolaning kassamizda qancha puli bor".
        # Balansdan ALOHIDA: bolada bir vaqtda yopilmagan faktura ham,
        # keyingi oy uchun berilgan pul ham bo'lishi mumkin.
        "advance": f"{max(child.advance, Decimal('0')):.2f}",
    }


def month_board_summary(
    *,
    organization_id: Any,
    period_year: int,
    period_month: int,
    branch_id: Any = None,
) -> dict[str, Any]:
    """
    Oyning yakuni — SAHIFADAN qat'i nazar.

    Ilgari yuqoridagi "jami" faqat yuklangan 25 qatordan hisoblanardi,
    ya'ni har doim kam ko'rsatardi.

    **Yig'indi annotatsiya ustidan emas, hisob-fakturalardan olinadi.**
    `Sum("charged")` — bu `Subquery` annotatsiyasi ustidan agregat, va
    Django uni SQL ga tushira olmaydi ("column charged does not
    exist"). Bevosita `Invoice` ustidan yig'ish soddaroq ham, tezroq ham.
    """
    children_queryset = board_children(organization_id=organization_id, branch_id=branch_id)
    invoices = Invoice.objects.filter(
        child__in=children_queryset, period_year=period_year, period_month=period_month
    ).exclude(status=InvoiceStatus.CANCELLED)

    money: DecimalField = DecimalField(max_digits=14, decimal_places=2)
    zero = Value(Decimal("0"), output_field=money)
    totals = invoices.aggregate(
        charged=Coalesce(Sum("amount_due"), zero),
        paid=Coalesce(Sum("amount_paid"), zero),
    )
    charged = totals["charged"]
    paid = totals["paid"]

    children = children_queryset.count()
    with_invoice = invoices.values("child").distinct().count()
    debtors = invoices.filter(amount_paid__lt=F("amount_due")).values("child").distinct().count()

    return {
        "period_year": period_year,
        "period_month": period_month,
        "charged": f"{charged:.2f}",
        "paid": f"{paid:.2f}",
        "outstanding": f"{max(charged - paid, Decimal('0')):.2f}",
        "children": children,
        "with_invoice": with_invoice,
        "without_invoice": children - with_invoice,
        "debtors": debtors,
    }
