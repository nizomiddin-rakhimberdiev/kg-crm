"""
Taklif havolasi (PLAN 5.5).

Avval vendor konsolda yangi mijoz ochganda parolni ham yozardi va uni
telefonda yoki Telegramda aytib yuborardi. Shu fayl o'sha odatning
qaytib kelmasligini ushlab turadi; tekshiriladigan to'rt xususiyat:

* yangi hisobga **parolsiz** kiriladigan yo'l yo'q;
* havola **72 soat** yashaydi va **bir martalik**;
* vendor so'rovida yuborilgan parol **e'tiborga olinmaydi**;
* qabul qilish fakti **mijozning** audit jurnaliga tushadi.
"""

from __future__ import annotations

import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts import invite
from apps.accounts.models import User
from apps.accounts.services import register_organization
from apps.core.tenancy import organization_context, platform_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

NEW_PASSWORD = "Birinchi-Juda-Kuchli-2026"  # noqa: S105 — test ma'lumoti


@pytest.fixture
def invited() -> User:
    """Parolsiz ochilgan bog'cha egasi — vendor konsoli shunday ochadi."""
    result = register_organization(
        organization_name="Taklif Bogʻcha",
        contact_email="owner@taklif.uz",
        full_name="Yangi Egasi",
    )
    return result.owner


def _accept(client, token: str, password: str = NEW_PASSWORD):
    return client.post(
        reverse("v1:auth-invite-accept"), {"token": token, "password": password}, format="json"
    )


def _login(client, email: str, password: str):
    return client.post(
        reverse("v1:auth-login"), {"email": email, "password": password}, format="json"
    )


class TestPasswordlessAccount:
    def test_a_new_owner_cannot_be_logged_into_before_accepting(self, invited, api_client):
        """
        Parol o'rnatilmaguncha hisob YOPIQ.

        Bo'sh parol bilan qoldirilsa `check_password("")` haqiqat
        qaytarishi mumkin edi — shuning uchun parol "bo'sh" emas,
        **ishlatib bo'lmaydigan** qilib qo'yiladi.
        """
        assert invited.has_usable_password() is False
        # Bo'sh parol serializer'da (`400`), qolganlari
        # autentifikatsiyada (`401`) to'xtaydi — muhimi birortasi ham
        # ichkariga kiritmasligi.
        for attempt in ("", " ", "parol", NEW_PASSWORD):
            assert _login(api_client, invited.email, attempt).status_code != 200

    def test_accepting_opens_the_account(self, invited, api_client):
        assert _accept(api_client, invite.make_token(invited)).status_code == 200
        assert _login(api_client, invited.email, NEW_PASSWORD).status_code == 200


class TestLink:
    def test_the_link_works_only_once(self, invited, api_client):
        token = invite.make_token(invited)
        assert _accept(api_client, token).status_code == 200

        # Token ichida parol xeshining izi bor: parol o'rnatilgach iz
        # o'zgaradi va havola o'z-o'zidan o'ladi. Bir martalik
        # xususiyat tekinga keladi — yangi jadval ham, tozalash
        # vazifasi ham kerak emas.
        again = _accept(api_client, token, "Yana-Boshqa-Parol-2026")
        assert again.status_code == 422
        assert "eskirgan" in again.json()["error"]["message"]

        # Eski havola bilan yuborilgan parol hisobga TUSHMAYDI.
        assert _login(api_client, invited.email, "Yana-Boshqa-Parol-2026").status_code == 401

    def test_a_broken_link_says_the_same_thing_as_a_used_one(self, invited, api_client):
        response = _accept(api_client, "yolgon-token")
        assert response.status_code == 422
        assert "eskirgan" in response.json()["error"]["message"]

    def test_an_expired_link_is_refused(self, invited):
        token = invite.make_token(invited)
        assert invite.read_token(token) is not None
        # `max_age` ataylab parametr: 72 soatni test ichida kutib
        # bo'lmaydi, va vaqtni "soxtalashtirish" o'rniga qoidani
        # to'g'ridan-to'g'ri so'rash ishonchliroq.
        assert invite.read_token(token, max_age=-1) is None

    def test_the_window_is_three_days(self):
        """
        72 soat — qaror, tasodif emas (`invite.py` izohiga qarang):
        tiklash havolasi 30 daqiqa yashaydi, chunki odam uni hozir
        so'ragan; taklif esa sotuv suhbatidan keyin yuboriladi va
        ega uni dushanba kuni ochishi mumkin.
        """
        assert invite.INVITE_MAX_AGE == 72 * 3600

    def test_the_token_survives_without_a_tenant_context(self, invited):
        """
        Qabul qilish paytida tenant ANIQLANMAGAN: odam hali kirmagan.

        Shuning uchun qidiruv `auth_lookup_context()` orqali, nomi
        bilan so'raladi (docs/03 §6.3) — aks holda RLS hech narsa
        qaytarmaydi va havola "eskirgan" deb rad etilardi.
        """
        assert invite.read_token(invite.make_token(invited)) == invited

    def test_an_inactive_account_cannot_accept(self, invited, api_client):
        with organization_context(invited.organization_id):
            invited.is_active = False
            invited.save(update_fields=["is_active"])
        assert _accept(api_client, invite.make_token(invited)).status_code == 422


class TestValidation:
    def test_a_weak_password_is_refused(self, invited, api_client):
        # `400` — maydon validatsiyasi, `422` esa biznes qoidasi.
        # Birinchi parol eng ko'p ishlatiladigan "parol o'rnatish"
        # yo'li va u zaifroq qoidaga bo'ysunmaydi.
        assert _accept(api_client, invite.make_token(invited), "12345").status_code == 400
        assert _login(api_client, invited.email, "12345").status_code == 401


class TestEmail:
    def test_the_letter_carries_the_link_and_the_window(self, invited):
        mail.outbox.clear()
        link = invite.build_link(invited)
        invite.send_invite_email(invited, link, "Taklif Bogʻcha")

        assert len(mail.outbox) == 1
        body = mail.outbox[0].body
        assert "/invite?token=" in body
        assert "72 soat" in body
        # Parol xatda YO'Q va bo'lishi ham mumkin emas: biz uni
        # bilmaymiz.
        assert "parol:" not in body.lower()

    def test_a_broken_mailbox_does_not_undo_the_organization(self, monkeypatch):
        """
        Pochta ishlamasa tashkilot YARATILGAN qoladi.

        Sotuv suhbati tugagan, mijoz kutayapti — va vendor javobda
        havolani ham oladi, ya'ni uni qo'lda uzatishi mumkin.
        """

        def boom(**kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("SMTP yo'q")

        owner = register_organization(
            organization_name="Pochtasiz Bogʻcha",
            contact_email="owner@pochtasiz.uz",
            full_name="Egasi",
        ).owner

        monkeypatch.setattr("apps.accounts.invite.send_mail", boom)
        # Xato YUTILADI: u faqat log'ga tushadi.
        invite.send_invite_email(owner, invite.build_link(owner), "Pochtasiz Bogʻcha")

        from apps.organizations.models import Organization

        with platform_context():
            assert Organization.objects.filter(name="Pochtasiz Bogʻcha").exists()


class TestAudit:
    def test_the_acceptance_lands_in_the_customers_journal(self, invited, api_client):
        from apps.audit.models import AuditLog

        _accept(api_client, invite.make_token(invited))

        # Yozuv MIJOZNING tashkilotida: bog'cha o'z jurnalida
        # "hisob jonlandi" faktini ko'rishi kerak, va vendor
        # tekisligida uni ko'rib bo'lmaydi (ADR-10).
        with organization_context(invited.organization_id):
            row = AuditLog.objects.get(action="invite_accepted")
        assert row.actor_id == invited.id
        assert row.changes == {"invite_accepted": True}
