"""Chiqim tasdiqlash oqimi (docs/03 §16.2)."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext

from apps.cash import services as cash
from apps.cash.models import MovementDirection, MovementSource
from apps.core.exceptions import BusinessRuleViolation
from apps.expenses.models import Expense, ExpenseCategory, ExpenseItem, ExpenseStatus

__all__ = [
    "update_expense",
    "approve_expense",
    "reject_expense",
    "mark_expense_paid",
    "expense_summary",
    "create_expense_with_items",
]


def _assert_pending(expense: Expense, action: str) -> None:
    if expense.status != ExpenseStatus.PENDING:
        raise BusinessRuleViolation(
            gettext("Chiqim '{status}' holatida — {action} mumkin emas.").format(
                status=expense.get_status_display(), action=action
            )
        )


@transaction.atomic
def create_expense_with_items(
    *,
    organization: Any,
    branch: Any,
    category: Any,
    expense_date: Any,
    items: list[dict[str, Any]],
    description: str = "",
    cash_account: Any = None,
    allow_negative: bool = False,
    created_by: Any = None,
    **extra: Any,
) -> Expense:
    """
    Qatorlardan chiqim yaratadi va DARHOL tasdiqlaydi (PLAN 7.5, 7.2).

    `extra` — Bosqich 13.2a maydonlari (tegishli oy, investitsiya, nasiya).

    Summa qatorlardan hisoblanadi, mijozdan OLINMAYDI: ekranda
    ko'rsatilgan yig'indi bilan kassadan chiqqan pul har doim bir xil
    bo'lishi kerak. Mijoz yuborgan summaga ishonilsa, ular bir kun
    ajralib qolardi va buni hech kim sezmasdi.

    Har bir qator uchun `line_total = miqdor × narx` shu yerda
    hisoblanib SAQLANADI (modeldagi izoh).
    """
    rows, total = _build_items(organization=organization, branch=branch, items=items)

    expense = Expense.objects.create(
        organization=organization,
        branch=branch,
        category=category,
        amount=total,
        expense_date=expense_date,
        description=description[:255],
        cash_account=cash_account,
        **extra,
    )
    for row in rows:
        row.expense = expense
    ExpenseItem.objects.bulk_create(rows)

    return approve_expense(
        expense=expense,
        approved_by=created_by,
        cash_account=cash_account,
        allow_negative=allow_negative,
    )


def _build_items(
    *, organization: Any, branch: Any, items: list[dict[str, Any]]
) -> tuple[list[ExpenseItem], Decimal]:
    """
    Qatorlardan saqlanmagan `ExpenseItem` lar va ularning yig'indisi.

    Yaratish ham, tahrirlash ham shu yerdan o'tadi: `line_total` va jami
    bitta joyda hisoblanadi, aks holda ikki yo'l bir kun bir-biridan
    ajralib qolardi.
    """
    if not items:
        raise BusinessRuleViolation(gettext("Chiqimda kamida bitta qator boʻlishi kerak."))

    rows: list[ExpenseItem] = []
    total = Decimal("0")
    for item in items:
        quantity = Decimal(str(item["quantity"]))
        unit_price = Decimal(str(item["unit_price"]))
        line_total = (quantity * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += line_total
        rows.append(
            ExpenseItem(
                organization=organization,
                branch=branch,
                name=str(item["name"]).strip()[:120],
                quantity=quantity,
                unit=str(item.get("unit") or "dona")[:10],
                unit_price=unit_price,
                line_total=line_total,
                note=str(item.get("note") or "").strip()[:255],
            )
        )

    if total <= 0:
        raise BusinessRuleViolation(gettext("Chiqim summasi noldan katta boʻlishi kerak."))
    return rows, total


@transaction.atomic
def update_expense(
    *,
    expense: Expense,
    category: Any = None,
    expense_date: Any = None,
    description: str | None = None,
    items: list[dict[str, Any]] | None = None,
    amount: Decimal | None = None,
    cash_account: Any = None,
    allow_negative: bool = False,
    updated_by: Any = None,
) -> Expense:
    """
    Chiqimni tahrirlaydi (mijoz so'rovi, 2026-10-14).

    Chiqim yaratilishi bilan tasdiqlanadi va pul qopdan chiqadi, ya'ni
    tahrirlash ikki narsa: hujjatni o'zgartirish VA pul izini to'g'rilash.
    Summa, sana yoki qop o'zgarsa, eski chiqimga QARSHI yozuv va yangisiga
    chiqim yoziladi — eski harakat hech qachon tahrirlanmaydi (12-invariant).
    Qarshi yozuv avval yoziladi, shuning uchun o'sha qopdagi tahrir eski
    summa qaytgan qoldiq bilan tekshiriladi (ADR-29).

    Tavsif yoki kategoriya o'zgarsa — pulga tegilmaydi.

    Rad etilgan chiqim tahrirlanmaydi: u "nima so'ralgan va nega rad
    etilgan" degan yozuv. Ombor xaridiga bog'langan chiqimning qatorlari
    va summasi ham bu yerdan o'zgarmaydi — ular omborda, va bu yerdagi
    o'zgarish ombordagi miqdor bilan pulni ajratib qo'yardi.
    """
    expense = Expense.objects.select_for_update().get(pk=expense.pk)
    if expense.status == ExpenseStatus.REJECTED:
        raise BusinessRuleViolation(gettext("Rad etilgan chiqimni tahrirlab boʻlmaydi."))

    touches_lines = items is not None or amount is not None
    if touches_lines and expense.stock_movements.exists():
        raise BusinessRuleViolation(
            gettext(
                "Bu chiqim ombor xarididan tugʻilgan — miqdor va narxni ombordagi "
                "xarid yozuvida tuzating."
            )
        )
    if amount is not None and items is None and expense.items.exists():
        raise BusinessRuleViolation(
            gettext("Chiqim qatorlardan iborat — summani qatorlar orqali oʻzgartiring.")
        )

    fields = ["updated_at"]
    money_changed = False

    if category is not None and category.id != expense.category_id:
        expense.category = category
        fields.append("category")
    if description is not None:
        expense.description = description[:255]
        fields.append("description")
    if expense_date is not None and expense_date != expense.expense_date:
        expense.expense_date = expense_date
        fields.append("expense_date")
        money_changed = True
    if cash_account is not None and cash_account.id != expense.cash_account_id:
        if cash_account.organization_id != expense.organization_id:
            raise BusinessRuleViolation(gettext("Kassa hisobi boshqa tashkilotga tegishli."))
        expense.cash_account = cash_account
        fields.append("cash_account")
        money_changed = True

    new_rows: list[ExpenseItem] | None = None
    if items is not None:
        new_rows, total = _build_items(
            organization=expense.organization, branch=expense.branch, items=items
        )
    elif amount is not None:
        total = Decimal(amount).quantize(Decimal("0.01"))
        if total <= 0:
            raise BusinessRuleViolation(gettext("Chiqim summasi noldan katta boʻlishi kerak."))
    if touches_lines and total != expense.amount:
        expense.amount = total
        fields.append("amount")
        money_changed = True

    expense.save(update_fields=fields)
    if new_rows is not None:
        expense.items.all().delete()
        for row in new_rows:
            row.expense = expense
        ExpenseItem.objects.bulk_create(new_rows)

    unpaid_credit = expense.on_credit and expense.paid_on is None
    if (
        money_changed
        and not unpaid_credit
        and expense.status in (ExpenseStatus.APPROVED, ExpenseStatus.PAID)
    ):
        account = expense.cash_account or cash.account_for_method(
            branch=expense.branch, method="cash"
        )
        cash.reverse_movements_for(
            source_type=MovementSource.EXPENSE,
            source_id=expense.id,
            description=gettext("chiqim tahrirlandi"),
            created_by=updated_by,
        )
        cash.post_movement(
            account=account,
            direction=MovementDirection.OUT,
            amount=expense.amount,
            source_type=MovementSource.EXPENSE,
            source_id=expense.id,
            description=f"{expense.category.name}: {expense.description}"[:255],
            occurred_at=timezone.make_aware(datetime.combine(expense.expense_date, time.min)),
            created_by=updated_by,
            allow_negative=allow_negative,
        )
    return expense


@transaction.atomic
def approve_expense(
    *,
    expense: Expense,
    approved_by: Any,
    note: str = "",
    cash_account: Any = None,
    allow_negative: bool = False,
) -> Expense:
    """
    Chiqimni tasdiqlaydi va pulni kassadan CHIQARADI (ADR-17).

    **Bitta tranzaksiya** (invariant 12). Hujjat holati va pul harakati
    ikki yozuv, lekin bitta hodisa: ikkinchisi yiqilsa birinchisi ham
    qolmasligi kerak. Ilgari dekorator yoʻq edi va bu deyarli zararsiz
    koʻrinardi, chunki `post_movement()` amalda hech qachon xato
    koʻtarmasdi. ADR-29 dan keyin u MUNTAZAM koʻtaradi — qopda pul
    yetmasa — va oʻshanda chiqim "tasdiqlangan" boʻlib hisobotga
    kirib, kassadan esa chiqmay qolardi.

    Nega pul aynan shu yerda chiqadi, `mark-paid` da emas: hisobotlar
    (`expense_summary`, foyda-zarar) boshidan beri `approved` ni ham
    xarajat deb sanaydi. Kassa esa faqat `paid` da kamaysa, ikkita
    ekran bir xil savolga ikki xil javob berardi — va ko'p bog'cha
    "to'landi" tugmasini umuman bosmaydi. Mijozning o'z so'zi ham shu
    edi: "chiqim kiritayotgan paytda qaysi puldan ketayotgani hisobga
    olinishi kerak".

    `mark_expense_paid()` shundan keyin faqat bayroqni o'zgartiradi —
    pul ikkinchi marta chiqmaydi.
    """
    _assert_pending(expense, "tasdiqlash")

    if expense.on_credit:
        # Nasiya (Bosqich 13.2a): xarajat tan olinadi, pul hali chiqmaydi —
        # u `mark_expense_paid` da, to'langan kuni chiqadi.
        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = approved_by
        expense.decided_at = timezone.now()
        expense.decision_note = note[:255]
        expense.save(
            update_fields=["status", "approved_by", "decided_at", "decision_note", "updated_at"]
        )
        return expense

    account = cash_account or expense.cash_account
    if account is None:
        # Qop ko'rsatilmasa naqd kassa: bog'chada odatiy hol, va
        # tasdiqlashni "sozlama to'liq emas" deb to'xtatish noto'g'ri
        # nosozlik bo'lardi.
        account = cash.account_for_method(branch=expense.branch, method="cash")
    if account.organization_id != expense.organization_id:
        raise BusinessRuleViolation(gettext("Kassa hisobi boshqa tashkilotga tegishli."))

    expense.status = ExpenseStatus.APPROVED
    expense.approved_by = approved_by
    expense.decided_at = timezone.now()
    expense.decision_note = note[:255]
    expense.cash_account = account
    expense.paid_on = expense.expense_date
    expense.save(
        update_fields=[
            "status",
            "approved_by",
            "decided_at",
            "decision_note",
            "cash_account",
            "paid_on",
            "updated_at",
        ]
    )

    cash.post_movement(
        account=account,
        direction=MovementDirection.OUT,
        amount=expense.amount,
        source_type=MovementSource.EXPENSE,
        source_id=expense.id,
        description=f"{expense.category.name}: {expense.description}"[:255],
        occurred_at=timezone.make_aware(datetime.combine(expense.expense_date, time.min)),
        created_by=approved_by,
        allow_negative=allow_negative,
    )
    return expense


@transaction.atomic
def reject_expense(*, expense: Expense, approved_by: Any, note: str = "") -> Expense:
    """
    Rad etilgan chiqim O'CHIRILMAYDI.

    U nima so'ralgani va nega rad etilgani haqidagi yozuv bo'lib qoladi —
    aks holda "men buni so'ragan edim" degan bahsga javob bo'lmasdi.
    """
    _assert_pending(expense, "rad etish")
    expense.status = ExpenseStatus.REJECTED
    expense.approved_by = approved_by
    expense.decided_at = timezone.now()
    expense.decision_note = note[:255]
    expense.save(
        update_fields=["status", "approved_by", "decided_at", "decision_note", "updated_at"]
    )
    return expense


@transaction.atomic
def mark_expense_paid(
    *,
    expense: Expense,
    cash_account: Any = None,
    allow_negative: bool = False,
    created_by: Any = None,
    paid_on: Any = None,
) -> Expense:
    """
    Chiqimni "to'langan" deb belgilaydi — BAYROQ, pul harakati emas.

    Nasiya xarid bundan mustasno (Bosqich 13.2a): uning puli aynan shu
    yerda, `paid_on` kuni (sukut — bugun) tanlangan qopdan chiqadi.

    Pul tasdiqlash paytida allaqachon kassadan chiqqan
    (`approve_expense`). Bu yerda uni ikkinchi marta chiqarish qoldiqni
    ikki barobar kamaytirardi. Qop ko'rsatilsa — faqat to'g'rilanadi.
    """
    if expense.status != ExpenseStatus.APPROVED:
        raise BusinessRuleViolation(
            gettext("Faqat tasdiqlangan chiqimni toʻlangan deb belgilash mumkin.")
        )

    if expense.on_credit:
        if expense.paid_on is not None:
            raise BusinessRuleViolation(gettext("Bu nasiya allaqachon toʻlangan."))
        account = cash_account or cash.account_for_method(branch=expense.branch, method="cash")
        if account.organization_id != expense.organization_id:
            raise BusinessRuleViolation(gettext("Kassa hisobi boshqa tashkilotga tegishli."))
        day = paid_on or timezone.localdate()
        cash.post_movement(
            account=account,
            direction=MovementDirection.OUT,
            amount=expense.amount,
            source_type=MovementSource.EXPENSE,
            source_id=expense.id,
            description=f"{expense.category.name}: {expense.description}"[:255],
            occurred_at=timezone.make_aware(datetime.combine(day, time(12))),
            created_by=created_by,
            allow_negative=allow_negative,
        )
        expense.status = ExpenseStatus.PAID
        expense.cash_account = account
        expense.paid_on = day
        expense.save(update_fields=["status", "cash_account", "paid_on", "updated_at"])
        return expense

    fields = ["status", "updated_at"]
    expense.status = ExpenseStatus.PAID
    if cash_account is not None:
        if cash_account.organization_id != expense.organization_id:
            raise BusinessRuleViolation(gettext("Kassa hisobi boshqa tashkilotga tegishli."))
        # Qop o'zgarsa, pul harakati ham o'sha qopga ko'chiriladi:
        # eskisiga qarshi yozuv, yangisiga chiqim.
        if expense.cash_account_id != cash_account.id:
            cash.reverse_movements_for(
                source_type=MovementSource.EXPENSE,
                source_id=expense.id,
                description=gettext("qop oʻzgartirildi"),
                created_by=created_by,
            )
            cash.post_movement(
                account=cash_account,
                direction=MovementDirection.OUT,
                amount=expense.amount,
                source_type=MovementSource.EXPENSE,
                source_id=expense.id,
                description=f"{expense.category.name}: {expense.description}"[:255],
                occurred_at=timezone.make_aware(datetime.combine(expense.expense_date, time.min)),
                created_by=created_by,
                allow_negative=allow_negative,
            )
        expense.cash_account = cash_account
        fields.insert(1, "cash_account")

    expense.save(update_fields=fields)
    return expense


def expense_summary(
    *, organization_id: Any, date_from: date, date_to: date, branch_id: Any = None
) -> dict[str, Any]:
    """
    Davr bo'yicha kategoriya kesimida yig'ma.

    Faqat `approved`/`paid` hisobga olinadi — kutilayotgan so'rov hali
    xarajat emas, va uni P&L ga qo'shish sarfni oshirib ko'rsatardi.
    """
    queryset = Expense.objects.filter(
        expense_date__gte=date_from,
        expense_date__lte=date_to,
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
    )
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)

    rows = queryset.values("category__name").annotate(total=Sum("amount")).order_by("-total")
    total = queryset.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    return {
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "total": str(total),
        "by_category": [
            {"category": row["category__name"], "total": str(row["total"])} for row in rows
        ],
    }


# --- Bank komissiyasi (Bosqich 12.5, brif §5) ---

#: Komissiya chiqimlari shu toifaga tushadi — har filialda bittadan.
COMMISSION_CATEGORY = "Bank komissiyasi"


def commission_percent(*, branch: Any, method: str) -> Decimal:
    """Usul komissiyasi foizi — filial sozlamasi (`commission.<usul>_percent`)."""
    from apps.settings_app.services import DEFAULTS, get_setting

    key = f"commission.{method}_percent"
    if key not in DEFAULTS:
        return Decimal("0")
    # Buzuq sozlama (masalan "0,2") to'lov qabulini YIQITMASLIGI kerak:
    # pul kassirning qo'lida, komissiya esa keyin tuzatiladigan narsa.
    try:
        percent = Decimal(str(get_setting(key=key, branch=branch) or "0").replace(",", "."))
    except InvalidOperation:
        return Decimal("0")
    return percent if percent > 0 else Decimal("0")


@transaction.atomic
def record_bank_commission(*, payment: Any, account: Any, created_by: Any = None) -> Any:
    """
    To'lov usulining komissiyasini bank xarajati qilib yozadi.

    To'lov bankka YALPI tushadi (10 000 000), komissiya esa alohida
    chiqim (20 000) — shunda "terminal orqali qancha keldi?" va "bank
    qancha oldi?" ikki alohida savolga ikki to'g'ri javob bor. Chiqim
    darhol `paid`: bank uni so'ramaydi, o'zi ushlab qoladi.

    To'lov qaytarilsa komissiya QOLADI — bank uni qaytarmaydi.
    """
    percent = commission_percent(branch=payment.branch, method=payment.method)
    amount = (payment.amount * percent / Decimal("100")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    if amount <= 0:
        return None

    # Sukut ro'yxatdagi "Bank xarajatlari va komissiyalar" bo'lsa — o'sha
    # (Bosqich 13.2a); bo'lmasa o'zimizning "Bank komissiyasi".
    category = (
        ExpenseCategory.objects.filter(
            branch=payment.branch,
            name__in=(COMMISSION_CATEGORY, "Bank xarajatlari va komissiyalar"),
            is_active=True,
        )
        .order_by("name")
        .first()
    )
    if category is None:
        category = ExpenseCategory.objects.create(
            organization=payment.organization, branch=payment.branch, name=COMMISSION_CATEGORY
        )

    paid_on = timezone.localtime(payment.paid_at).date()
    label = payment.get_method_display()
    expense = Expense.objects.create(
        organization=payment.organization,
        branch=payment.branch,
        category=category,
        amount=amount,
        expense_date=paid_on,
        description=f"{label} {percent.normalize()}% — {payment.child.full_name}"[:255],
        status=ExpenseStatus.PAID,
        approved_by=created_by,
        decided_at=timezone.now(),
        cash_account=account,
        payment=payment,
    )
    cash.post_movement(
        account=account,
        direction=MovementDirection.OUT,
        amount=amount,
        source_type=MovementSource.EXPENSE,
        source_id=expense.id,
        description=f"{COMMISSION_CATEGORY}: {expense.description}"[:255],
        occurred_at=payment.paid_at,
        created_by=created_by,
        # Pul shu qopga hozirgina tushdi — komissiya undan kichik.
        allow_negative=True,
    )
    return expense


# --- Sukut toifalar (Bosqich 13.2a, brif §3.6) ---

#: Ikki darajali boshlang'ich ro'yxat. Hammasi tahrirlanadi; hisob kodlari
#: buxgalter eksporti bosqichida (13.8) to'ldiriladi.
DEFAULT_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Ish haqi", ("Naqd qism", "Karta qism", "Ijtimoiy soliq")),
    (
        "Oziq-ovqat",
        ("Goʻsht", "Sut mahsulotlari", "Non", "Sabzavot-meva", "Quruq mahsulotlar", "Bozor"),
    ),
    ("Kommunal", ("Elektr", "Gaz", "Suv", "Chiqindi", "Internet")),
    ("Ijara", ()),
    ("Taʼmir va xoʻjalik", ()),
    ("Oʻquv materiallari va oʻyinchoqlar", ()),
    ("Tadbirlar va sovgʻalar", ()),
    ("Tibbiyot va SES", ()),
    ("Marketing", ("SMM", "Target", "Reklama")),
    ("IT va dasturlar", ()),
    ("Bank xarajatlari va komissiyalar", ()),
    ("Soliqlar va yigʻimlar", ()),
    ("Transport", ()),
    ("Kiyim va forma", ()),
    ("Boshqa", ()),
)


@transaction.atomic
def ensure_default_categories(*, branch: Any) -> int:
    """
    Filialda toifa YO'Q bo'lsa — sukut ro'yxatini ochadi. Qaytaradi: nechta.

    Toifasi bor filialga tegmaydi: mavjud bog'chaning o'z ro'yxati uning
    qarori (va hisobotlari unga bog'langan). Idempotent.
    """
    if ExpenseCategory.objects.filter(branch=branch).exists():
        return 0
    created = 0
    for name, children in DEFAULT_CATEGORIES:
        parent = ExpenseCategory.objects.create(
            organization=branch.organization, branch=branch, name=name
        )
        created += 1
        for child in children:
            ExpenseCategory.objects.create(
                organization=branch.organization, branch=branch, name=child, parent=parent
            )
            created += 1
    return created
