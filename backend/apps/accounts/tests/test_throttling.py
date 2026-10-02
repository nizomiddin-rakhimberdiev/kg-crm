"""
Throttling testlari (docs/02 §20.2) — login brute-force VA jamoaviy ish.

Throttling umumiy test sozlamalarida o'chirilgan, chunki u kesh orqali
testlar orasida "oqib" ketadi va aloqasiz testlarni yiqitadi. Shuning uchun
u aynan shu yerda, ataylab qayta yoqib sinaladi — brute-force himoyasi
jimgina yo'qolib qolmasin.

Ikkinchi qism — CHEGARA QIYMATLARI: bog'chada hamma bitta Wi-Fi ortida,
ya'ni IP bo'yicha chegara amalda butun jamoa uchun umumiy.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from config.settings.base import REST_FRAMEWORK as BASE_REST_FRAMEWORK

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_throttle_cache():  # type: ignore[no-untyped-def]
    cache.clear()
    yield
    cache.clear()


def test_repeated_failed_logins_are_throttled(api_client, tenant_a, monkeypatch):
    """Ketma-ket muvaffaqiyatsiz urinishlar 429 bilan toʻsiladi."""
    from rest_framework.throttling import SimpleRateThrottle

    # DRF `THROTTLE_RATES` ni **klass atributi** sifatida import paytida
    # o'qiydi, shuning uchun `override_settings` unga ta'sir qilmaydi —
    # klassning o'zini almashtiramiz.
    monkeypatch.setattr(
        SimpleRateThrottle, "THROTTLE_RATES", {"anon": "1000/hour", "login": "3/min"}
    )

    url = reverse("v1:auth-login")
    payload = {"email": tenant_a.owner.email, "password": "noto-g-ri"}
    statuses = [api_client.post(url, payload, format="json").status_code for _ in range(5)]

    assert statuses[0] == 401, "Birinchi urinish oddiy 401 boʻlishi kerak"
    assert 429 in statuses, f"Login throttle ishlamadi: {statuses}"
    assert statuses[-1] == 429


def test_successful_login_is_also_counted(api_client, tenant_a, monkeypatch):
    """
    Throttle muvaffaqiyatli loginlarni ham hisoblaydi.

    Aks holda hujumchi har urinishdan keyin ma'lum bir to'g'ri hisob bilan
    kirib, hisoblagichni nolga tushirib turishi mumkin edi.
    """
    from rest_framework.throttling import SimpleRateThrottle

    monkeypatch.setattr(
        SimpleRateThrottle, "THROTTLE_RATES", {"anon": "1000/hour", "login": "2/min"}
    )

    url = reverse("v1:auth-login")
    good = {"email": tenant_a.owner.email, "password": "Juda-Kuchli-Parol-2026"}
    statuses = [api_client.post(url, good, format="json").status_code for _ in range(4)]

    assert statuses[0] == 200
    assert statuses[-1] == 429


# --- Chegara qiymatlari: umumiy IP ortidagi jamoa ---
#
# Chegaralar testlarda o'chirilgan (yuqoridagi izoh), shuning uchun qiymatlar
# BAZAVIY sozlamadan o'qiladi.

BASE_RATES = cast("dict[str, str]", BASE_REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])


def test_refresh_has_its_own_scope():
    """
    Access token faqat XOTIRADA yashaydi, ya'ni har sahifa yuklanishi va har
    15 daqiqada bitta `POST /auth/refresh` bo'ladi. So'rov anonim (token
    tanada), shuning uchun alohida scope bo'lmasa u `anon` = 120/soat ga
    tushardi — bitta IP ortidagi BUTUN bog'cha uchun. Natijada xodimlar ish
    kuni o'rtasida tizimdan chiqib ketardi.
    """
    assert "refresh" in BASE_RATES, "yangilash umumiy `anon` chegarasiga tushib qoladi"
    count, _, period = BASE_RATES["refresh"].partition("/")
    assert period == "min"
    assert int(count) >= 30, "umumiy IP ortidagi jamoa uchun juda tor"


def test_login_rate_fits_a_shared_office_ip():
    """Oʻnlab xodim smena boshida birga kirsa, oxirgilari bloklanmasin."""
    count = int(BASE_RATES["login"].split("/")[0])
    assert count >= 20


@override_settings(REST_FRAMEWORK={**BASE_REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {**BASE_RATES}})
def test_many_refreshes_from_one_ip_are_not_blocked(tenant_a: Any, api_client: Any):
    """Bitta IP dan 40 ta yangilash — bitta bogʻchaning yarim kunlik ishi."""
    from apps.accounts.cookies import CSRF_COOKIE, CSRF_HEADER

    api_client.post(
        reverse("v1:auth-login"),
        {"email": tenant_a.owner.email, "password": tenant_a.password},
        format="json",
    )

    # Refresh token COOKIE'da (PLAN 5.1) — klient uni o'zi saqlaydi,
    # biz faqat CSRF sarlavhasini qo'yamiz (frontend ham shunday
    # qiladi).
    for index in range(40):
        headers = {CSRF_HEADER: api_client.cookies[CSRF_COOKIE].value}
        response = api_client.post(reverse("v1:auth-refresh"), {}, format="json", headers=headers)
        assert response.status_code == 200, f"{index}-urinishda {response.status_code}"
