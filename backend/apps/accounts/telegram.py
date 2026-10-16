"""
Xodimni Telegram botga ulash (Bosqich 13.3c).

Ota-ona havolasi bilan bir xil yo'l (ADR-23): kod tashkilotni o'z ichida
olib yuradi, webhook uni ochib TO'G'RI tashkilot kontekstini o'rnatadi va
xodimni shu chegara ichida topadi — RLS kengaytirilmaydi. Farqi faqat
`s_` old qo'shimchasi: bot qaysi havola ekanini biladi.

Suhbatdan tashkilotga yo'l — `ContactIndex(kind=staff)` (xeshlangan
chat id): ota-ona suhbatlari bilan aralashmaydi.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.accounts.models import User
from apps.core.tenancy import organization_context

__all__ = ["PREFIX", "link_url", "link_staff", "staff_for_chat", "unlink"]

PREFIX = "s_"


def link_url(user: User) -> str:
    """Yangi bir martalik havola — eskisi bekor bo'ladi."""
    from apps.children.telegram import bot_username, build_code

    user.telegram_code = PREFIX + build_code(user.organization_id)
    user.save(update_fields=["telegram_code", "updated_at"])
    username = bot_username() or "bot"
    return f"https://t.me/{username}?start={user.telegram_code}"


def link_staff(*, code: str, chat_id: str) -> User | None:
    """`/start s_<kod>` — suhbatni xodimga bog'laydi; kod bir martalik."""
    from apps.children.telegram import organization_from_code
    from apps.parent_bot.index import chat_digest, remember
    from apps.parent_bot.models import ContactKind

    cleaned = (code or "").strip()
    if not cleaned.startswith(PREFIX) or not chat_id:
        return None
    organization_id = organization_from_code(cleaned[len(PREFIX) :])
    if organization_id is None:
        return None
    with organization_context(organization_id):
        user = User.objects.filter(telegram_code=cleaned, is_active=True).first()
        if user is None:
            return None
        User.objects.filter(telegram_chat_id=chat_id).exclude(pk=user.pk).update(
            telegram_chat_id="", telegram_linked_at=None
        )
        user.telegram_chat_id = chat_id
        user.telegram_code = ""
        user.telegram_linked_at = timezone.now()
        user.save(
            update_fields=["telegram_chat_id", "telegram_code", "telegram_linked_at", "updated_at"]
        )
        remember(
            organization_id=organization_id,
            entries=[(ContactKind.STAFF, chat_digest(chat_id) or "")],
        )
        return user


def staff_for_chat(chat_id: str) -> tuple[str, Any] | None:
    """Suhbat → (tashkilot, xodim); ulanmagan bo'lsa `None`."""
    from apps.parent_bot.index import chat_digest, organizations_for
    from apps.parent_bot.models import ContactKind

    for organization_id in organizations_for(ContactKind.STAFF, chat_digest(chat_id)):
        with organization_context(organization_id):
            user = User.objects.filter(telegram_chat_id=chat_id, is_active=True).first()
            if user is not None:
                return str(organization_id), user
    return None


def unlink(user: User) -> None:
    user.telegram_chat_id = ""
    user.telegram_code = ""
    user.telegram_linked_at = None
    user.save(
        update_fields=["telegram_chat_id", "telegram_code", "telegram_linked_at", "updated_at"]
    )
