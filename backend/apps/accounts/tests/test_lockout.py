"""
Kirish urinishlari chegarasi (PLAN 5.3).

Nega tezlik chegarasining o'zi yetarli emas: `LoginThrottle` IP
bo'yicha 20/min beradi va u JAMOAVIY — bog'chada hamma bitta Wi-Fi
ortida. 20/min esa soatda 1200 urinish, ya'ni bitta hisobga qarshi
parol terish uchun ko'p.
"""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.accounts import lockout

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.fixture(autouse=True)
def _clean_cache():
    cache.clear()
    yield
    cache.clear()


def _login(client, email: str, password: str = "xato-parol", **extra):  # noqa: S107
    return client.post(
        reverse("v1:auth-login"), {"email": email, "password": password}, format="json", **extra
    )


class TestCounter:
    def test_failures_are_counted_per_email_and_per_ip(self):
        lockout.record_failure(email="a@alfa.uz", ip="10.0.0.1")
        lockout.record_failure(email="b@alfa.uz", ip="10.0.0.1")
        state = lockout.state(email="a@alfa.uz", ip="10.0.0.1")
        assert state["login:fail:email:a@alfa.uz"] == 1
        # IP hisoblagichi IKKI urinishni ko'radi: bitta manbadan ko'p
        # hisobni sinab ko'rish ham to'xtatilishi kerak.
        assert state["login:fail:ip:10.0.0.1"] == 2

    def test_the_email_is_case_insensitive(self):
        lockout.record_failure(email="A@Alfa.uz")
        assert lockout.is_locked(email="a@alfa.uz") is False
        for _ in range(lockout.MAX_ATTEMPTS - 1):
            lockout.record_failure(email="a@ALFA.uz")
        assert lockout.is_locked(email="A@alfa.UZ") is True

    def test_success_clears_the_counter(self):
        for _ in range(lockout.MAX_ATTEMPTS - 1):
            lockout.record_failure(email="a@alfa.uz", ip="10.0.0.1")
        lockout.reset(email="a@alfa.uz", ip="10.0.0.1")
        assert lockout.state(email="a@alfa.uz", ip="10.0.0.1") == {
            "login:fail:email:a@alfa.uz": 0,
            "login:fail:ip:10.0.0.1": 0,
        }


class TestLoginEndpoint:
    def test_too_many_attempts_are_blocked_with_a_clear_answer(self, tenant_a, api_client):
        for _ in range(lockout.MAX_ATTEMPTS):
            response = _login(api_client, tenant_a.owner.email)
            assert response.status_code == 401

        blocked = _login(api_client, tenant_a.owner.email)
        assert blocked.status_code == 429
        body = blocked.json()["error"]
        assert body["code"] == "TOO_MANY_ATTEMPTS"
        # Aniq daqiqa aytiladi: "keyinroq urinib ko'ring" degan javob
        # odamni har 10 soniyada qayta bosishga majbur qiladi.
        assert "daqiqa" in body["message"]
        assert blocked.headers["Retry-After"]

    def test_a_blocked_account_is_refused_even_with_the_right_password(self, tenant_a, api_client):
        """Blok paroldan QAT'I NAZAR ishlaydi — aks holda u to'siq emas."""
        for _ in range(lockout.MAX_ATTEMPTS):
            _login(api_client, tenant_a.owner.email)
        response = _login(api_client, tenant_a.owner.email, password=tenant_a.password)
        assert response.status_code == 429

    def test_a_correct_password_resets_the_counter(self, tenant_a, api_client):
        for _ in range(lockout.MAX_ATTEMPTS - 1):
            _login(api_client, tenant_a.owner.email)
        ok = _login(api_client, tenant_a.owner.email, password=tenant_a.password)
        assert ok.status_code == 200
        # Parolni unutib to'qqiz marta xato tergan xodim to'g'ri
        # kirgach jazolanmasligi kerak.
        assert lockout.is_locked(email=tenant_a.owner.email) is False

    def test_another_account_from_the_same_office_still_gets_in(self, tenant_a, api_client):
        """
        IP chegarasi email chegarasidan KENGROQ.

        Bog'chada hamma bitta Wi-Fi ortida: bitta xodim parolini
        unutgani butun jamoani tizimdan chiqarib qo'ymasligi kerak.
        """
        for _ in range(lockout.MAX_ATTEMPTS - 1):
            _login(api_client, "boshqa@alfa.uz")
        response = _login(api_client, tenant_a.owner.email, password=tenant_a.password)
        assert response.status_code == 200

    def test_the_block_is_written_to_the_audit_log(self, tenant_a, api_client):
        from apps.audit.models import AuditLog
        from apps.core.tenancy import platform_context

        for _ in range(lockout.MAX_ATTEMPTS + 1):
            _login(api_client, tenant_a.owner.email)

        # Muvaffaqiyatsiz kirish yozuvida TASHKILOT yo'q (kim
        # urinayotganini hali bilmaymiz), shuning uchun u RLS'da
        # platforma tekisligida o'qiladi (docs/03 §6.3) — aynan
        # shunday loyihalangan: "kimdir kirishga urindi" yozuvini
        # mijoz ko'rmaydi, lekin u yo'qolmaydi ham.
        with platform_context():
            blocked = AuditLog.objects.filter(action="login_blocked")
            assert blocked.exists(), "blok hujumning belgisi — jurnalda qolishi kerak"
            assert blocked.first().actor_email == tenant_a.owner.email

    def test_the_failure_count_is_in_the_audit_trail(self, tenant_a, api_client):
        from apps.audit.models import AuditLog
        from apps.core.tenancy import platform_context

        _login(api_client, tenant_a.owner.email)
        with platform_context():
            row = AuditLog.objects.filter(action="login_failed").first()
        assert row is not None
        assert row.changes.get("attempts") == 1
