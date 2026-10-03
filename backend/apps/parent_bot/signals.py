"""Keeps the contact index current on every guardian save (ADR-27)."""

from __future__ import annotations

import logging
from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="children.Guardian", dispatch_uid="parent_bot_index_guardian")
def index_guardian(sender: Any, instance: Any, **kwargs: Any) -> None:
    from apps.parent_bot.index import entries_for_guardian, remember

    try:
        remember(organization_id=instance.organization_id, entries=entries_for_guardian(instance))
    except Exception:  # noqa: BLE001 — the index is derived; saving the guardian must not fail
        logger.exception("Contact index not updated for guardian %s", instance.pk)
