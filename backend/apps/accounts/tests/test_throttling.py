"""
Login throttling testi (docs/02 §20.2).

Throttling umumiy test sozlamalarida o'chirilgan, chunki u kesh orqali
testlar orasida "oqib" ketadi va aloqasiz testlarni yiqitadi. Shuning uchun
u aynan shu yerda, ataylab qayta yoqib sinaladi — brute-force himoyasi
jimgina yo'qolib qolmasin.
"""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _clear_throttle_cache():  # type: ignore[no-untyped-def]
    cache.clear()
    yield
    cache.clear()


def test_repeated_failed_logins_are_throttled(api_client, tenant_a, monkeypatch):
    """Ketma-ket muvaffaqiyatsiz urinishlar 429 bilan to'siladi."""
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

    assert statuses[0] == 401, "Birinchi urinish oddiy 401 bo'lishi kerak"
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
