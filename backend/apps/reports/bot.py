"""
Rahbar uchun buyruqli bot (mijoz so'rovi, 2026-10-20).

Botga ulangan xodim (13.3) oddiy so'z bilan so'raydi — "bugungi tushum",
"bu oy foyda", "shu oydagi chiqim", "faol bolalar" — va raqam oladi.

**Sun'iy intellekt yo'q** (egasining qarori, ADR-14 kuchda): savol
`search_key` skeletiga aylantiriladi (o'zbek lotin/kirill, rus, ingliz,
apostroflarsiz) va so'z ro'yxatlari bilan solishtiriladi. Tushunilmagan
matn `None` qaytaradi — u chiqim kiritish yoki ota-ona botiga o'tadi.

Raqamlar shu yerda hisoblanmaydi: tushum — to'lov hujjatlari, foyda —
`money.profit_and_loss`, qarz — `finance.selectors.debtor_queryset`
(balans formulasi bitta joyda, invariant 13), qoplar —
`cash.selectors.account_balances`. Har savol web'dagi ruxsat bilan
tekshiriladi: kassir foydani so'rasa — "ruxsat yo'q"; "faqat o'ziniki"
kassir faqat o'zi qabul qilgan pulni eshitadi (ADR-30).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.utils import timezone, translation
from django.utils.translation import gettext

from apps.core.translit import search_key

__all__ = ["answer", "classify", "help_text"]

ZERO = Decimal("0")

#: Savol turi → skeletdagi so'z bo'laklari. Tartib muhim: "qarzdor bolalar"
#: — qarz, "sof foyda" — foyda.
INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("profit", ("foyda", "pribil", "profit")),
    ("expenses", ("chiqim", "harajat", "rashod", "ehpens", "spent")),  # x → h (search_key)
    ("revenue", ("tushum", "tushgan", "kirim", "viruchk", "vyruchk", "postuplen", "revenue")),
    ("debts", ("qarz", "dolg", "debt")),
    ("cash", ("kass", "balans", "cash")),
    ("children", ("bola", "deti", "detey", "child", "kids")),
)

#: Davr → so'z bo'laklari. Tartib muhim: "segodnya" ichida "god" bor.
PERIODS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("today", ("bugun", "segodn", "today")),
    ("yesterday", ("kecha", "vcher", "yesterday")),
    ("last_month", ("otganoy", "utganoy", "otkanoy", "proshl", "lastmonth")),
    ("week", ("hafta", "nedel", "week")),
    ("year", ("yil", "god", "year")),
    ("month", ("oy", "mesya", "month")),
)

DEFAULT_PERIOD = {
    "revenue": "today",
    "expenses": "month",
    "profit": "month",
    "children": "today",
    "debts": "today",
    "cash": "today",
}

HELP_WORDS = ("help", "menu", "yordam", "menyu", "pomosh", "spravk")


def classify(text: str) -> tuple[str, str] | None:
    """Savol turi va davri; savol bo'lmasa — `None`."""
    key = search_key(text or "")
    if not key or key[0].isdigit():
        return None  # "150 000 kartoshka" — chiqim kiritish
    intent = next((name for name, words in INTENTS if any(w in key for w in words)), None)
    if intent is None:
        return None
    period = next(
        (name for name, words in PERIODS if any(w in key for w in words)),
        DEFAULT_PERIOD[intent],
    )
    return intent, period


def _som(value: Any) -> str:
    amount = int(Decimal(str(value or 0)))
    text = f"{abs(amount):,}".replace(",", " ")
    return f"−{text}" if amount < 0 else text


def _range(period: str) -> tuple[date, date, str]:
    today = timezone.localdate()
    if period == "yesterday":
        day = today - timedelta(days=1)
        return day, day, gettext("kecha ({date})").format(date=day.strftime("%d.%m"))
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, today, gettext("shu hafta")
    if period == "month":
        return today.replace(day=1), today, gettext("shu oy")
    if period == "last_month":
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end, gettext("oʻtgan oy")
    if period == "year":
        return today.replace(month=1, day=1), today, gettext("shu yil")
    return today, today, gettext("bugun ({date})").format(date=today.strftime("%d.%m"))


def _allowed(user: Any, *codes: str) -> bool:
    from apps.core.permissions import has_permission_code

    return all(has_permission_code(user, code) for code in codes)


def _denied() -> str:
    return gettext("Bu maʼlumotni koʻrishga rolingizda ruxsat yoʻq.")


def _where(user: Any) -> str:
    return f" · {user.branch.name}" if user.branch_id else ""


def _revenue(user: Any, period: str) -> str:
    from datetime import datetime, time

    from apps.finance.models import Payment, PaymentMethod
    from apps.finance.scope import payments_own_only

    if not _allowed(user, "payments.read"):
        return _denied()
    start, end, label = _range(period)
    payments = Payment.objects.filter(
        organization_id=user.organization_id,
        reversed_at__isnull=True,
        paid_at__gte=timezone.make_aware(datetime.combine(start, time.min)),
        paid_at__lte=timezone.make_aware(datetime.combine(end, time.max)),
    )
    if user.branch_id:
        payments = payments.filter(branch_id=user.branch_id)
    own = payments_own_only(user)
    if own:
        payments = payments.filter(received_by=user)
    rows = list(payments.values("method").annotate(total=Sum("amount")).order_by("-total"))
    total = sum((row["total"] for row in rows), ZERO)
    title = gettext("Siz qabul qilgan pul") if own else gettext("Tushum")
    lines = [f"💰 {title} — {label}{_where(user)}: {_som(total)} {gettext('soʻm')}"]
    labels = dict(PaymentMethod.choices)
    lines += [f"• {labels.get(row['method'], row['method'])}: {_som(row['total'])}" for row in rows]
    return "\n".join(lines)


def _expenses(user: Any, period: str) -> str:
    from django.db.models.functions import Coalesce

    from apps.expenses.models import Expense, ExpenseStatus

    if not _allowed(user, "expenses.read"):
        return _denied()
    start, end, label = _range(period)
    expenses = Expense.objects.filter(
        organization_id=user.organization_id,
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
        expense_date__gte=start,
        expense_date__lte=end,
    )
    if user.branch_id:
        expenses = expenses.filter(branch_id=user.branch_id)
    rows = list(
        expenses.annotate(group=Coalesce("category__parent__name", "category__name"))
        .values("group")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    total = sum((row["total"] for row in rows), ZERO)
    lines = [f"📉 {gettext('Chiqim')} — {label}{_where(user)}: {_som(total)} {gettext('soʻm')}"]
    lines += [f"• {row['group'] or '—'}: {_som(row['total'])}" for row in rows[:5]]
    return "\n".join(lines)


def _profit(user: Any, period: str) -> str:
    from apps.reports import money
    from apps.reports.views import report_allowed

    if not _allowed(user, "reports.read") or not report_allowed(user, "finance"):
        return _denied()
    today = timezone.localdate()
    if period == "last_month":
        end = today.replace(day=1) - timedelta(days=1)
        months, label = [(end.year, end.month)], gettext("oʻtgan oy")
    elif period == "year":
        months, label = [(today.year, m) for m in range(1, today.month + 1)], gettext("shu yil")
    else:
        # Foyda oy bo'yicha hisoblanadi (oylik, amortizatsiya oyga tegishli).
        months, label = [(today.year, today.month)], gettext("shu oy")
    totals = {"revenue": ZERO, "expenses": ZERO, "payroll": ZERO, "profit": ZERO}
    for year, month in months:
        pnl = money.profit_and_loss(
            organization_id=user.organization_id, year=year, month=month, branch_id=user.branch_id
        )
        totals["revenue"] += Decimal(pnl["revenue"]["total"])
        totals["expenses"] += Decimal(pnl["operating_expenses"]) + Decimal(pnl["amortization"])
        totals["payroll"] += Decimal(pnl["payroll"])
        totals["profit"] += Decimal(pnl["operating_profit"])
    sign = "📈" if totals["profit"] >= 0 else "🔻"
    return "\n".join(
        [
            f"{sign} {gettext('Foyda')} — {label}{_where(user)}: "
            f"{_som(totals['profit'])} {gettext('soʻm')}",
            f"• {gettext('Daromad')}: {_som(totals['revenue'])}",
            f"• {gettext('Xarajatlar')}: {_som(totals['expenses'])}",
            f"• {gettext('Ish haqi')}: {_som(totals['payroll'])}",
        ]
    )


def _children(user: Any, period: str) -> str:
    from apps.children.models import Child
    from apps.reports.selectors import active_children_count

    if not _allowed(user, "children.read"):
        return _denied()
    count = active_children_count(organization_id=user.organization_id, branch_id=user.branch_id)
    month_start = timezone.localdate().replace(day=1)
    new = Child.objects.filter(
        organization_id=user.organization_id, enrolled_on__gte=month_start, is_active=True
    )
    if user.branch_id:
        new = new.filter(branch_id=user.branch_id)
    return "\n".join(
        [
            f"👶 {gettext('Faol bolalar')}{_where(user)}: {count}",
            f"• {gettext('Shu oy kelganlar')}: {new.count()}",
        ]
    )


def _debts(user: Any, period: str) -> str:
    from apps.finance.selectors import debtor_queryset

    if not _allowed(user, "debtors.read"):
        return _denied()
    debtors = debtor_queryset()
    if user.branch_id:
        debtors = debtors.filter(branch_id=user.branch_id)
    total = sum((row.ledger_balance for row in debtors.only("id")), ZERO)
    return "\n".join(
        [
            f"⚠️ {gettext('Qarzdorlik')}{_where(user)}: {_som(total)} {gettext('soʻm')}",
            f"• {gettext('Qarzdor bolalar')}: {debtors.count()}",
        ]
    )


def _cash(user: Any, period: str) -> str:
    from apps.cash.selectors import account_balances
    from apps.finance.scope import payments_own_only

    if not _allowed(user, "payments.read") or payments_own_only(user):
        return _denied()
    rows = account_balances(organization_id=user.organization_id, branch_id=user.branch_id)
    total = sum((Decimal(row["balance"]) for row in rows), ZERO)
    lines = [f"🏦 {gettext('Pul qoplarda')}{_where(user)}: {_som(total)} {gettext('soʻm')}"]
    lines += [f"• {row['name']}: {_som(row['balance'])}" for row in rows]
    return "\n".join(lines)


_HANDLERS = {
    "revenue": _revenue,
    "expenses": _expenses,
    "profit": _profit,
    "children": _children,
    "debts": _debts,
    "cash": _cash,
}


def help_text() -> str:
    return "\n".join(
        [
            gettext("Savol yozing, masalan:"),
            "• " + gettext("bugungi tushum"),
            "• " + gettext("kechagi tushum"),
            "• " + gettext("bu oy foyda"),
            "• " + gettext("oʻtgan oy foyda"),
            "• " + gettext("shu oydagi chiqim"),
            "• " + gettext("faol bolalar"),
            "• " + gettext("qarzdorlik"),
            "• " + gettext("kassada qancha pul bor"),
            gettext("Chiqim kiritish uchun summadan boshlang: 150 000 kartoshka."),
        ]
    )


def _language(user: Any) -> str:
    from apps.settings_app.services import get_setting

    language = str(get_setting(key="general.default_language", branch=user.branch_id) or "uz")
    return language if language in ("uz", "ru", "en") else "uz"


def answer(*, user: Any, text: str) -> str | None:
    """Tashkilot kontekstida chaqiriladi. Savol bo'lmasa — `None`."""
    key = search_key(text or "")
    with translation.override(_language(user)):
        if key and any(word in key for word in HELP_WORDS):
            return help_text()
        found = classify(text)
        if found is None:
            return None
        intent, period = found
        return _HANDLERS[intent](user, period)
