"""
Moliya o'qish funksiyalari — jumladan **Qarzdorlar** (ADR-7, docs/03 §13.7).

`debtor` jadvali YO'Q va bo'lmaydi. Qarzdor — bu ledger balansi musbat
bo'lgan bola, ya'ni hisoblangan holat. Alohida jadval saqlansa, u ertami
kechmi ledger bilan mos kelmay qoladi va "qaysi biri to'g'ri?" degan
javobsiz savol paydo bo'ladi. Hisoblangan ro'yxat esa hech qachon
haqiqatdan ajralmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import (
    Count,
    DecimalField,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy

from apps.children.models import (
    Child,
    Enrollment,
    EnrollmentState,
    EnrollmentStatus,
)
from apps.finance import balance
from apps.finance.models import Invoice, InvoiceStatus

__all__ = [
    "ChildPrice",
    "child_monthly_price",
    "debtor_queryset",
    "debtor_rows",
    "child_statement",
    "board_children",
    "month_board_queryset",
    "month_board_summary",
    "board_row",
    "BOARD_STATUSES",
    "recent_invoices",
    "recent_payments",
    "open_invoices_fifo",
]


def debtor_queryset(
    *,
    min_amount: Decimal | None = None,
    overdue_only: bool = False,
    min_days: int | None = None,
    group_id: Any = None,
) -> Any:
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
    if min_days is not None:
        # "15+ kun", "30+ kun" filtrlari (PLAN 3.5). Sana bo'yicha
        # taqqoslash kunlarni Python'da sanashdan tez va indeksdan
        # foydalanadi: eng eski muddati shu sanadan OLDIN bo'lsa,
        # kechikish shuncha kundan ko'p.
        queryset = queryset.filter(
            oldest_overdue_date__isnull=False,
            oldest_overdue_date__lte=timezone.localdate() - timedelta(days=min_days),
        )
    if group_id:
        queryset = queryset.filter(
            enrollments__group_id=group_id,
            enrollments__status=EnrollmentState.ACTIVE,
            enrollments__end_date__isnull=True,
        )

    return queryset.order_by("-ledger_balance")


def debtor_rows(
    *,
    min_amount: Decimal | None = None,
    overdue_only: bool = False,
    min_days: int | None = None,
    group_id: Any = None,
    order_by: str = "debt",
) -> list[dict[str, Any]]:
    """Qarzdorlar ro'yxati — API javobiga tayyor shaklda (docs/04 §10)."""
    from apps.notifications.selectors import last_reminders

    children = list(
        debtor_queryset(
            min_amount=min_amount,
            overdue_only=overdue_only,
            min_days=min_days,
            group_id=group_id,
        ).prefetch_related("guardian_links__guardian", "enrollments__group")
    )

    # Oxirgi eslatma — BITTA so'rovda (PLAN 3.5). Qator-qator so'rash
    # 200 qarzdor uchun 200 ta so'rovga aylanardi.
    guardian_ids = [
        link.guardian_id
        for child in children
        for link in child.guardian_links.all()
        if link.guardian_id
    ]
    reminded_at = last_reminders(guardian_ids=guardian_ids)
    today = timezone.localdate()

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
                # Kechikkan kunlar — ekranda hisoblanmaydi: "qancha
                # kechikdi?" degan savolga javob bitta joydan chiqsin,
                # aks holda hisobot bilan ekran farq qila boshlaydi.
                "days_overdue": (
                    (today - child.oldest_overdue_date).days if child.oldest_overdue_date else None
                ),
                "primary_guardian": (
                    {
                        "full_name": primary.guardian.full_name,
                        "phone": primary.guardian.phone,
                    }
                    if primary
                    else None
                ),
                "last_reminder_at": (
                    reminded_at[primary.guardian_id].isoformat()
                    if primary and reminded_at.get(primary.guardian_id)
                    else None
                ),
            }
        )

    # Saralash: qarz bo'yicha (sukut), kechikish yoki ism bo'yicha.
    if order_by == "days":
        rows.sort(key=lambda row: row["days_overdue"] or 0, reverse=True)
    elif order_by == "name":
        rows.sort(key=lambda row: row["child"]["full_name"])
    return rows


def _period_bounds(date_from: Any, date_to: Any) -> tuple[tuple[int, int], tuple[int, int]]:
    return (date_from.year, date_from.month), (date_to.year, date_to.month)


def debt_by_period(
    *,
    date_from: Any,
    date_to: Any,
    branch_id: Any = None,
    group_id: Any = None,
) -> list[dict[str, Any]]:
    """
    Oy boʻyicha qarzdorlik yoshi (PLAN 9.2).

    Savol — "qaysi oyning qarzi qolgan?" — balansdan javob olmaydi:
    balans bitta son, u qaysi oydan qolganini bilmaydi. Javob
    hisob-fakturada (`period_year/period_month`) va taqsimotda
    (`payment_allocation`): oktabrda kelgan pul SENTABRNING
    fakturasini yopgan boʻlsa, u sentabr qatorida koʻrinadi (ADR-20).

    Shuning uchun bu yerda `invoice.amount_paid` keshi emas, taqsimot
    jadvali oʻqiladi — kesh bir kun siljisa, hisobot haqiqatdan
    ajralib qolardi.
    """
    from apps.finance.models import PaymentAllocation

    (from_year, from_month), (to_year, to_month) = _period_bounds(date_from, date_to)
    invoices = Invoice.objects.exclude(status=InvoiceStatus.CANCELLED).filter(
        Q(period_year__gt=from_year) | Q(period_year=from_year, period_month__gte=from_month),
        Q(period_year__lt=to_year) | Q(period_year=to_year, period_month__lte=to_month),
    )
    if branch_id:
        invoices = invoices.filter(branch_id=branch_id)
    if group_id:
        invoices = invoices.filter(
            child__enrollments__group_id=group_id,
            child__enrollments__status=EnrollmentState.ACTIVE,
            child__enrollments__end_date__isnull=True,
        )

    # Toʻlangan summa — BOʻSHATILMAGAN taqsimotlardan. Qaytarilgan toʻlov
    # qatorni boʻshatadi, yaʼni qarz oʻz joyiga qaytadi.
    paid_rows = (
        PaymentAllocation.objects.filter(invoice__in=invoices, released_at__isnull=True)
        .values("invoice__period_year", "invoice__period_month")
        .annotate(
            paid=Coalesce(Sum("amount"), Decimal("0")),
            paid_late=Coalesce(
                Sum("amount", filter=Q(payment__paid_at__date__gt=F("invoice__due_date"))),
                Decimal("0"),
            ),
        )
    )
    paid_by_period = {
        (row["invoice__period_year"], row["invoice__period_month"]): row for row in paid_rows
    }

    rows: list[dict[str, Any]] = []
    grouped = (
        invoices.values("period_year", "period_month")
        .annotate(
            invoiced=Coalesce(Sum("amount_due"), Decimal("0")),
            children=Count("id", distinct=True),
        )
        .order_by("-period_year", "-period_month")
    )
    for row in grouped:
        key = (row["period_year"], row["period_month"])
        money = paid_by_period.get(key, {})
        paid = money.get("paid") or Decimal("0")
        outstanding = row["invoiced"] - paid
        debtors = sum(
            1
            for invoice in invoices.filter(period_year=key[0], period_month=key[1]).annotate(
                allocated=Coalesce(
                    Sum("allocations__amount", filter=Q(allocations__released_at__isnull=True)),
                    Decimal("0"),
                )
            )
            if invoice.amount_due - invoice.allocated > 0
        )
        rows.append(
            {
                "period": f"{key[0]:04d}-{key[1]:02d}",
                "period_year": key[0],
                "period_month": key[1],
                "invoiced": f"{row['invoiced']:.2f}",
                "paid": f"{paid:.2f}",
                "paid_late": f"{(money.get('paid_late') or Decimal('0')):.2f}",
                "outstanding": f"{outstanding:.2f}",
                "children": row["children"],
                "debtors": debtors,
            }
        )
    return rows


def debt_period_children(
    *,
    period_year: int,
    period_month: int,
    branch_id: Any = None,
    group_id: Any = None,
    debtors_only: bool = False,
) -> list[dict[str, Any]]:
    """
    Bitta oyning tafsiloti: kim qancha toʻladi, qachon, nima orqali, qancha qoldi.

    Toʻlovlar roʻyxati — taqsimotdan, yaʼni "shu oyni yopgan pul".
    Ota-onaning umumiy toʻlovlari emas: bir toʻlov ikki oyni yopsa, har
    oy oʻz ulushini koʻradi.
    """
    from apps.finance.models import PaymentAllocation

    invoices = (
        Invoice.objects.exclude(status=InvoiceStatus.CANCELLED)
        .filter(period_year=period_year, period_month=period_month)
        .select_related("child")
    )
    if branch_id:
        invoices = invoices.filter(branch_id=branch_id)
    if group_id:
        invoices = invoices.filter(
            child__enrollments__group_id=group_id,
            child__enrollments__status=EnrollmentState.ACTIVE,
            child__enrollments__end_date__isnull=True,
        )

    allocations = (
        PaymentAllocation.objects.filter(invoice__in=invoices, released_at__isnull=True)
        .select_related("payment")
        .order_by("payment__paid_at")
    )
    by_invoice: dict[Any, list[dict[str, Any]]] = {}
    for allocation in allocations:
        by_invoice.setdefault(allocation.invoice_id, []).append(
            {
                # MAHALLIY vaqt: toʻlov Toshkentda soat 00:30 da qabul
                # qilinsa, UTC da u KECHAGI kun boʻlib chiqadi va
                # hisobotdagi sana kassadagi chek bilan mos kelmasdi.
                "paid_at": timezone.localtime(allocation.payment.paid_at).isoformat(),
                "method": allocation.payment.method,
                "amount": f"{allocation.amount:.2f}",
                "payment_id": str(allocation.payment_id),
            }
        )

    today = timezone.localdate()
    rows: list[dict[str, Any]] = []
    for invoice in invoices:
        payments = by_invoice.get(invoice.id, [])
        paid = sum((Decimal(item["amount"]) for item in payments), Decimal("0"))
        outstanding = invoice.amount_due - paid
        if debtors_only and outstanding <= 0:
            continue
        rows.append(
            {
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.number,
                "child_id": str(invoice.child_id),
                "child_name": invoice.child.full_name,
                "invoiced": f"{invoice.amount_due:.2f}",
                "paid": f"{paid:.2f}",
                "outstanding": f"{outstanding:.2f}",
                "due_date": invoice.due_date.isoformat(),
                "days_overdue": (today - invoice.due_date).days if outstanding > 0 else 0,
                "payments": payments,
            }
        )
    rows.sort(key=lambda row: Decimal(row["outstanding"]), reverse=True)
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

    # Fakturasiz bolaning SABABI (audit, 2026-10-21). Ekran ilgari
    # sababni taxmin qilardi — "tarifi yo'q bo'lishi mumkin" — va
    # bolalarda individual narx bo'lganda bu noto'g'ri maslahat edi.
    # Narx manbai ikkita (`child_monthly_price`): tarif yoki
    # `monthly_fee`; ikkisi ham bo'lmasa fakturani chiqarib bo'lmaydi.
    without_price = (
        children_queryset.exclude(pk__in=invoices.values("child"))
        .filter(monthly_fee__isnull=True, tariff__isnull=True)
        .count()
    )

    return {
        "period_year": period_year,
        "period_month": period_month,
        "charged": f"{charged:.2f}",
        "paid": f"{paid:.2f}",
        "outstanding": f"{max(charged - paid, Decimal('0')):.2f}",
        "children": children,
        "with_invoice": with_invoice,
        "without_invoice": children - with_invoice,
        "without_price": without_price,
        "debtors": debtors,
    }


@dataclass(frozen=True)
class ChildPrice:
    """Bolaning oylik narxi va uning manbai."""

    amount: Decimal
    #: Tarif bo'yicha bo'lsa — tarif; individual narx bo'lsa — `None`.
    tariff: Any
    #: Hisob-faktura qatoridagi nom: tarif nomi yoki "Individual narx".
    label: str


def child_monthly_price(child: Any) -> ChildPrice | None:
    """
    Bola oyiga qancha to'laydi — YAGONA javob beradigan joy.

    Narx manbai ikkita bo'lishi mumkin: tarif yoki individual summa
    (`child.monthly_fee`). Baza ikkalasini birga qo'ymaydi
    (`ck_child_one_price_source`). Hech biri bo'lmasa — `None`: bunday
    bolaga hisob-faktura chiqarilmaydi.

    Hisob-faktura, kelmagan kunlar uchun kunlik stavka va ro'yxatlar shu
    funksiyani o'qiydi — narx qoidasi bir necha joyda takrorlansa, bir
    kun ular ajralib ketadi.
    """
    from django.utils.translation import gettext

    if child.monthly_fee is not None:
        return ChildPrice(
            amount=Decimal(child.monthly_fee), tariff=None, label=gettext("Individual narx")
        )
    if child.tariff_id is not None:
        tariff = child.tariff
        return ChildPrice(amount=Decimal(tariff.amount), tariff=tariff, label=tariff.name)
    return None


# --- The parent's view (PLAN 6.2) ---
#
# What the parent bot shows. Kept here so the bot never imports finance
# models (invariant 1); the debt itself always comes from `balance.py`.


def recent_invoices(child: Any, *, limit: int = 6) -> list[Invoice]:
    """The child's latest invoices, newest period first, cancelled ones included."""
    newest_first = ("-period_year", "-period_month", "-created_at")
    return list(Invoice.objects.filter(child=child).order_by(*newest_first)[:limit])


def recent_payments(child: Any, *, limit: int = 5) -> list[Any]:
    """The child's latest payments, reversed ones included (they are marked)."""
    from apps.finance.models import Payment

    return list(Payment.objects.filter(child=child).order_by("-paid_at", "-created_at")[:limit])


def open_invoices_fifo(child: Any) -> list[Invoice]:
    """Invoices still carrying an amount, in the order money settles them (ADR-20)."""
    return [
        invoice
        for invoice in Invoice.objects.filter(child=child)
        .exclude(status__in=[InvoiceStatus.PAID, InvoiceStatus.CANCELLED])
        .order_by("due_date", "created_at")
        if invoice.amount_paid < invoice.amount_due
    ]


def payroll_tuition_totals(
    *, employee_ids: Any, period_year: int, period_month: int
) -> dict[Any, Decimal]:
    """
    Oylikdan ushlanadigan bog'cha to'lovlari — xodim bo'yicha (Bosqich 12.4).

    Oylik moduli `payment` modelini o'zi o'qimaydi (invariant 1): u shu
    selektordan oladi. Davr — to'lov sanasi bo'yicha, avans kabi;
    qaytarilgan to'lov hisoblanmaydi.
    """
    from apps.finance.models import Payment, PaymentMethod

    rows = (
        Payment.objects.filter(
            method=PaymentMethod.PAYROLL,
            employee_id__in=list(employee_ids),
            reversed_at__isnull=True,
            paid_at__year=period_year,
            paid_at__month=period_month,
        )
        .values("employee_id")
        .annotate(total=Sum("amount"))
    )
    return {row["employee_id"]: row["total"] or Decimal("0") for row in rows}


# --- Oylik yig'ma (Bosqich 12.6, brif §6) ---

#: Toifa — fakturadagi imtiyoz qatoridan; rang yoki matndan emas.
_CATEGORY_LABELS = {
    "full": gettext_lazy("Toʻliq narx"),
    "sibling": gettext_lazy("Aka-uka"),
    "staff_child": gettext_lazy("Xodim farzandi"),
    "low_income": gettext_lazy("Kam taʼminlangan"),
    "full_benefit": gettext_lazy("Toʻliq imtiyoz"),
    "custom": gettext_lazy("Boshqa imtiyoz"),
    "pause": gettext_lazy("Vaqtincha toʻxtatilgan"),
    "no_invoice": gettext_lazy("Fakturasiz"),
}

_RECALC_LABELS = {
    "proration": gettext_lazy("Kelgan / ketgan / sinov"),
    "pause": gettext_lazy("Bir oylik ariza (pauza)"),
    "write_off": gettext_lazy("Hisobdan chiqarilgan"),
}


def _month_end(year: int, month: int) -> date:
    return date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)


def _category(lines: list[Any]) -> str:
    for line in lines:
        if line.kind == "pause":
            return "pause"
    for line in lines:
        if line.kind == "benefit":
            kind = line.benefit_kind or "custom"
            return "full_benefit" if kind == "full" else kind
    return "full"


def _month_invoices(
    *, organization_id: Any, branch_id: Any, year: int, month: int
) -> list[Invoice]:
    queryset = Invoice.objects.filter(
        organization_id=organization_id, period_year=year, period_month=month
    ).exclude(status=InvoiceStatus.CANCELLED)
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)
    return list(
        queryset.select_related("child").prefetch_related("lines__absence_claim").order_by("number")
    )


def monthly_summary(
    *, organization_id: Any, year: int, month: int, branch_id: Any = None
) -> dict[str, Any]:
    """
    Oyning yig'masi — bitta ekran, bitta raqamlar to'plami (brif §6).

    Ikki ko'rinish ataylab ALOHIDA:

    * `cash_received` — pul QAYSI OYDA kelgan (to'lov sanasi bo'yicha);
    * `collected_for_month` — pul QAYSI OY fakturasini yopgan
      (taqsimot bo'yicha), qachon kelganidan qat'i nazar.

    Bitta to'lov ikkalasida bittadan bo'ladi — ikki marta emas. Tenglik
    turli MANBALARNI solishtiradi (qatorlar, faktura keshi, taqsimot),
    shuning uchun u haqiqiy tekshiruv: kesh siljisa — qizil.
    """
    from apps.finance.models import MonthClose, Payment, PaymentAllocation

    zero = Decimal("0")
    start, end = date(year, month, 1), _month_end(year, month)
    invoices = _month_invoices(
        organization_id=organization_id, branch_id=branch_id, year=year, month=month
    )
    invoice_ids = [invoice.id for invoice in invoices]

    # --- Toifalar va hisoblangan summa ---
    categories: dict[str, dict[str, Any]] = {}
    recalcs: dict[str, dict[str, Any]] = {}
    charged = benefits = recalculated = lines_total = zero
    for invoice in invoices:
        lines = list(invoice.lines.all())
        key = _category(lines)
        row = categories.setdefault(
            key, {"children": 0, "charged": zero, "benefit": zero, "due": zero}
        )
        row["children"] += 1
        row["due"] += invoice.amount_due
        for line in lines:
            lines_total += line.line_total
            if line.kind == "base":
                row["charged"] += line.line_total
                charged += line.line_total
            elif line.kind == "benefit":
                row["benefit"] += line.line_total
                benefits += line.line_total
            else:
                if line.kind == "credit" and line.absence_claim is not None:
                    claim = line.absence_claim
                    bucket = f"{claim.kind}:{claim.basis or 'full_rate'}"
                    label = f"{claim.kind} — {claim.basis or 'full_rate'}"
                else:
                    bucket = line.kind or "other"
                    label = str(_RECALC_LABELS.get(bucket, bucket))
                entry = recalcs.setdefault(bucket, {"label": label, "count": 0, "amount": zero})
                entry["count"] += 1
                entry["amount"] += line.line_total
                recalculated += line.line_total

    invoiced_children = {invoice.child_id for invoice in invoices}
    roster = board_children(organization_id=organization_id, branch_id=branch_id).filter(
        Q(enrolled_on__isnull=True) | Q(enrolled_on__lte=end)
    )
    no_invoice = roster.exclude(pk__in=invoiced_children).count()
    if no_invoice:
        categories["no_invoice"] = {
            "children": no_invoice,
            "charged": zero,
            "benefit": zero,
            "due": zero,
        }

    # Qayta hisob turlarining nomi — arizalar turidan.
    from apps.attendance.models_absence import AbsenceKind

    kind_names = dict(
        AbsenceKind.objects.filter(organization_id=organization_id).values_list("code", "name")
    )
    basis_names = {
        "fixed_per_day": gettext("kuniga summa"),
        "full_rate": gettext("toʻliq stavka"),
        "none": gettext("qaytarilmaydi"),
    }
    for bucket, entry in recalcs.items():
        if ":" in bucket:
            code, basis = bucket.split(":", 1)
            entry["label"] = f"{kind_names.get(code, code)} — {basis_names.get(basis, basis)}"

    amount_due = sum((invoice.amount_due for invoice in invoices), zero)
    amount_paid = sum((invoice.amount_paid for invoice in invoices), zero)

    # --- Oy uchun yig'ilgan: taqsimot bo'yicha ---
    allocations = PaymentAllocation.objects.filter(
        invoice_id__in=invoice_ids, released_at__isnull=True
    ).select_related("payment")
    collected = before = during = after = zero
    collected_by_method: dict[str, Decimal] = {}
    for allocation in allocations:
        amount = allocation.amount
        collected += amount
        paid_on = timezone.localtime(allocation.payment.paid_at).date()
        if paid_on < start:
            before += amount
        elif paid_on > end:
            after += amount
        else:
            during += amount
        method = allocation.payment.method
        collected_by_method[method] = collected_by_method.get(method, zero) + amount

    # --- Kassa tushumi: to'lov sanasi bo'yicha ---
    payments = Payment.objects.filter(
        organization_id=organization_id,
        reversed_at__isnull=True,
        paid_at__date__gte=start,
        paid_at__date__lte=end,
    )
    if branch_id:
        payments = payments.filter(branch_id=branch_id)
    cash_by_method = {
        row["method"]: row["total"]
        for row in payments.values("method").annotate(total=Sum("amount")).order_by("method")
    }
    cash_total = sum(cash_by_method.values(), zero)
    # Shu oyda kelib, KEYINGI oylar fakturasini yopgan yoki hali hech
    # narsani yopmagan pul — keyingi oylar uchun avans.
    future_allocated = (
        PaymentAllocation.objects.filter(payment__in=payments, released_at__isnull=True)
        .filter(
            Q(invoice__period_year__gt=year)
            | Q(invoice__period_year=year, invoice__period_month__gt=month)
        )
        .aggregate(total=Sum("amount"))["total"]
        or zero
    )
    unallocated = cash_total - (
        PaymentAllocation.objects.filter(payment__in=payments, released_at__isnull=True).aggregate(
            total=Sum("amount")
        )["total"]
        or zero
    )
    advances = future_allocated + unallocated

    # --- Qarz: shu oy va eskilari (aging) ---
    outstanding = amount_due - amount_paid
    aging_qs = Invoice.objects.filter(
        organization_id=organization_id,
        status__in=[InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE],
    ).filter(Q(period_year__lt=year) | Q(period_year=year, period_month__lte=month))
    if branch_id:
        aging_qs = aging_qs.filter(branch_id=branch_id)
    aging = [
        {
            "period": f"{row['period_year']}-{row['period_month']:02d}",
            "outstanding": f"{row['due'] - row['paid']:.2f}",
            "children": row["children"],
        }
        for row in aging_qs.values("period_year", "period_month")
        .annotate(
            due=Sum("amount_due"), paid=Sum("amount_paid"), children=Count("child", distinct=True)
        )
        .order_by("-period_year", "-period_month")
        if row["due"] - row["paid"] > 0
    ]

    # --- Tenglik ---
    lines_ok = lines_total == amount_due
    allocation_ok = collected == amount_paid
    balance_ok = charged + benefits + recalculated == collected + outstanding
    check = {
        "ok": bool(lines_ok and allocation_ok and balance_ok),
        "lines_match_invoices": lines_ok,
        "allocations_match_paid": allocation_ok,
        "equation": f"{charged:.2f} + ({benefits:.2f}) + ({recalculated:.2f}) = "
        f"{collected:.2f} + {outstanding:.2f}",
        # Tenglikning qismlari ALOHIDA: ekran undan odam o'qiydigan
        # gap yasaydi. Ilgari faqat `equation` bor edi va ekranda xom
        # formula turardi — "5100000.00 + (0.00) + (-1159000.00)"
        # (audit, 2026-10-21).
        "parts": {
            "charged": f"{charged:.2f}",
            "benefits": f"{benefits:.2f}",
            "recalculated": f"{recalculated:.2f}",
            "collected": f"{collected:.2f}",
            "outstanding": f"{outstanding:.2f}",
        },
    }

    closed = None
    close_qs = MonthClose.objects.filter(
        organization_id=organization_id, period_year=year, period_month=month
    ).select_related("closed_by")
    if branch_id:
        close_qs = close_qs.filter(branch_id=branch_id)
    record = close_qs.first()
    if record is not None:
        closed = {
            "closed_at": record.created_at.isoformat(),
            "closed_by": record.closed_by.full_name if record.closed_by_id else "",
        }

    def money(value: Decimal) -> str:
        return f"{value:.2f}"

    return {
        "period": f"{year}-{month:02d}",
        "roster": len(invoiced_children) + no_invoice,
        "categories": [
            {
                "category": key,
                "label": str(_CATEGORY_LABELS.get(key, key)),
                "children": row["children"],
                "charged": money(row["charged"]),
                "benefit": money(row["benefit"]),
                "due": money(row["due"]),
            }
            for key, row in sorted(categories.items(), key=lambda item: -item[1]["children"])
        ],
        "invoiced": {
            "charged": money(charged),
            "benefits": money(benefits),
            "recalculations": money(recalculated),
            "amount_due": money(amount_due),
        },
        "benefits_total": money(benefits),
        "recalculations": [
            {
                "kind": key,
                "label": entry["label"],
                "count": entry["count"],
                "amount": money(entry["amount"]),
            }
            for key, entry in sorted(recalcs.items())
        ],
        "collected_for_month": {
            "total": money(collected),
            "before_month": money(before),
            "in_month": money(during),
            "after_month": money(after),
            "by_method": [
                {"method": method, "total": money(total)}
                for method, total in sorted(collected_by_method.items())
            ],
        },
        "cash_received": {
            "total": money(cash_total),
            "by_method": [
                {"method": method, "total": money(total)}
                for method, total in cash_by_method.items()
            ],
            "advances_for_later": money(advances),
        },
        "outstanding": money(outstanding),
        "aging": aging,
        "check": check,
        "closed": closed,
    }


def monthly_table_rows(
    *, organization_id: Any, year: int, month: int, branch_id: Any = None, **_: Any
) -> list[dict[str, Any]]:
    """
    Eski "oylik to'lov jadvali" ko'rinishi — o'tish davrida Excel bilan
    solishtirish uchun (brif §6). Bitta bola — bitta qator.
    """
    from apps.finance.models import PaymentAllocation

    invoices = _month_invoices(
        organization_id=organization_id, branch_id=branch_id, year=year, month=month
    )
    groups = dict(
        Child.objects.filter(
            pk__in=[invoice.child_id for invoice in invoices],
            enrollments__status=EnrollmentState.ACTIVE,
            enrollments__end_date__isnull=True,
        ).values_list("pk", "enrollments__group__name")
    )
    paid: dict[Any, dict[str, Decimal]] = {}
    dates: dict[Any, list[str]] = {}
    for allocation in (
        PaymentAllocation.objects.filter(invoice__in=invoices, released_at__isnull=True)
        .select_related("payment")
        .order_by("payment__paid_at")
    ):
        per = paid.setdefault(allocation.invoice_id, {})
        method = allocation.payment.method
        per[method] = per.get(method, Decimal("0")) + allocation.amount
        stamp = timezone.localtime(allocation.payment.paid_at).strftime("%d.%m")
        if stamp not in dates.setdefault(allocation.invoice_id, []):
            dates[allocation.invoice_id].append(stamp)

    rows = []
    for invoice in invoices:
        lines = list(invoice.lines.all())

        def total(predicate: Any, lines: list[Any] = lines) -> Decimal:
            return sum((line.line_total for line in lines if predicate(line)), Decimal("0"))

        methods = paid.get(invoice.id, {})
        rows.append(
            {
                "child": invoice.child.full_name,
                "group": groups.get(invoice.child_id) or "",
                "price": total(lambda line: line.kind == "base"),
                "benefit": total(lambda line: line.kind == "benefit"),
                "cash": methods.get("cash", Decimal("0")),
                "terminal": methods.get("terminal", Decimal("0")),
                "bank_transfer": methods.get("bank_transfer", Decimal("0")),
                "click": methods.get("click", Decimal("0")) + methods.get("online", Decimal("0")),
                "payme": methods.get("payme", Decimal("0")),
                "payroll": methods.get("payroll", Decimal("0")),
                "paid_dates": ", ".join(dates.get(invoice.id, [])),
                "medical": total(
                    lambda line: line.kind == "credit"
                    and line.absence_claim is not None
                    and line.absence_claim.kind == "medical"
                ),
                "application": total(
                    lambda line: line.kind == "credit"
                    and not (
                        line.absence_claim is not None and line.absence_claim.kind == "medical"
                    )
                ),
                "proration": total(lambda line: line.kind in ("proration", "pause")),
                "due": invoice.amount_due,
                "balance": invoice.amount_due - invoice.amount_paid,
            }
        )
    return rows


# --- Yo'ldagi pul (Bosqich 13.2c) ---


def in_transit(
    *,
    organization_id: Any,
    branch_id: Any = None,
    as_of: date | None = None,
    received_by_id: Any = None,
) -> list[dict[str, Any]]:
    """
    Bankka hali tushmagan terminal/Click/Payme to'lovlari.

    Kutilgan summa = to'lov − komissiya (komissiya chiqimi to'lovning o'zida,
    `expense.payment`); kutilgan sana = to'lov kuni + `transit.settle_days`.
    `as_of` — o'sha kun oxiridagi holat (oy oxiri balansi uchun).
    """
    from apps.cash.models import CashMovement
    from apps.expenses.models import Expense
    from apps.finance.models import TRANSIT_METHODS, Payment
    from apps.settings_app.services import get_setting

    day = as_of or timezone.localdate()
    payments = Payment.objects.filter(
        organization_id=organization_id,
        method__in=TRANSIT_METHODS,
        reversed_at__isnull=True,
        paid_at__date__lte=day,
    ).filter(Q(settlement__isnull=True) | Q(settlement__settled_on__gt=day))
    if branch_id:
        payments = payments.filter(branch_id=branch_id)
    if received_by_id:
        payments = payments.filter(received_by_id=received_by_id)
    payments = list(payments.select_related("child", "branch").order_by("paid_at"))
    ids = [payment.id for payment in payments]
    commissions = {
        row["payment"]: row["total"]
        for row in Expense.objects.filter(payment_id__in=ids)
        .values("payment")
        .annotate(total=Sum("amount"))
    }
    pots = dict(
        CashMovement.objects.filter(source_type="payment", source_id__in=ids).values_list(
            "source_id", "cash_account_id"
        )
    )
    today = timezone.localdate()
    days_cache: dict[Any, int] = {}
    rows = []
    for payment in payments:
        if payment.branch_id not in days_cache:
            days_cache[payment.branch_id] = int(
                get_setting(key="transit.settle_days", branch=payment.branch) or 0
            )
        paid_on = timezone.localtime(payment.paid_at).date()
        expected_on = paid_on + timedelta(days=days_cache[payment.branch_id])
        commission = commissions.get(payment.id) or Decimal("0")
        rows.append(
            {
                "payment_id": str(payment.id),
                "child": payment.child.full_name,
                "method": payment.method,
                "paid_on": paid_on.isoformat(),
                "amount": f"{payment.amount:.2f}",
                "commission": f"{commission:.2f}",
                "expected_amount": f"{payment.amount - commission:.2f}",
                "expected_on": expected_on.isoformat(),
                "overdue": expected_on < today,
                "cash_account_id": str(pots.get(payment.id) or ""),
            }
        )
    return rows
