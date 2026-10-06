"""
Maintaining and reading the contact index (ADR-27).

Writes happen inside the guardian's own organization context (a signal
on every guardian save, see `signals.py`); the one cross-tenant read —
"which organizations know this contact?" — asks for `platform_context()`
by name, and the table it reads holds only HMAC digests.

Stale rows are harmless by construction: the bot always re-checks the
guardian inside the organization, so an old digest leads to "nobody
here" rather than to the wrong family. `rebuild_contact_index` removes
them.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Iterable
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction

from apps.core.phone import PhoneFormatError, normalise_phone
from apps.core.tenancy import platform_context
from apps.parent_bot.models import ContactIndex, ContactKind

__all__ = [
    "digest",
    "phone_digest",
    "chat_digest",
    "organizations_for",
    "remember",
    "forget_chat",
    "entries_for_guardian",
]


def _key() -> bytes:
    """
    `CONTACT_INDEX_KEY`, or a key derived from `SECRET_KEY` when unset.

    Changing either makes every stored digest unfindable — the bot then
    answers "not linked" until `rebuild_contact_index --apply` runs.
    """
    configured = str(getattr(settings, "CONTACT_INDEX_KEY", "") or "")
    if configured:
        return configured.encode()
    return hashlib.sha256(f"contact-index:{settings.SECRET_KEY}".encode()).digest()


def digest(kind: str, value: str) -> str:
    message = f"{kind}:{value}".encode()
    raw = hmac.new(_key(), message, hashlib.sha256).digest()
    return base64.b16encode(raw).decode().lower()


def phone_digest(phone: str) -> str | None:
    """Digest of a phone in its one canonical form; `None` if it is not a valid number."""
    try:
        normalised = normalise_phone(phone)
    except PhoneFormatError:
        return None
    return digest(ContactKind.PHONE, normalised) if normalised else None


def chat_digest(chat_id: str) -> str | None:
    cleaned = (chat_id or "").strip()
    return digest(ContactKind.CHAT, cleaned) if cleaned else None


def organizations_for(kind: str, value_digest: str | None) -> list[str]:
    """The only cross-tenant read: organization ids that know this digest."""
    if not value_digest:
        return []
    with platform_context():
        return [
            str(organization_id)
            for organization_id in ContactIndex.all_objects.filter(
                kind=kind, digest=value_digest, is_active=True
            )
            .values_list("organization_id", flat=True)
            .distinct()
        ]


def remember(*, organization_id: Any, entries: Iterable[tuple[str, str]]) -> int:
    """Adds `(kind, digest)` rows for one organization; existing ones are kept."""
    created = 0
    for kind, value_digest in entries:
        if not value_digest:
            continue
        try:
            with transaction.atomic():
                _, was_created = ContactIndex.all_objects.get_or_create(
                    organization_id=organization_id, kind=kind, digest=value_digest
                )
        except IntegrityError:  # a concurrent save wrote the same row
            continue
        created += int(was_created)
    return created


def forget_chat(chat_id: str, *, organization_ids: Iterable[Any]) -> int:
    """`/stop`: drop the chat's rows, each inside its own organization."""
    from apps.core.tenancy import organization_context

    value_digest = chat_digest(chat_id)
    if not value_digest:
        return 0
    removed = 0
    for organization_id in organization_ids:
        with organization_context(organization_id):
            removed += ContactIndex.all_objects.filter(
                organization_id=organization_id, kind=ContactKind.CHAT, digest=value_digest
            ).delete()[0]
    return removed


def entries_for_guardian(guardian: Any) -> list[tuple[str, str]]:
    """What a guardian row contributes to the index."""
    entries: list[tuple[str, str]] = []
    if not getattr(guardian, "is_active", True):
        return entries
    # Ikkala raqam ham indeksga tushadi (PLAN 7.4): ota-ona botga
    # qaysi SIM'dan yozsa ham topilishi kerak.
    for number in (getattr(guardian, "phone", ""), getattr(guardian, "phone_alt", "")):
        digest_value = phone_digest(number or "")
        if digest_value:
            entries.append((ContactKind.PHONE, digest_value))
    chat = chat_digest(getattr(guardian, "telegram_chat_id", "") or "")
    if chat:
        entries.append((ContactKind.CHAT, chat))
    return entries
