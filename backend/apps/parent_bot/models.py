"""
Contact index — how the bot finds a parent's kindergarten (ADR-27).

A Telegram update arrives with no tenant: just a chat id, or a phone
number the parent shared. Finding the guardian behind it is a search
ACROSS organizations, and the operational tables deliberately have no
exit for that (ADR-10) — widening RLS for the bot was already rejected
once (ADR-23).

So the bot asks a narrow question first — "which organizations know
this contact?" — of this table, and then works inside each of those
organizations' own context as usual. The table holds no phone number
and no chat id, only `HMAC-SHA256(CONTACT_INDEX_KEY, value)`: read on
its own it cannot answer "whose number is this" or "which family is in
which kindergarten". It is metadata (readable in platform mode), and it
is derived — rebuilt at any time by `rebuild_contact_index`.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantScopedModel

__all__ = ["ContactKind", "ContactIndex"]


class ContactKind(models.TextChoices):
    PHONE = "phone", "Phone"
    CHAT = "chat", "Telegram chat"
    # Xodimning suhbati (Bosqich 13.3c) — ota-onanikidan alohida, bot uni
    # vasiy deb adashmasin.
    STAFF = "staff", "Staff Telegram chat"


class ContactIndex(TenantScopedModel):
    kind = models.CharField(max_length=5, choices=ContactKind.choices)
    digest = models.CharField(max_length=64)

    class Meta:
        db_table = "contact_index"
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "digest", "organization"], name="uq_contact_index_entry"
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=["phone", "chat", "staff"]),
                name="ck_contact_index_kind",
            ),
        ]
        indexes = [models.Index(fields=["kind", "digest"], name="ix_contact_index_lookup")]

    def __str__(self) -> str:
        return f"{self.kind}:{self.digest[:8]}…"
