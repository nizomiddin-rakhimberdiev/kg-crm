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

from django.db.models import Count, Sum
from django.utils import timezone, translation
from django.utils.translation import gettext

from apps.core.translit import search_key

__all__ = ["answer", "classify", "help_text", "not_understood"]

ZERO = Decimal("0")

#: Savol turi → so'z bo'laklari (`search_key` skeletida: apostrofsiz, kirill
#: lotinga, x → h). Bo'lak matnning istalgan joyida bo'lsa yetadi; 4 harfdan
#: uzun so'zlarda bitta harf xatosi ham kechiriladi ("tushm" → tushum).
#: Tartib muhim: aniq mavzular avval, "hisobot/holat" (umumiy xulosa) — oxirida.
INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("subscription", ("obuna", "podpisk", "subscription")),
    ("payroll", ("maosh", "ishhaqi", "zarplat", "salary")),
    ("profit", ("foyda", "pribil", "profit")),
    ("expenses", ("chiqim", "harajat", "rashod", "ehpens", "sarf", "spent")),  # x → h
    (
        "revenue",
        (
            "tushum",
            "tushgan",
            "kirim",
            "daromad",
            "viruchk",
            "vyruchk",
            "postuplen",
            "dohod",
            "revenue",
            "income",
        ),
    ),
    ("debts", ("qarz", "dolg", "debt")),
    ("attendance", ("davomat", "keldi", "kelmadi", "kelgan", "poseshch", "prishl", "attendance")),
    ("staff", ("hodim", "sotrudnik", "tarbiyachi", "employee", "staff")),
    ("cash", ("kass", "balans", "qoldiq", "cash")),
    ("children", ("bola", "deti", "detey", "rebenok", "rebyonok", "child", "kids")),
    (
        "summary",
        (
            "hisobot",
            "hulosa",
            "otchet",
            "otchot",
            "svodk",
            "itog",
            "umumiy",
            "holat",
            "ahvol",
            "vaziyat",
            "report",
            "summary",
        ),
    ),
)

#: Davr → so'z bo'laklari. Tartib muhim: "segodnya" ichida "god" bor, shuning
#: uchun "bugun" yildan oldin. "Oy" — faqat so'z boshida ("bu oy", "oydagi").
PERIODS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("today", ("bugun", "kunlik", "segodn", "today", "daily")),
    ("yesterday", ("kecha", "vcher", "yesterday")),
    ("last_month", ("otganoy", "utganoy", "otkanoy", "proshl", "lastmonth")),
    ("week", ("hafta", "nedel", "week")),
    ("year", ("yil", "god", "year")),
    ("month", ("mesya", "month")),
)

DEFAULT_PERIOD = {
    "revenue": "today",
    "expenses": "month",
    "profit": "month",
    "children": "today",
    "debts": "today",
    "cash": "today",
    "subscription": "month",
    "payroll": "month",
    "attendance": "today",
    "staff": "today",
    "summary": "today",
}

#: Umumiy so'z yoki salom — yordam ro'yxati bilan javob.
HELP_WORDS = (
    "help",
    "menu",
    "yordam",
    "menyu",
    "pomosh",
    "spravk",
    "nima",
    "salom",
    "assalom",
    "privet",
    "zdravst",
    "hello",
    "qanday",
    "qanaqa",
)


def _tokens(text: str) -> list[str]:
    import re

    return [key for key in (search_key(part) for part in re.split(r"[\s,.!?;:]+", text)) if key]


def _close(token: str, word: str) -> bool:
    """Bitta harf xatosi: "tushm" ~ "tushum", "chiqm" ~ "chiqim"."""
    from difflib import SequenceMatcher

    if len(token) < 4 or len(word) < 4:
        return False
    return SequenceMatcher(None, token[: len(word) + 1], word).ratio() >= 0.83


def _mentions(key: str, tokens: list[str], words: tuple[str, ...]) -> bool:
    return any(word in key for word in words) or any(
        _close(token, word) for token in tokens for word in words
    )


def classify(text: str) -> tuple[str, str] | None:
    """Savol turi va davri; savol bo'lmasa — `None`."""
    key = search_key(text or "")
    if not key or key[0].isdigit():
        return None  # "150 000 kartoshka" — chiqim kiritish
    tokens = _tokens(text)
    intent = next((name for name, words in INTENTS if _mentions(key, tokens, words)), None)
    if intent is None:
        return None
    period = next((name for name, words in PERIODS if any(word in key for word in words)), None)
    if period is None and any(token.startswith("oy") for token in tokens):
        period = "month"
    return intent, period or DEFAULT_PERIOD[intent]


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
    if period in ("month", "last_month") and not own:
        # "Qancha daromad qildik?" — oy uchun hisoblangan summa ham (fakturalar).
        from apps.finance.models import Invoice, InvoiceStatus

        invoices = Invoice.objects.filter(
            organization_id=user.organization_id,
            period_year=start.year,
            period_month=start.month,
        ).exclude(status=InvoiceStatus.CANCELLED)
        if user.branch_id:
            invoices = invoices.filter(branch_id=user.branch_id)
        charged = invoices.aggregate(total=Sum("amount_due"))["total"] or ZERO
        lines.append(f"• {gettext('Oy uchun hisoblangan (fakturalar)')}: {_som(charged)}")
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


def _attendance(user: Any, period: str) -> str:
    from apps.attendance.models import AttendanceRecord, AttendanceStatus
    from apps.reports.selectors import active_children_count

    if not _allowed(user, "attendance.read"):
        return _denied()
    day, _end, label = _range("yesterday" if period == "yesterday" else "today")
    records = AttendanceRecord.objects.filter(
        organization_id=user.organization_id, attendance_date=day
    )
    if user.branch_id:
        records = records.filter(branch_id=user.branch_id)
    counts = dict(records.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    active = active_children_count(organization_id=user.organization_id, branch_id=user.branch_id)
    marked = sum(counts.values())
    labels = dict(AttendanceStatus.choices)
    lines = [f"🗓 {gettext('Davomat')} — {label}{_where(user)}"]
    lines += [
        f"• {labels[status]}: {counts.get(status, 0)}"
        for status in (AttendanceStatus.PRESENT, AttendanceStatus.ABSENT, AttendanceStatus.EXCUSED)
    ]
    lines.append(f"• {gettext('Belgilanmagan')}: {max(active - marked, 0)}")
    return "\n".join(lines)


def _staff(user: Any, period: str) -> str:
    from apps.hr.models import Employee, EmploymentStatus

    if not _allowed(user, "payroll.read"):
        return _denied()
    employees = Employee.objects.filter(organization_id=user.organization_id)
    if user.branch_id:
        employees = employees.filter(branch_id=user.branch_id)
    counts = dict(
        employees.values_list("employment_status")
        .annotate(n=Count("id"))
        .values_list("employment_status", "n")
    )
    return "\n".join(
        [
            f"👥 {gettext('Xodimlar')}{_where(user)}: "
            f"{counts.get(EmploymentStatus.ACTIVE, 0) + counts.get(EmploymentStatus.ON_LEAVE, 0)}",
            f"• {gettext('Ishlayapti')}: {counts.get(EmploymentStatus.ACTIVE, 0)}",
            f"• {gettext('Taʼtilda')}: {counts.get(EmploymentStatus.ON_LEAVE, 0)}",
        ]
    )


def _payroll(user: Any, period: str) -> str:
    from apps.payroll.models import PayrollItem, PayrollPayout, PayrollStatus

    if not _allowed(user, "payroll.read"):
        return _denied()
    today = timezone.localdate()
    if period == "last_month":
        end = today.replace(day=1) - timedelta(days=1)
        year, month, label = end.year, end.month, gettext("oʻtgan oy")
    else:
        year, month, label = today.year, today.month, gettext("shu oy")
    items = PayrollItem.objects.filter(
        organization_id=user.organization_id,
        payroll_run__period_year=year,
        payroll_run__period_month=month,
        payroll_run__status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
    )
    payouts = PayrollPayout.objects.filter(
        organization_id=user.organization_id,
        payroll_run__period_year=year,
        payroll_run__period_month=month,
    )
    if user.branch_id:
        items = items.filter(branch_id=user.branch_id)
        payouts = payouts.filter(branch_id=user.branch_id)
    totals = items.aggregate(gross=Sum("gross"), net=Sum("net"))
    if totals["gross"] is None:
        return f"💼 {gettext('Ish haqi')} — {label}: " + gettext("oylik hisobi hali yakunlanmagan.")
    paid = payouts.aggregate(total=Sum("amount"))["total"] or ZERO
    net = totals["net"] or ZERO
    return "\n".join(
        [
            f"💼 {gettext('Ish haqi')} — {label}{_where(user)}: "
            f"{_som(totals['gross'])} {gettext('soʻm')}",
            f"• {gettext('Qoʻlga beriladi')}: {_som(net)}",
            f"• {gettext('Toʻlangan')}: {_som(paid)}",
            f"• {gettext('Qoldi')}: {_som(max(net - paid, ZERO))}",
        ]
    )


def _subscription(user: Any, period: str) -> str:
    from apps.subscriptions import services as billing
    from apps.subscriptions.models import Subscription, SubscriptionStatus

    if not _allowed(user, "billing.read"):
        return _denied()
    subscription = (
        Subscription.objects.filter(organization_id=user.organization_id)
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )
    if subscription is None:
        return gettext("Obuna maʼlumoti yoʻq.")
    usage = billing.projected_usage(subscription=subscription)
    status = dict(SubscriptionStatus.choices).get(subscription.status, subscription.status)
    lines = [
        f"🧾 {gettext('Obuna')}: {status}",
        f"• {gettext('Shu oy taxminiy summa')}: {_som(usage['projected']['total_amount'])} "
        f"{gettext('soʻm')}",
        f"• {gettext('Bolalar (hisobga)')}: {usage['peak_children']}",
    ]
    if subscription.status == SubscriptionStatus.TRIALING and subscription.trial_ends_at:
        lines.append(
            f"• {gettext('Sinov davri tugaydi')}: "
            f"{timezone.localtime(subscription.trial_ends_at).strftime('%d.%m.%Y')}"
        )
    else:
        lines.append(
            f"• {gettext('Joriy davr')}: {subscription.current_period_start.strftime('%d.%m.%Y')}"
            f" — {subscription.current_period_end.strftime('%d.%m.%Y')}"
        )
    return "\n".join(lines)


def _summary(user: Any, period: str) -> str:
    """Kunlik (yoki davr) xulosa — foydalanuvchi ko'ra oladigan bo'limlar."""
    blocks = []
    for name in ("revenue", "expenses", "cash", "debts", "attendance"):
        text = _HANDLERS[name](user, period if name in ("revenue", "expenses") else "today")
        if text != _denied():
            blocks.append(text)
    if not blocks:
        return _denied()
    _start, _end, label = _range(period)
    return f"📊 {gettext('Xulosa')} — {label}\n\n" + "\n\n".join(blocks)


_HANDLERS = {
    "revenue": _revenue,
    "expenses": _expenses,
    "profit": _profit,
    "children": _children,
    "debts": _debts,
    "cash": _cash,
    "attendance": _attendance,
    "staff": _staff,
    "payroll": _payroll,
    "subscription": _subscription,
    "summary": _summary,
}


def help_text() -> str:
    return "\n".join(
        [
            gettext("Savol yozing, masalan:"),
            "• " + gettext("kunlik hisobot"),
            "• " + gettext("bugungi tushum"),
            "• " + gettext("bu oy qancha daromad qildik"),
            "• " + gettext("bu oy foyda"),
            "• " + gettext("oʻtgan oy foyda"),
            "• " + gettext("shu oydagi chiqim"),
            "• " + gettext("faol bolalar"),
            "• " + gettext("bugun nechta bola keldi"),
            "• " + gettext("qarzdorlik"),
            "• " + gettext("kassada qancha pul bor"),
            "• " + gettext("bu oy oylik maosh"),
            "• " + gettext("xodimlar soni"),
            "• " + gettext("obuna summasi"),
            gettext("Chiqim kiritish uchun summadan boshlang: 150 000 kartoshka."),
        ]
    )


def _language(user: Any) -> str:
    from apps.settings_app.services import get_setting

    language = str(get_setting(key="general.default_language", branch=user.branch_id) or "uz")
    return language if language in ("uz", "ru", "en") else "uz"


def not_understood(*, user: Any) -> str:
    """Xodim chatida tushunilmagan matn — nima so'rash mumkinligi bilan."""
    with translation.override(_language(user)):
        return "🤔 " + gettext("Savolni tushunmadim.") + "\n\n" + help_text()


def answer(*, user: Any, text: str) -> str | None:
    """Tashkilot kontekstida chaqiriladi. Savol bo'lmasa — `None`."""
    key = search_key(text or "")
    with translation.override(_language(user)):
        found = classify(text)
        if found is not None:
            intent, period = found
            return _HANDLERS[intent](user, period)
        # Savol emas, lekin umumiy so'z yoki salom — nima so'rash mumkinligini aytamiz.
        if key and not key[0].isdigit() and any(word in key for word in HELP_WORDS):
            return help_text()
        return None
