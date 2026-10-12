"""Radix AI asosiy oqimi: rozilik → vektor → tanish → yuborish (docs/08)."""

from __future__ import annotations

import cv2
import numpy as np
import pytest
from django.utils import timezone

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.memories import services
from apps.memories.models import ChatKind, FaceSample, PhotoSource, PhotoTag, TagStatus
from apps.memories.tests.factories import jpeg, link_chat, make_family

pytestmark = pytest.mark.django_db


def _enroll(tenant, child, guardian, name):
    services.grant_consent(child=child, guardian=guardian)
    services.enroll_face(child=child, image_bytes=jpeg(name))


@pytest.fixture
def families(tenant_a):
    with organization_context(tenant_a.organization.id):
        pass
    ali, ali_p = make_family(tenant_a, "Ali", "100001")
    vali, vali_p = make_family(tenant_a, "Vali", "100002")
    return ali, ali_p, vali, vali_p


def test_enroll_requires_consent(tenant_a, families):
    ali, *_ = families
    with organization_context(tenant_a.organization.id), pytest.raises(BusinessRuleViolation):
        services.enroll_face(child=ali, image_bytes=jpeg("ali"))


def test_embedding_is_encrypted_at_rest(tenant_a, families):
    ali, ali_p, *_ = families
    with organization_context(tenant_a.organization.id):
        _enroll(tenant_a, ali, ali_p, "ali")
        raw = bytes(FaceSample.objects.get(child=ali).embedding)
    plain = np.float32(0).tobytes()
    assert raw.startswith(b"gAAAA")  # Fernet tokeni, xom float32 emas
    assert len(raw) > 128 * len(plain)


def test_enroll_needs_exactly_one_face(tenant_a, families):
    ali, ali_p, *_ = families
    with organization_context(tenant_a.organization.id):
        services.grant_consent(child=ali, guardian=ali_p)
        for data in (jpeg(), jpeg("ali", "vali")):
            with pytest.raises(BusinessRuleViolation):
                services.enroll_face(child=ali, image_bytes=data)


def test_group_photo_goes_only_to_matching_parents_and_blurs_others(
    tenant_a, families, _telegram_recorder
):
    ali, ali_p, vali, vali_p = families
    with organization_context(tenant_a.organization.id):
        _enroll(tenant_a, ali, ali_p, "ali")
        _enroll(tenant_a, vali, vali_p, "vali")
        ali_chat = link_chat(tenant_a, ChatKind.PARENT, guardian=ali_p, language="ru")
        vali_chat = link_chat(tenant_a, ChatKind.PARENT, guardian=vali_p)
        original = jpeg("ali", "vali", "nomalum", seed=3)
        photo = services.store_photo(
            branch=tenant_a.branch, data=original, source=PhotoSource.UPLOAD
        )
        result = services.process_photo(photo)

    assert result == {"matched": 2, "unknown": 1, "sent": 2}
    sent = {chat_id: (data, caption) for chat_id, data, caption in _telegram_recorder.photos}
    assert set(sent) == {ali_chat.chat_id, vali_chat.chat_id}
    # Til chatga bog'liq: ruscha chatda sarlavha uzbekcha emas.
    assert "Ali" in sent[ali_chat.chat_id][1]

    # Begona yuz xiralashgan: Ali yuboriladigan rasmda Vali qutisining tafsiloti kamaygan.
    def region(data, box):
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_GRAYSCALE)
        h, w = img.shape
        x, y, bw, bh = box
        return img[int(y * h) : int((y + bh) * h), int(x * w) : int((x + bw) * w)].astype(float)

    with organization_context(tenant_a.organization.id):
        vali_box = PhotoTag.objects.get(child=vali).box
        ali_box = PhotoTag.objects.get(child=ali).box
    got = sent[ali_chat.chat_id][0]
    assert region(got, vali_box).std() < region(original, vali_box).std() * 0.6
    # Bolaning o'z yuzi tegilmagan (qayta kodlash bundan mustasno, shovqin saqlanadi).
    assert region(got, ali_box).std() > region(original, ali_box).std() * 0.6


def test_revoking_consent_deletes_vectors_and_stops_recognition(
    tenant_a, families, _telegram_recorder
):
    ali, ali_p, *_ = families
    with organization_context(tenant_a.organization.id):
        _enroll(tenant_a, ali, ali_p, "ali")
        link_chat(tenant_a, ChatKind.PARENT, guardian=ali_p)
        assert services.revoke_consent(child=ali) == 1
        assert not FaceSample.objects.filter(child=ali).exists()
        photo = services.store_photo(
            branch=tenant_a.branch, data=jpeg("ali"), source=PhotoSource.UPLOAD
        )
        assert services.process_photo(photo)["matched"] == 0
    assert _telegram_recorder.photos == []


def test_suggested_tag_is_not_sent_until_confirmed(
    tenant_a, families, _telegram_recorder, settings, django_capture_on_commit_callbacks
):
    ali, ali_p, *_ = families
    settings.FACE_MATCH_THRESHOLD = (
        1.5  # taxminiy tegni majburlash: auto-confirm hech qachon bo'lmaydi
    )
    with organization_context(tenant_a.organization.id):
        _enroll(tenant_a, ali, ali_p, "ali")
        photo = services.store_photo(
            branch=tenant_a.branch, data=jpeg("ali"), source=PhotoSource.UPLOAD
        )
        assert services.process_photo(photo) == {"matched": 0, "unknown": 1, "sent": 0}

    settings.FACE_MATCH_THRESHOLD = 0.9
    with organization_context(tenant_a.organization.id):
        link_chat(tenant_a, ChatKind.PARENT, guardian=ali_p)
        tag = PhotoTag.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            photo=photo,
            child=ali,
            confidence=0.95,
            status=TagStatus.SUGGESTED,
        )
        assert services.deliver_tag(tag) == 0
        with django_capture_on_commit_callbacks(execute=True):
            services.set_tag_status(tag=tag, status=TagStatus.CONFIRMED)
    assert len(_telegram_recorder.photos) == 1


def test_manual_tag_needs_consent(tenant_a, families):
    ali, *_ = families
    with organization_context(tenant_a.organization.id):
        photo = services.store_photo(branch=tenant_a.branch, data=jpeg(), source=PhotoSource.UPLOAD)
        with pytest.raises(BusinessRuleViolation):
            services.tag_manually(photo=photo, child=ali)


def test_oversized_upload_is_rejected(tenant_a, settings):
    settings.MEMORIES_MAX_UPLOAD_BYTES = 100
    with organization_context(tenant_a.organization.id), pytest.raises(BusinessRuleViolation):
        services.store_photo(branch=tenant_a.branch, data=jpeg(), source=PhotoSource.UPLOAD)


def test_schedule_dispatch_sends_once_per_item(tenant_a, families, _telegram_recorder):
    from datetime import time

    from apps.memories.models import DayScheduleItem

    _, ali_p, *_ = families
    with organization_context(tenant_a.organization.id):
        chat = link_chat(tenant_a, ChatKind.PARENT, guardian=ali_p, language="en")
        DayScheduleItem.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            kind="menu",
            on_date=timezone.localdate(),
            at_time=time(0, 0),
            title="Soup",
        )
        DayScheduleItem.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            kind="activity",
            on_date=timezone.localdate(),
            at_time=time(23, 59),
            title="Later",
        )
        now = timezone.localtime().replace(hour=12, minute=0)
        assert services.dispatch_schedule(now) == 1
        assert services.dispatch_schedule(now) == 0  # takroran yuborilmaydi
    ((chat_id, text),) = _telegram_recorder.messages
    assert chat_id == chat.chat_id
    assert "Soup" in text and "Menu" in text and "Later" not in text


def test_camera_alert_goes_to_staff_with_photo_evidence(tenant_a, _telegram_recorder):
    from django.core.files.base import ContentFile

    from apps.memories.models import CameraEvent

    with organization_context(tenant_a.organization.id):
        chat = link_chat(tenant_a, ChatKind.STAFF, user=tenant_a.owner, language="ru")
        event = CameraEvent(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            kind="staff_violation",
            severity="critical",
            note="Telefon",
            occurred_at=timezone.now(),
        )
        event.snapshot.save("e.jpg", ContentFile(jpeg()), save=False)
        event.save()
        assert services.report_camera_event(event=event) == 1
        assert services.report_camera_event(event=event) == 0  # ikkinchi marta ogohlantirmaydi
    ((chat_id, data, caption),) = _telegram_recorder.photos
    assert chat_id == chat.chat_id and data[:2] == b"\xff\xd8"
    assert "Telefon" in caption


def test_info_events_do_not_alert(tenant_a, _telegram_recorder):
    from apps.memories.models import CameraEvent

    with organization_context(tenant_a.organization.id):
        link_chat(tenant_a, ChatKind.STAFF, user=tenant_a.owner)
        event = CameraEvent.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            kind="other",
            severity="info",
            occurred_at=timezone.now(),
        )
        assert services.report_camera_event(event=event) == 0
