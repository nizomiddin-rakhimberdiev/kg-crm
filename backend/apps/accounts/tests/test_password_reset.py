"""
Parolni tiklash (PLAN 5.2).

Uchta xususiyat sinaladi va uchalasi ham xavfsizlik qarori:

* javob email mavjudligini **oshkor qilmaydi**;
* havola **bir martalik** va 30 daqiqa yashaydi;
* tiklash **barcha sessiyalarni yopadi** — aks holda u qulfni
  almashtirib, ichkaridagini qoldirish bo'lardi.
"""

from __future__ import annotations

import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from apps.accounts import password_reset
from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.fixture(autouse=True)
def _clean():
    cache.clear()
    mail.outbox.clear()
    yield
    cache.clear()


def _request(client, email: str):
    return client.post(reverse("v1:auth-password-reset"), {"email": email}, format="json")


def _confirm(client, uid: str, token: str, password: str):
    return client.post(
        reverse("v1:auth-password-reset-confirm"),
        {"uid": uid, "token": token, "password": password},
        format="json",
    )


def _link_parts(link: str) -> tuple[str, str]:
    from urllib.parse import parse_qs, urlparse

    query = parse_qs(urlparse(link).query)
    return query["uid"][0], query["token"][0]


class TestDisclosure:
    def test_the_answer_is_the_same_for_a_known_and_an_unknown_email(self, tenant_a, api_client):
        known = _request(api_client, tenant_a.owner.email)
        cache.clear()
        unknown = _request(api_client, "hechkim@example.uz")
        assert known.status_code == unknown.status_code == 200
        # "Bu email ro'yxatda yo'q" degan javob begona odamga mijozlar
        # ro'yxatini tekshirish imkonini berardi.
        assert known.json()["data"] == unknown.json()["data"]

    def test_a_known_email_gets_a_letter_and_an_unknown_one_does_not(self, tenant_a, api_client):
        _request(api_client, tenant_a.owner.email)
        assert len(mail.outbox) == 1
        assert tenant_a.owner.email in mail.outbox[0].to

        mail.outbox.clear()
        cache.clear()
        _request(api_client, "hechkim@example.uz")
        assert mail.outbox == []

    def test_the_letter_carries_a_working_link(self, tenant_a, api_client):
        _request(api_client, tenant_a.owner.email)
        body = mail.outbox[0].body
        assert "/reset-password?" in body
        assert "30 daqiqa" in body

    def test_both_accounts_with_the_same_email_get_their_own_link(
        self, tenant_a, tenant_b, api_client
    ):
        """
        Email tashkilot ICHIDA unikal (ADR-9).

        Bir odam ikki bog'chada ishlashi mumkin; har bir hisob uchun
        alohida havola kerak, aks holda ikkinchisi parolini tiklay
        olmasdi.
        """
        from apps.accounts.models import User

        with organization_context(tenant_b.organization.id):
            User.objects.create_user(
                email=tenant_a.owner.email,
                password="Juda-Kuchli-Parol-2026",  # noqa: S106 — test ma'lumoti
                full_name="Ikkinchi hisob",
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                role=tenant_b.role("org_owner"),
            )

        _request(api_client, tenant_a.owner.email)
        assert len(mail.outbox) == 2


class TestConfirm:
    def test_a_fresh_link_sets_the_new_password(self, tenant_a, api_client):
        link = password_reset.build_link(tenant_a.owner)
        uid, token = _link_parts(link)

        response = _confirm(api_client, uid, token, "Yangi-Kuchli-Parol-2026")
        assert response.status_code == 200

        login = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": "Yangi-Kuchli-Parol-2026"},
            format="json",
        )
        assert login.status_code == 200

    def test_the_link_works_only_once(self, tenant_a, api_client):
        uid, token = _link_parts(password_reset.build_link(tenant_a.owner))
        assert _confirm(api_client, uid, token, "Yangi-Kuchli-Parol-2026").status_code == 200

        # Token joriy parol XESHIDAN hosil qilinadi — parol
        # o'zgargach u o'z-o'zidan o'ladi.
        again = _confirm(api_client, uid, token, "Yana-Boshqa-Parol-2026")
        assert again.status_code == 422

    def test_a_broken_link_says_the_same_thing_as_an_expired_one(self, tenant_a, api_client):
        # Farqini aytish hujumchiga token tuzilishi haqida ma'lumot
        # berardi.
        uid, _ = _link_parts(password_reset.build_link(tenant_a.owner))
        response = _confirm(api_client, uid, "yolgon-token", "Yangi-Kuchli-Parol-2026")
        assert response.status_code == 422
        assert "eskirgan" in response.json()["error"]["message"]

    def test_an_expired_link_is_refused(self, tenant_a, api_client, settings):
        uid, token = _link_parts(password_reset.build_link(tenant_a.owner))
        # Django tokenning yoshini `PASSWORD_RESET_TIMEOUT` bilan
        # taqqoslaydi: nolga tushirish havolani darhol eskirgan
        # qiladi.
        # `-1`, `0` emas: Django yoshni `> PASSWORD_RESET_TIMEOUT`
        # bilan taqqoslaydi, va bir soniya ichida yaratilgan token
        # uchun yosh `0` — ya'ni `0 > 0` yolg'on bo'lib, havola
        # hali ham ishlab turardi.
        settings.PASSWORD_RESET_TIMEOUT = -1
        assert _confirm(api_client, uid, token, "Yangi-Kuchli-Parol-2026").status_code == 422

    def test_a_weak_password_is_refused(self, tenant_a, api_client):
        uid, token = _link_parts(password_reset.build_link(tenant_a.owner))
        # `400` — maydon validatsiyasi (serializer), `422` esa biznes
        # qoidasi. Tiklash eng ko'p ishlatiladigan "yangi parol
        # o'rnatish" yo'li, va u zaifroq qoidaga bo'ysunmaydi.
        assert _confirm(api_client, uid, token, "12345").status_code == 400

    def test_every_session_is_closed(self, tenant_a, api_client):
        """
        Hisob o'g'irlangan bo'lsa, parolni almashtirishning butun
        ma'nosi shu: eski token bilan ichkarida o'tirgan odam
        chiqarib yuborilishi kerak.
        """
        from apps.accounts.models import RefreshToken

        logged_in = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": tenant_a.password},
            format="json",
        )
        refresh = logged_in.json()["data"]["refresh"]

        uid, token = _link_parts(password_reset.build_link(tenant_a.owner))
        _confirm(api_client, uid, token, "Yangi-Kuchli-Parol-2026")

        with organization_context(tenant_a.organization.id):
            assert RefreshToken.objects.filter(revoked_at__isnull=True).count() == 0

        again = api_client.post(reverse("v1:auth-refresh"), {"refresh": refresh}, format="json")
        assert again.status_code == 401

    def test_it_unblocks_an_account_that_hit_the_login_limit(self, tenant_a, api_client):
        from apps.accounts import lockout

        for _ in range(lockout.MAX_ATTEMPTS):
            api_client.post(
                reverse("v1:auth-login"),
                {"email": tenant_a.owner.email, "password": "xato"},
                format="json",
            )
        assert lockout.is_locked(email=tenant_a.owner.email) is True

        uid, token = _link_parts(password_reset.build_link(tenant_a.owner))
        _confirm(api_client, uid, token, "Yangi-Kuchli-Parol-2026")
        # Parolni unutib bloklangan odam tiklagandan keyin DARHOL
        # kira olishi kerak — aks holda u yana 15 daqiqa kutardi.
        assert lockout.is_locked(email=tenant_a.owner.email) is False


class TestAudit:
    def test_the_request_and_the_reset_are_both_logged(self, tenant_a, api_client):
        from apps.audit.models import AuditLog
        from apps.core.tenancy import platform_context

        _request(api_client, tenant_a.owner.email)
        uid, token = _link_parts(password_reset.build_link(tenant_a.owner))
        _confirm(api_client, uid, token, "Yangi-Kuchli-Parol-2026")

        with organization_context(tenant_a.organization.id):
            actions = set(AuditLog.objects.values_list("action", flat=True))
        assert "password_reset_requested" in actions
        assert "password_reset" in actions

        # Hisob topilmasa ham so'rov fakti qoladi: "kimdir shu
        # emailni tekshirib ko'rdi" — xavfsizlik jurnalining to'g'ri
        # yozuvi. Bunday qatorda TASHKILOT yo'q, shuning uchun u
        # platforma tekisligida o'qiladi (docs/03 §6.3).
        cache.clear()
        _request(api_client, "hechkim@example.uz")
        with platform_context():
            assert AuditLog.objects.filter(
                action="password_reset_requested", actor_email="hechkim@example.uz"
            ).exists()


class TestThrottle:
    def test_the_endpoint_is_rate_limited(self, tenant_a, api_client, monkeypatch):
        from rest_framework.throttling import SimpleRateThrottle

        # DRF `THROTTLE_RATES` ni KLASS atributi sifatida import
        # paytida o'qiydi, shuning uchun `override_settings` unga
        # ta'sir qilmaydi (`test_throttling.py` bilan bir xil naqsh).
        monkeypatch.setattr(
            SimpleRateThrottle,
            "THROTTLE_RATES",
            {"anon": "1000/hour", "password_reset": "2/hour"},
        )
        statuses = [_request(api_client, tenant_a.owner.email).status_code for _ in range(4)]
        # Cheklovsiz endpoint begona odamga bizning pochtamiz bilan
        # boshqa odamni bezovta qilish imkonini berardi.
        assert 429 in statuses
