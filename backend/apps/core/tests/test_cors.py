"""
CORS sarlavhalari — to'lovning ikki marta yozilishidan himoyasi shunga bog'liq.

Productionda SPA va API bitta origin'da, ya'ni preflight bo'lmaydi va bu
kamchilik ko'rinmaydi. Lokal ishlab chiqishda va API alohida domenga
chiqarilganda esa brauzer `Idempotency-Key` li so'rovni butunlay bloklaydi:
to'lov umuman yozilmaydi. Shuning uchun sarlavha ro'yxati testda qotirilgan.
"""

from __future__ import annotations

import pytest
from django.conf import settings
from django.test import Client

pytestmark = pytest.mark.django_db

ORIGIN = settings.CORS_ALLOWED_ORIGINS[0]


def test_idempotency_key_is_allowed_in_settings():
    assert "idempotency-key" in [h.lower() for h in settings.CORS_ALLOW_HEADERS]


def test_preflight_for_payment_allows_idempotency_key():
    response = Client().options(
        "/api/v1/payments",
        HTTP_ORIGIN=ORIGIN,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,idempotency-key",
    )
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert response.status_code == 200, response.status_code
    assert "idempotency-key" in allowed, allowed


def test_language_header_needs_no_entry():
    """
    `Accept-Language` (ADR-16) ro'yxatda YO'Q va bo'lishi ham shart emas:
    u CORS'ning "xavfsiz" sarlavhalaridan, ya'ni brauzer uni preflight'da
    umuman so'ramaydi. Brauzerda tekshirilgan: cross-origin so'rov ruscha
    xabar qaytardi. Test shuni qayd etadi — kimdir uni "yetishmayapti" deb
    qo'shmasin yoki safelist'ga tayangan joyni buzmasin.
    """
    assert "accept-language" not in [h.lower() for h in settings.CORS_ALLOW_HEADERS]
