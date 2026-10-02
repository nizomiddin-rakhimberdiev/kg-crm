"""
Bog'chaning sukut tili (ADR-16).

Til har bir odam uchun brauzerda saqlanadi, lekin bog'cha "biz asosan
ruscha ishlaymiz" deyishi mumkin. Shunda o'z tanlovi yo'q xodim tizimni
darhol o'sha tilda ko'radi — har safar qo'lda almashtirmaydi.
"""

from __future__ import annotations

from typing import Any

import pytest

from apps.settings_app.services import DEFAULTS

pytestmark = pytest.mark.django_db


def test_default_is_uzbek():
    assert DEFAULTS["general.default_language"] == "uz"


def test_me_exposes_the_organization_language(tenant_a: Any):
    """Frontend uni boot paytida `/auth/me` dan oladi — alohida soʻrovsiz."""
    body = tenant_a.client().get("/api/v1/auth/me").json()["data"]
    assert body["organization_settings"]["default_language"] == "uz"


def test_changing_the_setting_changes_what_me_returns(tenant_a: Any):
    client = tenant_a.client()
    response = client.put(
        "/api/v1/settings/general.default_language", {"value": "ru"}, format="json"
    )
    assert response.status_code == 200, response.content

    body = client.get("/api/v1/auth/me").json()["data"]
    assert body["organization_settings"]["default_language"] == "ru"
