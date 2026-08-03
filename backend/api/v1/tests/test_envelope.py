"""Konvert va xato formati testlari (docs/04 §2)."""

from __future__ import annotations

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestSuccessEnvelope:
    def test_api_root_uses_envelope(self, api_client):  # type: ignore[no-untyped-def]
        response = api_client.get(reverse("v1:root"))
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "data": {"version": "v1", "modules": []},
            "meta": None,
            "message": None,
        }

    def test_envelope_keys_are_always_present(self, api_client):  # type: ignore[no-untyped-def]
        """Frontend bitta handler yozadi — kalitlar hech qachon yo'qolmasin."""
        body = api_client.get(reverse("v1:root")).json()
        assert set(body) == {"success", "data", "meta", "message"}


class TestHealthCheck:
    def test_health_reports_database(self, api_client):  # type: ignore[no-untyped-def]
        response = api_client.get(reverse("v1:health"))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "ok"
        assert data["checks"]["database"] == "ok"


class TestErrorEnvelope:
    def test_unknown_path_returns_error_envelope(self, api_client):  # type: ignore[no-untyped-def]
        response = api_client.get("/api/v1/mavjud-emas")
        assert response.status_code == 404
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "NOT_FOUND"
        assert "details" in body["error"]

    def test_unauthenticated_request_is_denied_by_default(self, api_client):  # type: ignore[no-untyped-def]
        """
        P5 — deny-by-default.

        `/api/v1/` va `/health` ataylab ochiq; boshqa hamma narsa yopiq.
        Bu test router'ga birinchi haqiqiy endpoint qo'shilganda uni
        himoyalanmagan holda qoldirib bo'lmasligini kafolatlaydi.
        """
        from django.conf import settings
        from rest_framework.permissions import IsAuthenticated

        assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
            "rest_framework.permissions." + IsAuthenticated.__name__
        ]
