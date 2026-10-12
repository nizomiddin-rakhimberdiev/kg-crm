"""Telegram webhook xavfsizligi, ulash havolalari va API (docs/08 §5–6)."""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.core.tenancy import organization_context, platform_context
from apps.memories import services
from apps.memories.models import ChatKind, MemoryPhoto, PairingToken, TelegramChat
from apps.memories.tests.factories import jpeg, link_chat, make_family, next_chat_id

pytestmark = pytest.mark.django_db

SECRET = {"HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN": "test-webhook-secret-0123456789"}
URL = "/api/v1/telegram/webhook"


def _msg(chat_id, text=None, chat_type="private", **extra):
    message = {
        "chat": {"id": chat_id, "type": chat_type, "first_name": "Ona"},
        "from": {"first_name": "Ona", "language_code": "ru"},
        "date": int(timezone.now().timestamp()),
    }
    if text:
        message["text"] = text
    message.update(extra)
    return {"update_id": 1, "message": message}


def post(api_client, payload, headers=SECRET):
    return api_client.post(URL, payload, format="json", **headers)


# --- Webhook autentifikatsiyasi ---


@pytest.mark.parametrize("headers", [{}, {"HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN": "wrong"}])
def test_webhook_rejects_missing_or_wrong_secret(api_client, headers, _telegram_recorder):
    assert post(api_client, _msg(1, "/help"), headers).status_code == 404
    assert _telegram_recorder.messages == []


def test_webhook_is_closed_when_secret_unset(api_client, settings, _telegram_recorder):
    settings.TELEGRAM_WEBHOOK_SECRET = ""
    assert (
        api_client.post(
            URL, _msg(1, "/help"), format="json", HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN=""
        ).status_code
        == 404
    )


def test_webhook_swallows_garbage_payload(api_client):
    assert post(api_client, {"message": "yo'q"}).status_code == 200
    assert post(api_client, {"message": {"chat": {"id": "x"}}}).status_code == 200


def test_unlinked_private_chat_is_told_to_link(api_client, _telegram_recorder):
    post(api_client, _msg(777, "/photos"))
    ((chat, text),) = _telegram_recorder.messages
    assert chat == 777 and "не подключён" in text  # Telegram tili (ru) bo'yicha


def test_unlinked_group_stays_silent(api_client, _telegram_recorder):
    post(api_client, _msg(-888, "salom", chat_type="supergroup"))
    assert _telegram_recorder.messages == []


# --- Ulash havolalari ---


def _pair(tenant, kind, **kw):
    with organization_context(tenant.organization.id):
        result = services.issue_pairing(
            organization=tenant.organization, branch=tenant.branch, kind=kind, **kw
        )
    return result["url"].split("=", 1)[1]


def test_parent_pairing_links_chat_and_token_is_single_use(
    tenant_a, api_client, _telegram_recorder
):
    _, guardian = make_family(tenant_a, "Ali", "200001")
    token = _pair(tenant_a, ChatKind.PARENT, guardian=guardian)
    cid = next_chat_id()
    post(api_client, _msg(cid, f"/start {token}"))
    with platform_context():
        chat = TelegramChat.all_objects.get(chat_id=cid)
    assert (
        chat.kind == ChatKind.PARENT and chat.guardian_id == guardian.id and chat.language == "ru"
    )
    assert "Вы подключены" in _telegram_recorder.messages[-1][1]
    # Ikkinchi urinish — havola o'lik.
    post(api_client, _msg(next_chat_id(), f"/start {token}"))
    assert "недействительна" in _telegram_recorder.messages[-1][1]


def test_token_is_stored_hashed(tenant_a):
    _, guardian = make_family(tenant_a, "Ali", "200002")
    token = _pair(tenant_a, ChatKind.PARENT, guardian=guardian)
    secret = token.split("_", 1)[1]
    with organization_context(tenant_a.organization.id):
        assert not PairingToken.objects.filter(token_hash__contains=secret).exists()


def test_expired_and_forged_tokens_are_rejected(tenant_a, api_client, _telegram_recorder):
    _, guardian = make_family(tenant_a, "Ali", "200003")
    token = _pair(tenant_a, ChatKind.PARENT, guardian=guardian)
    with organization_context(tenant_a.organization.id):
        PairingToken.objects.update(expires_at=timezone.now() - timezone.timedelta(minutes=1))
    for bad in (token, "zzzz", f"{'0' * 32}_abc", token + "x"):
        post(api_client, _msg(next_chat_id(), f"/start {bad}"))
        assert "недействительна" in _telegram_recorder.messages[-1][1]


def test_group_token_cannot_be_used_in_private_chat(tenant_a, api_client, _telegram_recorder):
    token = _pair(tenant_a, ChatKind.GROUP)
    post(api_client, _msg(next_chat_id(), f"/start {token}", chat_type="private"))
    with platform_context():
        assert not TelegramChat.all_objects.filter(kind=ChatKind.GROUP).exists()
    assert "другого типа" in _telegram_recorder.messages[-1][1]


def test_chat_of_one_org_cannot_be_hijacked_by_another(tenant_a, tenant_b, api_client):
    link_chat(tenant_a, ChatKind.GROUP)
    with platform_context():
        chat_id = TelegramChat.all_objects.get().chat_id
    token_b = _pair(tenant_b, ChatKind.GROUP)
    post(
        api_client,
        _msg(
            chat_id,
            f"/start {token_b}",
            chat_type="group",
        ),
    )
    with platform_context():
        assert (
            TelegramChat.all_objects.get(chat_id=chat_id).organization_id
            == tenant_a.organization.id
        )


# --- Guruh → ota-ona oqimi ---


def test_group_photo_message_reaches_parent_end_to_end(
    tenant_a, api_client, _telegram_recorder, django_capture_on_commit_callbacks
):
    ali, guardian = make_family(tenant_a, "Ali", "200004")
    with organization_context(tenant_a.organization.id):
        services.grant_consent(child=ali, guardian=guardian)
        services.enroll_face(child=ali, image_bytes=jpeg("ali"))
    parent = link_chat(tenant_a, ChatKind.PARENT, guardian=guardian)
    group = link_chat(tenant_a, ChatKind.GROUP)
    _telegram_recorder.files["F1"] = jpeg("ali", "boshqa")

    with django_capture_on_commit_callbacks(execute=True):
        post(
            api_client,
            _msg(
                group.chat_id,
                chat_type="supergroup",
                photo=[{"file_id": "small"}, {"file_id": "F1"}],
                message_id=5,
            ),
        )

    assert [c for c, *_ in _telegram_recorder.photos] == [parent.chat_id]
    assert any(c == group.chat_id for c, _ in _telegram_recorder.messages)  # o'qituvchiga hisobot
    with organization_context(tenant_a.organization.id):
        photo = MemoryPhoto.objects.get()
        assert photo.source == "telegram" and photo.faces_detected == 2


def test_parent_gets_only_own_child_in_album(tenant_a, api_client, _telegram_recorder):
    ali, ali_p = make_family(tenant_a, "Ali", "200005")
    vali, vali_p = make_family(tenant_a, "Vali", "200006")
    with organization_context(tenant_a.organization.id):
        for child, guardian, name in ((ali, ali_p, "ali"), (vali, vali_p, "vali")):
            services.grant_consent(child=child, guardian=guardian)
            services.enroll_face(child=child, image_bytes=jpeg(name))
        a = link_chat(tenant_a, ChatKind.PARENT, guardian=ali_p, language="en")
        services.process_photo(
            services.store_photo(branch=tenant_a.branch, data=jpeg("vali", seed=1), source="upload")
        )
        services.process_photo(
            services.store_photo(branch=tenant_a.branch, data=jpeg("ali", seed=2), source="upload")
        )
    _telegram_recorder.photos.clear()
    _telegram_recorder.messages.clear()

    post(api_client, _msg(a.chat_id, "/photos"))
    assert len(_telegram_recorder.photos) == 1
    assert all("Ali" in caption for *_, caption in _telegram_recorder.photos)
    assert "1 photos found" in _telegram_recorder.messages[0][1]


def test_language_command_switches_bot_language(tenant_a, api_client, _telegram_recorder):
    _, guardian = make_family(tenant_a, "Ali", "200007")
    chat = link_chat(tenant_a, ChatKind.PARENT, guardian=guardian)
    post(api_client, _msg(chat.chat_id, "/language en"))
    assert _telegram_recorder.messages[-1][1] == "Language changed."
    post(api_client, _msg(chat.chat_id, "/menu"))
    assert "not been entered" in _telegram_recorder.messages[-1][1]
    post(api_client, _msg(chat.chat_id, "/language xx"))  # noma'lum til — o'zgarmaydi
    with organization_context(tenant_a.organization.id):
        assert TelegramChat.objects.get(pk=chat.pk).language == "en"


# --- Boshqaruv API ---


def test_pairing_endpoint_returns_deep_link(tenant_a):
    _, guardian = make_family(tenant_a, "Ali", "200008")
    resp = tenant_a.client().post(
        "/api/v1/telegram-chats/pairing",
        {"kind": "parent", "guardian_id": str(guardian.id)},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["data"]["url"].startswith("https://t.me/radix_test_bot?start=")


def test_pairing_with_foreign_guardian_is_rejected(tenant_a, tenant_b):
    _, foreign = make_family(tenant_b, "Beta", "200009")
    resp = tenant_a.client().post(
        "/api/v1/telegram-chats/pairing",
        {"kind": "parent", "guardian_id": str(foreign.id)},
        format="json",
    )
    assert resp.status_code == 400


def test_upload_and_authenticated_image_download(tenant_a, tenant_b):
    client = tenant_a.client()
    resp = client.post(
        "/api/v1/memory-photos",
        {"image": SimpleUploadedFile("a.jpg", jpeg(), "image/jpeg")},
        format="multipart",
    )
    assert resp.status_code == 201, resp.content
    photo_id = resp.json()["data"]["id"]
    img = client.get(f"/api/v1/memory-photos/{photo_id}/image")
    assert img.status_code == 200 and img["Cache-Control"] == "private, no-store"
    assert tenant_b.client().get(f"/api/v1/memory-photos/{photo_id}/image").status_code == 404


def test_upload_rejects_non_images(tenant_a):
    resp = tenant_a.client().post(
        "/api/v1/memory-photos",
        {"image": SimpleUploadedFile("a.jpg", b"<?php", "image/jpeg")},
        format="multipart",
    )
    assert resp.status_code == 400
    resp = tenant_a.client().post(
        "/api/v1/memory-photos",
        {"image": SimpleUploadedFile("a.svg", b"<svg/>", "image/svg+xml")},
        format="multipart",
    )
    assert resp.status_code == 400


def test_cashier_without_permission_is_forbidden(tenant_a):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with organization_context(tenant_a.organization.id):
        user = User.objects.create_user(
            email="kassir@alfa.uz",
            password="Juda-Kuchli-Parol-2026",
            full_name="Kassir",
            organization=tenant_a.organization,
            role=tenant_a.role("cashier"),
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    for path in ("memory-photos", "cameras", "camera-events", "face-consents", "telegram-chats"):
        assert client.get(f"/api/v1/{path}").status_code == 403, path


def test_camera_stream_url_is_encrypted_and_never_returned(tenant_a):
    client = tenant_a.client()
    resp = client.post(
        "/api/v1/cameras",
        {"name": "Kirish", "stream_url": "rtsp://admin:parol@10.0.0.5/1"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()["data"]
    assert "stream_url" not in body and body["has_stream"] is True
    from apps.memories.models import Camera

    with organization_context(tenant_a.organization.id):
        raw = Camera.objects.get().stream_url
    assert "parol" not in raw and raw.startswith("gAAAA")
    bad = client.post(
        "/api/v1/cameras", {"name": "X", "stream_url": "file:///etc/passwd"}, format="json"
    )
    assert bad.status_code == 400


def test_camera_event_api_alerts_staff_and_can_be_acknowledged(tenant_a, _telegram_recorder):
    link_chat(tenant_a, ChatKind.STAFF, user=tenant_a.owner, language="en")
    client = tenant_a.client()
    resp = client.post(
        "/api/v1/camera-events",
        {
            "kind": "child_distress",
            "severity": "critical",
            "note": "Yig'layapti",
            "snapshot": SimpleUploadedFile("s.jpg", jpeg(), "image/jpeg"),
        },
        format="multipart",
    )
    assert resp.status_code == 201, resp.content
    event = resp.json()["data"]
    assert len(_telegram_recorder.photos) == 1
    assert "Child is crying" in _telegram_recorder.photos[0][2]
    ack = client.post(f"/api/v1/camera-events/{event['id']}/acknowledge")
    assert ack.json()["data"]["status"] == "acknowledged"
    assert client.get(f"/api/v1/camera-events/{event['id']}/snapshot").status_code == 200


def test_consent_enroll_revoke_via_api(tenant_a, tenant_b):
    child, guardian = make_family(tenant_a, "Ali", "200010")
    client = tenant_a.client()
    made = client.post(
        "/api/v1/face-consents",
        {"child_id": str(child.id), "guardian_id": str(guardian.id)},
        format="json",
    )
    assert made.status_code == 201, made.content
    cid = made.json()["data"]["id"]
    enrolled = client.post(
        f"/api/v1/face-consents/{cid}/enroll",
        {"image": SimpleUploadedFile("f.jpg", jpeg("ali"), "image/jpeg")},
        format="multipart",
    )
    assert enrolled.status_code == 201 and enrolled.json()["data"]["samples"] == 1
    assert tenant_b.client().post(f"/api/v1/face-consents/{cid}/revoke").status_code == 404
    revoked = client.post(f"/api/v1/face-consents/{cid}/revoke")
    assert revoked.status_code == 200 and revoked.json()["data"]["samples"] == 0
    assert client.post(f"/api/v1/face-consents/{cid}/revoke").status_code == 422
