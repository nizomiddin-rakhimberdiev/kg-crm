"""
Egaga darhol xabarlar va kunlik xulosa (Bosqich 13.4, brif §7).

Qabul qiluvchilar — botga ulangan (13.3c) egasi; `alerts.recipients`
sozlamasi bilan direktor ham qo'shiladi. Xabar tranzaksiya TASDIQLANGACH
ketadi (`on_commit`): rad etilgan amal haqida xabar bormasin.

Chegaralar sozlamada: `alerts.expense_threshold`, `alerts.benefit_percent`,
`alerts.digest_hour`. Tasdiqlash (maker-checker) o'chiq bo'lsa ham bu
xabarlar ishlaydi — egasi bilib turadi.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext

logger = logging.getLogger(__name__)

__all__ = [
    "notify",
    "notify_user",
    "expense_recorded",
    "benefit_given",
    "send_digest",
    "recipients",
]


def _som(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", " ")


def _setting(key: str, default: Any) -> Any:
    from apps.settings_app.services import get_setting

    value = get_setting(key=key)
    return default if value in (None, "") else value


def _send(chat_id: str, text: str) -> None:
    from apps.notifications.providers import TelegramProvider

    try:
        TelegramProvider().send(address=chat_id, body=text)
    except Exception:  # noqa: BLE001 — xabar ketmasa ham ish to'xtamaydi
        logger.exception("Egaga xabar yuborilmadi")


def recipients(organization_id: Any) -> list[str]:
    """Botga ulangan egasi (va sozlamada bo'lsa — direktor)."""
    from django.db.models import Q

    from apps.accounts.models import User

    roles = {part.strip() for part in str(_setting("alerts.recipients", "owner")).split(",")}
    codes = ["org_owner"] + (["director"] if "director" in roles else [])
    who = Q(role__code__in=codes)
    return list(
        User.objects.filter(organization_id=organization_id, is_active=True)
        .filter(who)
        .exclude(telegram_chat_id="")
        .values_list("telegram_chat_id", flat=True)
    )


def notify_user(*, user: Any, text: str) -> None:
    """Bitta xodimga (botga ulangan bo'lsa) — tranzaksiya tasdiqlangach."""
    chat = (getattr(user, "telegram_chat_id", "") or "").strip()
    if chat:
        transaction.on_commit(lambda: _send(chat, text))


def _header(organization_id: Any) -> str:
    """
    Bog'cha nomi — xabarning birinchi qatori (audit 2026-11-12).

    Bitta ega ikki bog'cha ochishi mumkin, bot esa bitta: "Storno 500 000"
    qaysi bog'chada bo'lganini xabarning o'zi aytishi kerak.
    """
    from apps.organizations.models import Organization

    name = Organization.objects.filter(pk=organization_id).values_list("name", flat=True).first()
    return f"🏫 {name}" if name else ""


def notify(*, organization_id: Any, text: str) -> None:
    """Tranzaksiya tasdiqlangach har bir qabul qiluvchiga."""
    chats = recipients(organization_id)
    if not chats:
        return
    header = _header(organization_id)
    if header:
        text = f"{header}\n{text}"

    def deliver() -> None:
        for chat in chats:
            _send(chat, text)

    transaction.on_commit(deliver)


def expense_recorded(expense: Any) -> None:
    """Chegaradan katta xarajat."""
    threshold = Decimal(str(_setting("alerts.expense_threshold", 5000000)))
    if expense.amount < threshold:
        return
    notify(
        organization_id=expense.organization_id,
        text=gettext("⚠️ Katta xarajat: {amount} soʻm — {category}. {note}").format(
            amount=_som(expense.amount),
            category=expense.category.name,
            note=expense.description or "",
        ),
    )


def benefit_given(discount: Any, percent: Decimal | None, amount: Decimal | None) -> None:
    """Katta imtiyoz — foizi yoki summasi chegaradan oshsa."""
    limit = Decimal(str(_setting("alerts.benefit_percent", 50)))
    if (percent is None or percent < limit) and (amount is None or amount < Decimal("1000000")):
        return
    rule = f"{percent:g}%" if percent is not None else f"{_som(amount or Decimal('0'))} soʻm"
    notify(
        organization_id=discount.organization_id,
        text=gettext("🎁 Imtiyoz: {child} — {kind} {rule}. Sabab: {reason}").format(
            child=discount.child.full_name,
            kind=discount.get_kind_display(),
            rule=rule,
            reason=discount.reason,
        ),
    )


def send_digest(*, organization: Any, day: date) -> int:
    """
    Kunlik xulosa: tushum usullar bo'yicha, xarajat, qoldiqlar, "Diqqat"
    soni. Qaytaradi: nechta odamga ketdi.
    """
    from apps.cash.selectors import account_balances
    from apps.expenses.models import Expense, ExpenseStatus
    from apps.finance.models import Payment, PaymentMethod
    from apps.intelligence.control import attention

    chats = recipients(organization.id)
    if not chats:
        return 0
    payments = (
        Payment.objects.filter(
            organization_id=organization.id, reversed_at__isnull=True, paid_at__date=day
        )
        .values("method")
        .order_by("method")
    )
    receipts = payments.annotate(total=Sum("amount"))
    spent = Expense.objects.filter(
        organization_id=organization.id,
        status__in=[ExpenseStatus.APPROVED, ExpenseStatus.PAID],
        expense_date=day,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    lines = [
        gettext("📊 {name} — kunlik xulosa, {day}").format(
            name=organization.name, day=day.strftime("%d.%m.%Y")
        )
    ]
    income = Decimal("0")
    for row in receipts:
        income += row["total"]
        label = str(PaymentMethod(row["method"]).label) if row["method"] else "—"
        lines.append(f"  {label}: {_som(row['total'])}")
    lines.insert(1, gettext("Tushum: {amount} soʻm").format(amount=_som(income)))
    lines.append(gettext("Xarajat: {amount} soʻm").format(amount=_som(spent)))
    for pot in account_balances(organization_id=organization.id):
        lines.append(f"{pot['name']}: {_som(Decimal(pot['balance']))}")
    count = len(attention(organization_id=organization.id, year=day.year, month=day.month))
    lines.append(gettext("Diqqat: {n}").format(n=count))
    text = "\n".join(lines)
    for chat in chats:
        _send(chat, text)
    return len(chats)
