"""Kuzatuvchanlik testlari (P1-008)."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.core.logging import HEADER

pytestmark = pytest.mark.django_db


class TestRequestId:
    """
    Har bir so'rov iz qoldiradi.

    Nosozlikni tekshirishda bu farqni ko'rsatadi: mijoz ekrandagi kodni
    aytadi, siz log'dan bir urinishda topasiz.
    """

    def test_every_response_carries_a_request_id(self, api_client):
        response = api_client.get(reverse("v1:health"))
        assert response[HEADER]
        assert len(response[HEADER]) <= 64

    def test_the_client_id_is_kept(self, api_client):
        """
        Mijoz bergan ID saqlanadi — frontend xatosi bilan backend logi
        bitta ip bilan bog'lansin.
        """
        response = api_client.get(reverse("v1:health"), **{"HTTP_X_REQUEST_ID": "abc-123"})
        assert response[HEADER] == "abc-123"

    def test_an_oversized_id_is_trimmed(self, api_client):
        """Mijoz bergan qiymat ishonchsiz manba — logʻni toʻldirmasin."""
        response = api_client.get(reverse("v1:health"), **{"HTTP_X_REQUEST_ID": "x" * 500})
        assert len(response[HEADER]) == 64

    def test_two_requests_get_different_ids(self, api_client):
        first = api_client.get(reverse("v1:health"))[HEADER]
        second = api_client.get(reverse("v1:health"))[HEADER]
        assert first != second


class TestHealthChecksTheWorker:
    """
    O'lik ishchi jimgina zarar qiladi: hisob-fakturalar chiqmaydi,
    eslatmalar ketmaydi, eksport abadiy "tayyorlanmoqda" bo'lib qoladi —
    va hech qanday xato ko'rinmaydi.
    """

    def test_the_worker_is_reported(self, api_client):
        response = api_client.get(reverse("v1:health"))
        assert "worker" in response.json()["data"]["checks"]

    def test_a_missing_worker_does_not_take_the_service_down(self, api_client, monkeypatch):
        """
        Ishchi javob bermasa `degraded`, LEKIN javob `200`.

        Farq muhim: ishchisiz ham tizim o'qiladi va to'lov qabul qiladi,
        ya'ni load balancer serverni navbatdan chiqarib tashlamasligi
        kerak. `503` faqat haqiqiy nosozlikda — baza yoki kesh yo'q
        bo'lganda.

        Ishchi holati SOXTALASHTIRILADI: aks holda test mashinada
        tasodifan ishlab turgan Celery'ga bog'liq bo'lardi va
        noutbukda bir xil, CI'da boshqacha natija berardi.
        """
        from api.v1 import views

        monkeypatch.setattr(
            views.HealthCheckView, "_check_worker", staticmethod(lambda: "degraded")
        )

        response = api_client.get(reverse("v1:health"))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["checks"]["worker"] == "degraded"
        assert data["status"] == "degraded"
        assert data["checks"]["database"] == "ok"

    def test_a_dead_database_does_take_the_service_down(self, api_client, monkeypatch):
        """Baza yoʻq boʻlsa — `503`. Bu haqiqiy nosozlik."""
        from api.v1 import views

        monkeypatch.setattr(views.HealthCheckView, "_check_database", staticmethod(lambda: "error"))

        response = api_client.get(reverse("v1:health"))
        assert response.status_code == 503


class TestAdminIsNotExposed:
    """
    Django admin productionda marshrutlanmaydi (P2-006).

    U ADR-10 ga qarshi ikkinchi imtiyozli yo'l bo'lardi: sessiya bilan
    ishlaydi, 2FA talab qilmaydi, RBAC matritsasini chetlab o'tadi.
    """

    def test_admin_is_absent_when_debug_is_off(self, api_client, settings):
        # Test sozlamalarida `DEBUG = False` — ya'ni production kabi.
        assert settings.DEBUG is False
        assert api_client.get("/admin/").status_code == 404
