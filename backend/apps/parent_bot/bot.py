"""
The parent bot's conversation (PLAN 6.2 / 6.3, design §3).

A Telegram update carries no tenant. Every answer therefore goes the same
way: the contact index names the organizations that know this chat (or
phone), and each of them is visited INSIDE its own context, where the
guardian → child chain is checked again from scratch. A guardian who has
left (`/stop`, archived) gets nothing, and a parent never sees another
family's child — the query is "children of the guardian behind this chat
in this organization", nothing wider.

Answers to the parent's own button presses are not notifications and are
not logged as such; messages the kindergarten initiates (receipt after a
payment, absence alert) still go through `notifications` (ADR-22).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from apps.core.tenancy import organization_context
from apps.parent_bot import texts
from apps.parent_bot.index import chat_digest, organizations_for, phone_digest
from apps.parent_bot.models import ContactKind

logger = logging.getLogger(__name__)

__all__ = ["Reply", "is_linked", "answer", "menu", "link_contact", "language_of"]


@dataclass
class Reply:
    body: str
    markup: dict[str, Any] | None = None
    outcome: str = "answered"
    sections: list[str] = field(default_factory=list)


def _money(amount: Decimal | int, language: str) -> str:
    grouped = f"{Decimal(amount):,.0f}".replace(",", " ")
    return f"{grouped} {texts.pick(texts.CURRENCY, language)}"


def _date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


def language_of(guardian: Any = None, fallback: str = "") -> str:
    candidate = (getattr(guardian, "language", "") or fallback or "uz").lower()[:2]
    return candidate if candidate in texts.LANGUAGES else "uz"


# --- Who is behind this chat ---


def _families(chat_id: str) -> list[tuple[str, Any]]:
    """`(organization_id, guardian)` pairs — each guardian read in its own org."""
    from apps.children import telegram as links

    found: list[tuple[str, Any]] = []
    for organization_id in organizations_for(ContactKind.CHAT, chat_digest(chat_id)):
        with organization_context(organization_id):
            found.extend((organization_id, g) for g in links.guardians_for_chat(chat_id))
    return found


def is_linked(chat_id: str) -> bool:
    return bool(_families(chat_id))


# --- The four buttons ---


def _balance(child: Any, language: str) -> list[str]:
    from apps.finance.balance import child_balance
    from apps.finance.selectors import open_invoices_fifo

    figures = child_balance(child)
    lines: list[str] = []
    if figures.balance > 0:
        lines.append(
            texts.pick(texts.DEBT, language).format(money=_money(figures.balance, language))
        )
        if figures.overdue_amount > 0:
            lines.append(
                texts.pick(texts.OVERDUE, language).format(
                    money=_money(figures.overdue_amount, language),
                    date=_date(figures.oldest_overdue_date),
                )
            )
        open_invoices = open_invoices_fifo(child)
        if open_invoices:
            lines.append(
                texts.pick(texts.NEXT_DUE, language).format(date=_date(open_invoices[0].due_date))
            )
    else:
        lines.append(texts.pick(texts.NO_DEBT, language))
    if figures.advance > 0:
        lines.append(
            texts.pick(texts.ADVANCE, language).format(money=_money(figures.advance, language))
        )
    return lines


def _invoices(child: Any, language: str) -> list[str]:
    from apps.finance.selectors import recent_invoices

    rows = recent_invoices(child)
    if not rows:
        return [texts.pick(texts.NO_INVOICES, language)]
    return [
        f"{invoice.period_month:02d}.{invoice.period_year} · {_money(invoice.amount_due, language)}"
        f" · {texts.pick(texts.INVOICE_STATUS.get(invoice.status, {}), language) or invoice.status}"
        for invoice in rows
    ]


def _receipts(child: Any, language: str) -> list[str]:
    from apps.finance.selectors import recent_payments

    rows = recent_payments(child)
    if not rows:
        return [texts.pick(texts.NO_RECEIPTS, language)]
    lines = []
    for payment in rows:
        method = texts.METHODS.get(payment.method)
        line = (
            f"{_date(payment.paid_at.date())} · {_money(payment.amount, language)}"
            f" · {texts.pick(method, language) if method else payment.method}"
        )
        if payment.is_reversed:
            line += f" ({texts.pick(texts.REVERSED, language)})"
        lines.append(line)
    return lines


def _pay_links(child: Any, language: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Lines for the message and `(label, url)` buttons for one child."""
    from apps.finance.selectors import open_invoices_fifo
    from apps.online_payments import services as online

    for invoice in open_invoices_fifo(child):
        payable = online.payable_amount(invoice)
        if payable is None:
            continue
        if not online.active_credentials():
            return [texts.pick(texts.PAY_OFFLINE, language)], []
        link = online.create_link(invoice=invoice, created_by=None)
        label = texts.pick(texts.PAY_BUTTON, language).format(
            child=child.first_name, money=_money(payable, language)
        )
        return [], [(label, online.public_url(link))]
    return [texts.pick(texts.NOTHING_TO_PAY, language)], []


def answer(chat_id: str, text: str) -> Reply | None:
    """
    A message from a chat. `None` — the chat is not linked to anyone, and
    the bot stays silent (it is not a chat partner, ADR-23).
    """
    families = _families(chat_id)
    if not families:
        return None

    language = language_of(families[0][1])
    action = texts.action_for(text)
    if action is None:
        return Reply(texts.pick(texts.MENU, language), texts.menu_keyboard(language), "menu")

    several_orgs = len({organization_id for organization_id, _ in families}) > 1
    blocks: list[str] = []
    buttons: list[tuple[str, str]] = []
    plain_links: list[str] = []
    for organization_id, guardian in families:
        with organization_context(organization_id):
            from apps.children import telegram as links

            children = links.children_of(guardian)
            if several_orgs:
                blocks.append(f"🏫 {guardian.organization.name}")
            if not children:
                blocks.append(texts.pick(texts.NO_CHILDREN, language))
                continue
            for child in children:
                if action == "balance":
                    lines = _balance(child, language)
                elif action == "invoices":
                    lines = _invoices(child, language)
                elif action == "receipts":
                    lines = _receipts(child, language)
                else:
                    lines, child_buttons = _pay_links(child, language)
                    for label, url in child_buttons:
                        if url.startswith("https://"):
                            buttons.append((label, url))
                        else:  # Telegram refuses non-https button URLs (dev)
                            plain_links.append(f"{label}: {url}")
                blocks.append("\n".join([f"👶 {child.full_name}", *lines]))

    if action == "pay" and (buttons or plain_links):
        blocks.insert(0, texts.pick(texts.PAY_INTRO, language))
        blocks.extend(plain_links)
    markup = (
        {"inline_keyboard": [[{"text": label, "url": url}] for label, url in buttons]}
        if buttons
        else texts.menu_keyboard(language)
    )
    return Reply("\n\n".join(blocks), markup, action)


def menu(chat_id: str, fallback_language: str = "") -> Reply:
    """`/start` without a code: the menu for a linked chat, the invitation otherwise."""
    families = _families(chat_id)
    if families:
        language = language_of(families[0][1])
        return Reply(texts.pick(texts.MENU, language), texts.menu_keyboard(language), "menu")
    language = language_of(fallback=fallback_language)
    return Reply(
        texts.pick(texts.START_UNLINKED, language), texts.share_phone_keyboard(language), "help"
    )


def link_contact(
    *, chat_id: str, contact: dict[str, Any], sender_id: Any, fallback_language: str = ""
) -> Reply:
    """
    The parent pressed "share my phone number" (ADR-27).

    Only the sender's OWN contact counts: Telegram lets anyone forward
    someone else's contact card, and that must not link a stranger's chat
    to a family. `contact.user_id == from.id` is Telegram's own statement
    that the number belongs to this account.
    """
    from apps.children import telegram as links

    language = language_of(fallback=fallback_language)
    if not sender_id or str(contact.get("user_id") or "") != str(sender_id):
        return Reply(texts.pick(texts.NOT_OWN_PHONE, language), None, "not_own_phone")

    phone = str(contact.get("phone_number") or "")
    linked: list[Any] = []
    for organization_id in organizations_for(ContactKind.PHONE, phone_digest(phone)):
        with organization_context(organization_id):
            guardian = links.link_by_phone(phone=phone, chat_id=chat_id)
            if guardian is not None:
                linked.append(guardian)

    if not linked:
        return Reply(texts.pick(texts.PHONE_UNKNOWN, language), None, "phone_unknown")

    language = language_of(linked[0], fallback_language)
    logger.info("Telegram linked by phone: %s guardian(s)", len(linked))
    return Reply(
        texts.pick(texts.PHONE_LINKED, language).format(name=linked[0].first_name or ""),
        texts.menu_keyboard(language),
        "linked_by_phone",
    )
