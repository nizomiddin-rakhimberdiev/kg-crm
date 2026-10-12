"""Radix AI testlari uchun yordamchilar (haqiqiy JPEG + `FACE:` belgisi)."""

from __future__ import annotations

from datetime import date, time
from typing import Any

import cv2
import numpy as np
from django.utils import timezone

from apps.children.models import Child, ChildGuardian, Guardian
from apps.core.tenancy import organization_context
from apps.memories import services
from apps.memories.models import (
    Camera,
    CameraEvent,
    ChatKind,
    DayScheduleItem,
    PhotoSource,
    TelegramChat,
)

_chat_seq = [1000]


def jpeg(*names: str, seed: int = 0) -> bytes:
    """Shovqinli haqiqiy JPEG; oxirida FakeEngine o'qiydigan yuz belgisi."""
    rng = np.random.default_rng(seed)
    img = rng.integers(0, 255, (200, 300, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    data = buf.tobytes()
    return data + (b"\nFACE:" + ";".join(names).encode() if names else b"")


def next_chat_id() -> int:
    _chat_seq[0] += 1
    return _chat_seq[0]


def make_family(tenant: Any, first_name: str, phone_tail: str) -> tuple[Child, Guardian]:
    with organization_context(tenant.organization.id):
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=first_name,
            last_name="Test",
            date_of_birth=date(2021, 1, 1),
            gender="male",
        )
        guardian = Guardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ota",
            last_name=first_name,
            phone=f"+998900{phone_tail}",
        )
        ChildGuardian.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            child=child,
            guardian=guardian,
            relation="mother",
            is_primary=True,
        )
    return child, guardian


def link_chat(
    tenant: Any, kind: str, *, guardian: Any = None, user: Any = None, language: str = "uz"
) -> TelegramChat:
    with organization_context(tenant.organization.id):
        return TelegramChat.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            chat_id=next_chat_id(),
            kind=kind,
            guardian=guardian,
            user=user,
            language=language,
            title="t",
        )


def make_memories_row(tenant: Any, basename: str) -> Any:
    """Cross-tenant sweep uchun: berilgan endpoint turidagi bitta qator."""
    with organization_context(tenant.organization.id):
        org, branch = tenant.organization, tenant.branch
        if basename in {"memory-photo", "photo-tag"}:
            photo = services.store_photo(branch=branch, data=jpeg(), source=PhotoSource.UPLOAD)
            if basename == "memory-photo":
                return photo
            child, guardian = make_family(tenant, "Sweep", f"{abs(hash(org.slug)) % 10_000:04d}00")
            services.grant_consent(child=child, guardian=guardian)
            return services.tag_manually(photo=photo, child=child)
        if basename == "face-consent":
            child, guardian = make_family(tenant, "Rozi", f"{abs(hash(org.slug)) % 10_000:04d}11")
            return services.grant_consent(child=child, guardian=guardian)
        if basename == "schedule-item":
            return DayScheduleItem.objects.create(
                organization=org,
                branch=branch,
                kind="menu",
                on_date=timezone.localdate(),
                at_time=time(8, 0),
                title="Sho'rva",
            )
        if basename == "camera":
            return Camera.objects.create(organization=org, branch=branch, name="Kirish")
        if basename == "camera-event":
            return CameraEvent.objects.create(
                organization=org, branch=branch, kind="safety", occurred_at=timezone.now()
            )
        if basename == "telegram-chat":
            return TelegramChat.objects.create(
                organization=org, branch=branch, chat_id=next_chat_id(), kind=ChatKind.GROUP
            )
    raise AssertionError(basename)
