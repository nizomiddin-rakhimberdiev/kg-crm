"""
Refresh cookie'ning YOʻLI joylashtirishga moslashsin.

Brauzer cookie'ni faqat uning `path` i ostidagi soʻrovlarga yuboradi.
Yoʻl `/api/v1/auth` deb qotirib yozilgan edi — SaaS'da API aynan shu
yerda turadi, shuning uchun u yerda hammasi ishlagan. Standalone
nusxada esa ilova pastki yoʻlda (`/private`), API `/private/api/v1/...`
boʻladi va brauzer refresh cookie'ni **umuman yubormaydi**.

Natijasi ekranda: sahifani qayta yuklash — tizimdan chiqish. Access
token faqat xotirada yashaydi (04 §5), uni tiklaydigan yagona narsa
esa oʻsha cookie. Buni brauzerdagi E2E topdi: `page.reload()` dan
keyin foydalanuvchi kirish sahifasida edi.

ADR-13 standalone'ni **sotiladigan** ikkinchi yetkazish modeli deb
belgilaydi, yaʼni bu demo stendning gʻashligi emas.
"""

from __future__ import annotations

import importlib

import pytest
from django.test import override_settings

pytestmark = pytest.mark.django_db


def _cookie_path() -> str:
    from apps.accounts import cookies

    importlib.reload(cookies)
    return cookies.COOKIE_PATH


@override_settings(PUBLIC_BASE_URL="https://radix-crm.uz")
def test_saas_keeps_the_root_path():
    assert _cookie_path() == "/api/v1/auth"


@override_settings(PUBLIC_BASE_URL="https://radix-crm.uz/private")
def test_a_sub_path_deployment_gets_its_prefix():
    assert _cookie_path() == "/private/api/v1/auth"


@override_settings(PUBLIC_BASE_URL="https://bogcha.uz/app/")
def test_a_trailing_slash_does_not_double_up():
    assert _cookie_path() == "/app/api/v1/auth"


@override_settings(PUBLIC_BASE_URL="")
def test_an_empty_setting_falls_back_to_the_root():
    """Sozlama boʻsh boʻlsa ham ishlaydigan yoʻl qolsin."""
    assert _cookie_path() == "/api/v1/auth"
