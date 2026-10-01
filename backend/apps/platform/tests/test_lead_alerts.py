"""
Yangi ariza → Telegram (PLAN 3.6).

Asosiy savol: ogohlantirish ishlamay qolsa, ARIZA yo'qoladimi?
Javob: yo'q. Tarmoqqa chiqilmaydi — `requests.post` almashtiriladi.
"""

from __future__ import annotations

import uuid
from unittest.mock import Mock, patch

import pytest
from django.urls import reverse

from apps.platform import alerts
from apps.platform.models import Lead

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.fixture
def configured(settings):
    settings.TELEGRAM_BOT_TOKEN = "123:ABC"  # noqa: S105 — test qiymati
    settings.TELEGRAM_LEADS_CHAT_ID = "-1001"
    return settings


def _payload() -> dict:
    return {
        "name": "Nodira Karimova",
        "phone": "+998901234567",
        "kindergarten_name": "Oriental Kinderland",
        "children_count": 60,
        "city": "Toshkent",
        "message": "Narxni bilmoqchiman",
        "language": "uz",
        "submission_id": str(uuid.uuid4()),
        "privacy_policy_version": "1.0",
        "consent": True,
    }


class TestAlert:
    def test_a_new_lead_reaches_sales_immediately(
        self, configured, client, django_capture_on_commit_callbacks
    ):
        response = Mock(status_code=200, text="ok")
        # Ogohlantirish `on_commit` da: ariza BAZAGA tushgandan keyin
        # yuboriladi, aks holda rollback bo'lgan arizaga qo'ng'iroq
        # qilishardi. Test shu sababdan callback'larni o'zi ishga
        # tushiradi.
        with (
            patch("requests.post", return_value=response) as post,
            django_capture_on_commit_callbacks(execute=True),
        ):
            created = client.post(
                reverse("v1:public-lead-create"), _payload(), content_type="application/json"
            )

        assert created.status_code in (200, 201)
        assert post.called
        text = post.call_args.kwargs["json"]["text"]
        # Sotuvchi konsolni ochmasdan qo'ng'iroq qila olishi kerak.
        assert "+998901234567" in text
        assert "Oriental Kinderland" in text

    def test_a_telegram_failure_never_loses_the_lead(
        self, configured, client, django_capture_on_commit_callbacks
    ):
        import requests

        with (
            patch("requests.post", side_effect=requests.ConnectionError("tarmoq yo'q")),
            django_capture_on_commit_callbacks(execute=True),
        ):
            created = client.post(
                reverse("v1:public-lead-create"), _payload(), content_type="application/json"
            )

        assert created.status_code in (200, 201)
        assert Lead.objects.count() == 1

    def test_without_configuration_nothing_is_sent_and_nothing_breaks(self, settings, client):
        settings.TELEGRAM_BOT_TOKEN = ""
        settings.TELEGRAM_LEADS_CHAT_ID = ""
        with patch("requests.post") as post:
            created = client.post(
                reverse("v1:public-lead-create"), _payload(), content_type="application/json"
            )
        assert created.status_code in (200, 201)
        assert not post.called
        assert Lead.objects.count() == 1

    def test_a_name_with_angle_brackets_does_not_break_the_message(self, configured):
        lead = Mock(
            name_="x",
            phone="+998901234567",
            kindergarten_name="<b>Bog'cha</b>",
            children_count=10,
            city="Toshkent",
            message="",
            language="uz",
            source="website",
        )
        lead.name = "Ali <script>"
        with patch("requests.post", return_value=Mock(status_code=200, text="ok")) as post:
            alerts.notify_new_lead(lead)
        text = post.call_args.kwargs["json"]["text"]
        assert "<script>" not in text
        assert "&lt;script&gt;" in text


class TestNextCall:
    """PLAN 3.6: "ertaga qo'ng'iroq qilaman" — qachon ekanini yozib qo'yish."""

    @pytest.fixture
    def console(self):
        from rest_framework.test import APIClient

        from apps.platform.authentication import issue_platform_token
        from apps.platform.tests.test_leads import platform_admin

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_platform_token(platform_admin())}")
        return client

    @pytest.fixture
    def lead(self) -> Lead:
        from apps.platform.services_leads import create_lead

        created, _ = create_lead(data=_payload())
        return created

    def test_the_sales_person_can_set_and_clear_the_next_call(self, lead, console):
        url = f"/api/v1/platform/leads/{lead.id}/status"
        response = console.post(
            url,
            {"status": "contacted", "note": "Narx yubordim", "next_call_at": "2026-10-05"},
            format="json",
        )
        assert response.status_code == 200
        lead.refresh_from_db()
        assert lead.next_call_at.isoformat() == "2026-10-05"

        # Maydon yuborilmasa — reja o'z joyida qoladi.
        console.post(url, {"status": "qualified"}, format="json")
        lead.refresh_from_db()
        assert lead.next_call_at.isoformat() == "2026-10-05"

        # `null` — rejani bekor qiladi.
        console.post(url, {"status": "qualified", "next_call_at": None}, format="json")
        lead.refresh_from_db()
        assert lead.next_call_at is None
