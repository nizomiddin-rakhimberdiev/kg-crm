"""Kamera ulanishi: token modeli, ingest endpoint va edge-worker sof funksiyalari."""

from __future__ import annotations

from datetime import datetime, time

import numpy as np
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.core.tenancy import organization_context
from apps.memories.models import Camera, CameraEvent, ChatKind
from apps.memories.tests.factories import jpeg, link_chat
from edge import camera_worker as worker

URL = "/api/v1/camera-ingest"


def _camera(tenant) -> Camera:
    with organization_context(tenant.organization.id):
        return Camera.objects.create(
            organization=tenant.organization, branch=tenant.branch, name="Kirish"
        )


def _token(tenant) -> tuple[Camera, str]:
    client = tenant.client()
    cam = _camera(tenant)
    resp = client.post(f"/api/v1/cameras/{cam.id}/token")
    assert resp.status_code == 200, resp.content
    return cam, resp.json()["data"]["token"]


def _post(token, data=None, **kw):
    return APIClient().post(
        URL, data or {}, format="multipart", HTTP_AUTHORIZATION=f"Bearer {token}", **kw
    )


def test_token_is_shown_once_and_stored_hashed(tenant_a):
    cam, token = _token(tenant_a)
    with organization_context(tenant_a.organization.id):
        stored = Camera.objects.get(pk=cam.pk).ingest_token_hash
    assert token.split(".")[2] not in stored and len(stored) == 64
    listed = tenant_a.client().get("/api/v1/cameras").json()["data"]
    assert token.split(".")[2] not in str(listed) and listed[0]["has_token"] is True


def test_heartbeat_marks_online_without_event(tenant_a):
    cam, token = _token(tenant_a)
    assert _post(token).status_code == 200
    with organization_context(tenant_a.organization.id):
        assert CameraEvent.objects.count() == 0
    row = tenant_a.client().get("/api/v1/cameras").json()["data"][0]
    assert row["is_online"] is True and row["last_seen_at"]


def test_event_with_snapshot_alerts_staff_and_respects_cooldown(
    tenant_a, _telegram_recorder, django_capture_on_commit_callbacks
):
    link_chat(tenant_a, ChatKind.STAFF, user=tenant_a.owner, language="en")
    _, token = _token(tenant_a)
    payload = {
        "kind": "safety",
        "note": "motion",
        "snapshot": SimpleUploadedFile("s.jpg", jpeg(), "image/jpeg"),
    }
    with django_capture_on_commit_callbacks(execute=True):
        first = _post(token, payload).json()["data"]
    assert first["accepted"] is True and first["event_id"]
    assert len(_telegram_recorder.photos) == 1
    r2 = _post(
        token, {"kind": "safety", "snapshot": SimpleUploadedFile("s.jpg", jpeg(), "image/jpeg")}
    )
    again = r2.json()["data"]
    assert again["accepted"] is False and again["reason"] == "cooldown"
    with organization_context(tenant_a.organization.id):
        assert CameraEvent.objects.count() == 1


@pytest.mark.parametrize("mutate", ["", "x", "a.b", "a.b.c", None])
def test_garbage_tokens_are_401(tenant_a, mutate):
    _token(tenant_a)
    resp = APIClient().post(
        URL, {}, format="multipart", HTTP_AUTHORIZATION=f"Bearer {mutate or ''}"
    )
    assert resp.status_code == 401


def test_wrong_secret_revoked_and_inactive_are_401(tenant_a):
    cam, token = _token(tenant_a)
    org, cid, secret = token.split(".")
    assert _post(f"{org}.{cid}.{secret[:-1]}X").status_code == 401
    assert _post(token).status_code == 200
    with organization_context(tenant_a.organization.id):
        Camera.objects.filter(pk=cam.pk).update(is_active=False)
    assert _post(token).status_code == 401
    with organization_context(tenant_a.organization.id):
        Camera.objects.filter(pk=cam.pk).update(is_active=True)
    assert tenant_a.client().post(f"/api/v1/cameras/{cam.id}/revoke-token").status_code == 200
    assert _post(token).status_code == 401


def test_new_token_invalidates_old_one(tenant_a):
    cam, old = _token(tenant_a)
    new = tenant_a.client().post(f"/api/v1/cameras/{cam.id}/token").json()["data"]["token"]
    assert _post(old).status_code == 401 and _post(new).status_code == 200


def test_cross_tenant_token_tampering_is_401(tenant_a, tenant_b):
    cam_a, token_a = _token(tenant_a)
    _, token_b = _token(tenant_b)
    org_b = token_b.split(".")[0]
    _, cam_hex, secret = token_a.split(".")
    assert _post(f"{org_b}.{cam_hex}.{secret}").status_code == 401


def test_bad_snapshot_is_400_and_kind_is_validated(tenant_a):
    _, token = _token(tenant_a)
    bad = _post(
        token,
        {"kind": "safety", "snapshot": SimpleUploadedFile("s.jpg", b"not-an-image", "image/jpeg")},
    )
    assert bad.status_code == 422
    assert _post(token, {"kind": "nonsense"}).status_code == 400
    with organization_context(tenant_a.organization.id):
        assert CameraEvent.objects.count() == 0


def test_token_actions_need_permission_and_are_tenant_scoped(tenant_a, tenant_b):
    cam = _camera(tenant_a)
    assert tenant_b.client().post(f"/api/v1/cameras/{cam.id}/token").status_code == 404
    assert tenant_b.client().post(f"/api/v1/cameras/{cam.id}/revoke-token").status_code == 404


# --- edge-worker sof funksiyalari -----------------------------------------


def test_quiet_hours_cross_midnight():
    window = worker.parse_quiet_hours("20:00-07:00")
    assert worker.in_quiet_hours(time(23, 0), window)
    assert worker.in_quiet_hours(time(3, 0), window)
    assert not worker.in_quiet_hours(time(12, 0), window)
    assert not worker.in_quiet_hours(time(12, 0), None)
    day = worker.parse_quiet_hours("09:00-17:00")
    assert worker.in_quiet_hours(time(10, 0), day) and not worker.in_quiet_hours(time(18, 0), day)


def test_parse_quiet_hours_rejects_garbage():
    assert worker.parse_quiet_hours("") is None
    with pytest.raises(ValueError):
        worker.parse_quiet_hours("late")


def test_motion_ratio():
    a = np.zeros((10, 10), dtype=np.uint8)
    b = a.copy()
    b[:5] = 255
    assert worker.motion_ratio(a, a) == 0.0
    assert worker.motion_ratio(a, b) == pytest.approx(0.5)
    assert worker.motion_ratio(a, np.zeros((5, 5), dtype=np.uint8)) == 0.0


def test_validate_server_url():
    assert worker.validate_server_url("https://radix-crm.uz/") == "https://radix-crm.uz"
    assert worker.validate_server_url("http://localhost:8000") == "http://localhost:8000"
    for bad in ("http://radix-crm.uz", "ftp://x", "radix-crm.uz", ""):
        with pytest.raises(ValueError):
            worker.validate_server_url(bad)


def test_after_hours_motion_detector_fires_only_in_window():
    det = worker.AfterHoursMotion(quiet_hours=worker.parse_quiet_hours("20:00-07:00"))
    dark = np.zeros((120, 160, 3), dtype=np.uint8)
    bright = np.full((120, 160, 3), 255, dtype=np.uint8)
    night, noon = datetime(2026, 1, 1, 23, 0), datetime(2026, 1, 1, 12, 0)
    assert det.update(dark, night) is None  # birinchi kadr
    hit = det.update(bright, night)
    assert hit is not None and hit.kind == "safety"
    assert det.update(dark, noon) is None


# --- NVR / ONVIF / ko'p kamerali sozlama ----------------------------------


def test_nvr_template_builds_channel_urls_without_secrets():
    cfg = worker.nvr_template("hikvision", "192.168.1.10", "ad min", 2, "https://x.uz/api/v1")
    assert [c["name"] for c in cfg["cameras"]] == ["hikvision-ch1", "hikvision-ch2"]
    assert (
        cfg["cameras"][0]["rtsp"] == "rtsp://ad%20min:PAROL@192.168.1.10:554/Streaming/Channels/101"
    )
    assert cfg["cameras"][0]["token"].startswith("PASTE")
    dahua = worker.nvr_template("dahua", "nvr.local", "admin", 1, "https://x.uz/api/v1")
    assert "channel=1&subtype=0" in dahua["cameras"][0]["rtsp"]
    for bad in (("bogus", "h", 1), ("dahua", "a b;rm", 1), ("dahua", "h", 0), ("dahua", "h", 999)):
        with pytest.raises(ValueError):
            worker.nvr_template(bad[0], bad[1], "u", bad[2], "https://x.uz/api/v1")


def test_load_config_validates_and_rejects_placeholders(tmp_path):
    import json as _json
    import os

    path = tmp_path / "cams.json"

    def write(data):
        path.write_text(_json.dumps(data))
        os.chmod(path, 0o600)

    good = {
        "server": "https://radix-crm.uz/api/v1",
        "cameras": [{"token": "a.b.c", "rtsp": "rtsp://u:p@10.0.0.2:554/s", "name": "Zal"}],
    }
    write(good)
    server, cams = worker.load_config(str(path))
    assert server == "https://radix-crm.uz/api/v1" and cams[0].name == "Zal"
    assert "a.b.c" not in repr(cams[0])  # token reprga tushmaydi
    write({**good, "cameras": [{"token": "PASTE_TOKEN_1", "rtsp": "rtsp://h/s"}]})
    with pytest.raises(ValueError):
        worker.load_config(str(path))
    write({**good, "cameras": [{"token": "t", "rtsp": "http://h/s"}]})
    with pytest.raises(ValueError):
        worker.load_config(str(path))
    write({"server": "http://evil.example", "cameras": good["cameras"]})
    with pytest.raises(ValueError):
        worker.load_config(str(path))
    write(good)
    os.chmod(path, 0o644)
    if os.name == "posix":
        with pytest.raises(ValueError):
            worker.load_config(str(path))


_PROFILES = b"""<?xml version="1.0"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"><s:Body>
<trt:GetProfilesResponse xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
 xmlns:tt="http://www.onvif.org/ver10/schema">
<trt:Profiles token="prof1"><tt:Name>Main</tt:Name></trt:Profiles>
<trt:Profiles token="prof2"><tt:Name>Sub</tt:Name></trt:Profiles>
</trt:GetProfilesResponse></s:Body></s:Envelope>"""


def _uri(uri: str) -> bytes:
    return (
        '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"><s:Body>'
        '<trt:GetStreamUriResponse xmlns:trt="http://www.onvif.org/ver10/media/wsdl" '
        'xmlns:tt="http://www.onvif.org/ver10/schema"><trt:MediaUri>'
        f"<tt:Uri>{uri}</tt:Uri></trt:MediaUri></trt:GetStreamUriResponse></s:Body></s:Envelope>"
    ).encode()


def test_onvif_discovers_rtsp_uris_and_drops_other_schemes():
    sent = []

    def fake(url, xml):
        sent.append(xml)
        if "GetProfiles" in xml:
            return _PROFILES
        return _uri("rtsp://10.0.0.5:554/main" if "prof1" in xml else "http://evil/x")

    found = worker.onvif_stream_uris("10.0.0.5", "admin", "s3cret", transport=fake)
    assert found == [("Main", "rtsp://10.0.0.5:554/main")]
    assert all("s3cret" not in xml for xml in sent)  # parol ochiq ketmaydi (digest)
    assert "PasswordDigest" in sent[0]


def test_onvif_rejects_bad_host_and_hostile_xml():
    with pytest.raises(ValueError):
        worker.onvif_stream_uris("10.0.0.5;rm -rf", "u", "p", transport=lambda *_: b"")
    bomb = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "x">]><r>&a;</r>'
    with pytest.raises(Exception):  # noqa: B017 — defusedxml entity'ni rad etadi
        worker.onvif_stream_uris("10.0.0.5", "u", "p", transport=lambda *_: bomb)
