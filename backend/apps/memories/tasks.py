"""Radix AI fon vazifalari."""

from __future__ import annotations

import logging

from apps.core.tasks import reliable_task
from apps.core.tenancy import organization_context, platform_context

logger = logging.getLogger(__name__)

__all__ = ["process_photo_task", "dispatch_schedule_task", "alert_event_task"]


@reliable_task(name="memories.process_photo")
def process_photo_task(
    organization_id: str, photo_id: str, report_chat_id: int | None = None
) -> dict[str, int]:
    from apps.memories.models import MemoryPhoto, TelegramChat
    from apps.memories.services import process_photo

    with organization_context(organization_id):
        photo = MemoryPhoto.objects.select_related("organization", "branch").get(pk=photo_id)
        chat = (
            TelegramChat.objects.filter(chat_id=report_chat_id).first() if report_chat_id else None
        )
        return process_photo(photo, report_chat=chat)


@reliable_task(name="memories.alert_event")
def alert_event_task(organization_id: str, event_id: str) -> int:
    from apps.memories.models import CameraEvent
    from apps.memories.services import report_camera_event

    with organization_context(organization_id):
        event = CameraEvent.objects.select_related("branch").get(pk=event_id)
        return report_camera_event(event=event)


@reliable_task(name="memories.dispatch_schedule")
def dispatch_schedule_task() -> int:
    from apps.memories.services import dispatch_schedule
    from apps.organizations.models import Organization

    with platform_context():
        organizations = list(Organization.objects.filter(is_active=True))
    total = 0
    for organization in organizations:
        with organization_context(organization.id):
            try:
                total += dispatch_schedule()
            except Exception:  # noqa: BLE001 — bitta tashkilot butun tsiklni to'xtatmasin
                logger.exception("Kun tartibi yuborilmadi: org=%s", organization.id)
    return total
