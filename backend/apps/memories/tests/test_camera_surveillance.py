"""Kuzatuv (so'nggi kadr) va webhook: maxfiylik, tenant izolyatsiyasi, token qoidalari."""

from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.core.tenancy import organization_context
from apps.memories.models import Camera, CameraEvent
from apps.memories.tests.factories import jpeg

INGEST = "/api/v1/camera-ingest"
HOOK = "/api/v1/camera-webhook"


def _camera(tenant) -> Camera:
    with organization_context(tenant.organization.id):
        return Camera.objects.create(
            organization=tenant.organization, branch=tenant.branch, name="Zal"
        )


def _issue(tenant, connection="edge") -> tuple[Camera, str]:
    cam = _camera(tenant)
    resp = tenant.client().post(
        f"/api/v1/cameras/{cam.id}/token", {"connection": connection}, format="json"
    )
    assert resp.status_code == 200, resp.content
    return cam, resp.json()["data"]["token"]


def _frame(token, data=None):
    return APIClient().post(
        INGEST,
        {"snapshot": SimpleUploadedFile("f.jpg", data or jpeg(), "image/jpeg")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )


def _enable(tenant, cam, value=True):
    return tenant.client().patch(
        f"/api/v1/cameras/{cam.id}", {"preview_enabled": value}, format="json"
    )


def test_preview_is_off_by_default_and_frame_is_ignored(tenant_a):
    cam, token = _issue(tenant_a)
    body = _frame(token).json()["data"]
    assert body["preview_wanted"] is False and "preview_saved" not in body
    assert tenant_a.client().get(f"/api/v1/cameras/{cam.id}/preview").status_code == 404


def test_enabled_preview_is_stored_served_privately_and_deleted_on_disable(tenant_a):
    cam, token = _issue(tenant_a)
    assert _enable(tenant_a, cam).status_code == 200
    body = _frame(token).json()["data"]
    assert body["preview_wanted"] is True and body["preview_saved"] is True
    got = tenant_a.client().get(f"/api/v1/cameras/{cam.id}/preview")
    assert got.status_code == 200
    assert (
        got["Cache-Control"] == "private, no-store" and got["X-Content-Type-Options"] == "nosniff"
    )
    row = tenant_a.client().get("/api/v1/cameras").json()["data"][0]
    assert row["has_preview"] is True
    # tez-tez yozilmaydi
    assert _frame(token).json()["data"]["preview_saved"] is False
    # o'chirilsa — fayl ham yo'qoladi
    assert _enable(tenant_a, cam, False).status_code == 200
    with organization_context(tenant_a.organization.id):
        fresh = Camera.objects.get(pk=cam.pk)
        assert not fresh.preview and fresh.preview_at is None
    assert tenant_a.client().get(f"/api/v1/cameras/{cam.id}/preview").status_code == 404


def test_preview_is_tenant_scoped_and_needs_auth(tenant_a, tenant_b):
    cam, token = _issue(tenant_a)
    _enable(tenant_a, cam)
    _frame(token)
    assert tenant_b.client().get(f"/api/v1/cameras/{cam.id}/preview").status_code == 404
    assert APIClient().get(f"/api/v1/cameras/{cam.id}/preview").status_code in {401, 403}
    assert (
        tenant_b.client()
        .patch(f"/api/v1/cameras/{cam.id}", {"preview_enabled": False}, format="json")
        .status_code
        == 404
    )


def test_bad_preview_frame_is_rejected(tenant_a):
    cam, token = _issue(tenant_a)
    _enable(tenant_a, cam)
    assert _frame(token, b"not-an-image").status_code == 422


# --- webhook ---------------------------------------------------------------


def test_webhook_bearer_json_creates_event(tenant_a):
    cam, token = _issue(tenant_a, "webhook")
    resp = APIClient().post(
        HOOK,
        {"eventType": "motion detected", "severity": "bogus"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert resp.status_code == 200, resp.content
    with organization_context(tenant_a.organization.id):
        event = CameraEvent.objects.get()
    assert (
        event.note == "motion detected" and event.severity == "warning" and event.kind == "safety"
    )


def test_webhook_url_token_works_only_for_webhook_cameras(tenant_a):
    _, edge_token = _issue(tenant_a, "edge")
    assert APIClient().post(f"{HOOK}/{edge_token}", {}, format="json").status_code == 401
    _, hook_token = _issue(tenant_a, "webhook")
    assert APIClient().post(f"{HOOK}/{hook_token}", {"note": "x"}, format="json").status_code == 200


def test_url_token_cannot_write_preview_frames(tenant_a):
    cam, token = _issue(tenant_a, "webhook")
    _enable(tenant_a, cam)
    resp = APIClient().post(
        f"{HOOK}/{token}", jpeg(), content_type="image/jpeg", HTTP_CONTENT_TYPE="image/jpeg"
    )
    assert resp.status_code == 200
    with organization_context(tenant_a.organization.id):
        fresh = Camera.objects.get(pk=cam.pk)
        assert not fresh.preview  # rasm hodisaga ketdi, kuzatuv kadriga emas
        assert CameraEvent.objects.count() == 1


def test_webhook_xml_body_extracts_event_type_without_parsing_xml(tenant_a):
    _, token = _issue(tenant_a, "webhook")
    xml = (
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "boom">]>'
        b"<EventNotificationAlert><eventType>linedetection</eventType></EventNotificationAlert>"
    )
    resp = APIClient().post(
        HOOK, xml, content_type="application/xml", HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    assert resp.status_code == 200, resp.content
    with organization_context(tenant_a.organization.id):
        assert CameraEvent.objects.get().note == "linedetection"


def test_webhook_rejects_bad_tokens_and_control_chars(tenant_a):
    _, token = _issue(tenant_a, "webhook")
    assert APIClient().post(f"{HOOK}/garbage", {}, format="json").status_code == 401
    assert APIClient().post(HOOK, {}, format="json").status_code == 401
    APIClient().post(
        HOOK, {"note": "a\x00b\x1b[31mc"}, format="json", HTTP_AUTHORIZATION=f"Bearer {token}"
    )
    with organization_context(tenant_a.organization.id):
        assert "\x00" not in CameraEvent.objects.get().note


def test_token_issue_rejects_unknown_connection(tenant_a):
    cam = _camera(tenant_a)
    resp = tenant_a.client().post(
        f"/api/v1/cameras/{cam.id}/token", {"connection": "telnet"}, format="json"
    )
    assert resp.status_code in {400, 422}
