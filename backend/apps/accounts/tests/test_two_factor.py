"""
Ikki bosqichli tasdiqlash — mijoz tomoni (PLAN 5.4, ADR-24).

Sinaladigan narsalar ro'yxati qisqa, lekin har biri "2FA ishlayapti"
degan da'voni tekshiradi:

* yoqish IKKI qadam — tasdiqlanmagan sir hech narsani o'zgartirmaydi;
* yoqilgach kirish KOD SO'RAYDI, va kodsiz javob `TOTP_REQUIRED`;
* zaxira kodi ishlaydi va BIR MARTA ishlaydi;
* xato kod kirish hisoblagichiga tushadi (cheksiz terish yo'q);
* o'chirish PAROL so'raydi — o'g'irlangan sessiya himoyani olib
  tashlay olmasligi kerak.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts import two_factor
from apps.core.tenancy import organization_context
from apps.core.totp import current_code

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _login(client, tenant, code: str | None = None):
    payload = {"email": tenant.owner.email, "password": tenant.password}
    if code is not None:
        payload["code"] = code
    return client.post(reverse("v1:auth-login"), payload, format="json")


def _enable(tenant) -> list[str]:
    """2FA ni yoqadi va zaxira kodlarini qaytaradi (servis orqali, tez)."""
    with organization_context(tenant.organization.id):
        two_factor.start_setup(tenant.owner)
        codes = two_factor.confirm(user=tenant.owner, code=current_code(tenant.owner.totp_secret))
    assert codes, "sozlash muvaffaqiyatsiz — test shartlari buzilgan"
    return codes


class TestSetup:
    def test_setup_gives_a_secret_and_an_authenticator_link(self, tenant_a):
        response = tenant_a.client().post(reverse("v1:auth-2fa-setup"))
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["secret"]) >= 16
        assert data["otpauth_uri"].startswith("otpauth://totp/")
        assert "Radix%20CRM" in data["otpauth_uri"]

    def test_an_unconfirmed_secret_changes_nothing(self, tenant_a, api_client):
        """
        Sir yaratilgani 2FA yoqilgani EMAS.

        Odam QR'ni ko'rib, ilovaga qo'shmasdan sahifani yopsa va biz
        sirni "yoqilgan" deb hisoblasak, u keyingi kirishda o'z
        hisobidan chiqib qolardi.
        """
        tenant_a.client().post(reverse("v1:auth-2fa-setup"))
        assert _login(api_client, tenant_a).status_code == 200

    def test_a_wrong_code_does_not_enable_it(self, tenant_a, api_client):
        tenant_a.client().post(reverse("v1:auth-2fa-setup"))
        response = tenant_a.client().post(
            reverse("v1:auth-2fa-confirm"), {"code": "000000"}, format="json"
        )
        assert response.status_code == 422
        assert _login(api_client, tenant_a).status_code == 200

    def test_confirming_enables_it_and_returns_backup_codes(self, tenant_a):
        client = tenant_a.client()
        secret = client.post(reverse("v1:auth-2fa-setup")).json()["data"]["secret"]
        response = client.post(
            reverse("v1:auth-2fa-confirm"), {"code": current_code(secret)}, format="json"
        )
        assert response.status_code == 200

        codes = response.json()["data"]["backup_codes"]
        assert len(codes) == 10
        # Kodlar FAQAT shu javobda: saqlangani — xeshi.
        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            stored = tenant_a.owner.totp_backup_codes
        assert all(code not in stored for code in codes)

        profile = client.get(reverse("v1:auth-me")).json()["data"]
        assert profile["user"]["two_factor"] is True
        assert profile["user"]["backup_codes_left"] == 10


class TestLogin:
    def test_a_login_without_a_code_asks_for_one(self, tenant_a, api_client):
        _enable(tenant_a)
        response = _login(api_client, tenant_a)
        assert response.status_code == 401
        # Xato emas, bosqich: frontend aynan shu kodga qarab maydonni
        # ochadi (vendor login sahifasidagi naqsh bilan bir xil).
        assert response.json()["error"]["code"] == "TOTP_REQUIRED"

    def test_the_right_code_lets_you_in(self, tenant_a, api_client):
        _enable(tenant_a)
        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            code = current_code(tenant_a.owner.totp_secret)
        assert _login(api_client, tenant_a, code).status_code == 200

    def test_a_wrong_code_counts_towards_the_lockout(self, tenant_a, api_client):
        """Olti xonali kodni cheksiz terish mumkin bo'lmasligi kerak."""
        from apps.accounts import lockout

        _enable(tenant_a)
        for _ in range(lockout.MAX_ATTEMPTS):
            assert _login(api_client, tenant_a, "000000").status_code == 401
        assert lockout.is_locked(email=tenant_a.owner.email) is True

        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            code = current_code(tenant_a.owner.totp_secret)
        # Blok paroldan ham, koddan ham QAT'IY NAZAR ishlaydi.
        assert _login(api_client, tenant_a, code).status_code == 429

    def test_the_password_is_still_checked_first(self, tenant_a, api_client):
        """
        Xato parol + to'g'ri kod = kirish yo'q, va javob `TOTP_REQUIRED`
        EMAS: aks holda javobning o'zi "bu hisobda 2FA yoqilgan"
        degan ma'lumotni har qanday begonaga aytib qo'yardi.
        """
        _enable(tenant_a)
        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            code = current_code(tenant_a.owner.totp_secret)

        response = api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": "butunlay-boshqa", "code": code},
            format="json",
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


class TestBackupCodes:
    def test_a_backup_code_works_once(self, tenant_a, api_client):
        codes = _enable(tenant_a)

        assert _login(api_client, tenant_a, codes[0]).status_code == 200
        # Ikkinchi marta — yo'q. Qog'ozga yozilgan kod yo'qolishi
        # mumkin, va "ishlatilgan, lekin hamon yaroqli" kod eng yomon
        # holat.
        assert _login(api_client, tenant_a, codes[0]).status_code == 401
        # Qolgan kodlar ishlaydi.
        assert _login(api_client, tenant_a, codes[1]).status_code == 200

    def test_the_format_is_forgiving(self, tenant_a, api_client):
        """Odam kodni qog'ozdan ko'chiradi: katta harf va bo'sh joy kechiriladi."""
        codes = _enable(tenant_a)
        assert _login(api_client, tenant_a, f" {codes[0].upper()} ").status_code == 200

    def test_the_counter_goes_down(self, tenant_a, api_client):
        codes = _enable(tenant_a)
        _login(api_client, tenant_a, codes[0])
        profile = tenant_a.client().get(reverse("v1:auth-me")).json()["data"]
        assert profile["user"]["backup_codes_left"] == 9

    def test_regenerating_kills_the_old_sheet(self, tenant_a, api_client):
        codes = _enable(tenant_a)
        response = tenant_a.client().post(
            reverse("v1:auth-2fa-backup-codes"), {"password": tenant_a.password}, format="json"
        )
        assert response.status_code == 200
        fresh = response.json()["data"]["backup_codes"]

        assert _login(api_client, tenant_a, codes[0]).status_code == 401
        assert _login(api_client, tenant_a, fresh[0]).status_code == 200

    def test_a_wrong_password_does_not_regenerate(self, tenant_a):
        _enable(tenant_a)
        response = tenant_a.client().post(
            reverse("v1:auth-2fa-backup-codes"), {"password": "xato"}, format="json"
        )
        assert response.status_code == 422


class TestDisable:
    def test_disabling_needs_the_password(self, tenant_a, api_client):
        _enable(tenant_a)
        response = tenant_a.client().post(
            reverse("v1:auth-2fa-disable"), {"password": "xato"}, format="json"
        )
        assert response.status_code == 422
        # Hamon yoqilgan.
        assert _login(api_client, tenant_a).status_code == 401

    def test_disabling_removes_the_secret_and_the_codes(self, tenant_a, api_client):
        codes = _enable(tenant_a)
        response = tenant_a.client().post(
            reverse("v1:auth-2fa-disable"), {"password": tenant_a.password}, format="json"
        )
        assert response.status_code == 200

        assert _login(api_client, tenant_a).status_code == 200
        # Eski zaxira kodi ham o'ladi: u sir bilan birga qoldirilsa,
        # o'chirilgan 2FA hamon kirish yo'li bo'lib qolardi.
        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            assert tenant_a.owner.totp_backup_codes == []
            assert tenant_a.owner.totp_secret == ""
        assert all(len(code) > 0 for code in codes)


class TestOtherAccounts:
    def test_it_touches_only_the_callers_own_account(self, tenant_a, tenant_b, api_client):
        """
        Endpointlar faqat O'Z hisobi uchun.

        Ro'yxatda boshqa foydalanuvchi YO'Q — endpoint hech qanday
        identifikator qabul qilmaydi, ya'ni boshqa tenant hisobiga
        ta'sir qiladigan yo'l tuzilish jihatidan mavjud emas. Shu
        test aynan shuni qotirib qo'yadi.
        """
        _enable(tenant_b)
        with organization_context(tenant_a.organization.id):
            tenant_a.owner.refresh_from_db()
            assert tenant_a.owner.has_2fa is False
        assert _login(api_client, tenant_a).status_code == 200

    def test_a_second_account_with_the_same_email_is_asked_after_the_choice(
        self, tenant_a, tenant_b, api_client
    ):
        """
        Bir email ikki bog'chada bo'lsa (ADR-9), 2FA tashkilot
        TANLANGANDAN keyin so'raladi: sir hisobga tegishli, hisob esa
        aynan shu bosqichda aniqlanadi.
        """
        from apps.accounts.models import User

        shared = "ikkita@example.uz"
        for tenant in (tenant_a, tenant_b):
            with organization_context(tenant.organization.id):
                user = User.objects.create_user(
                    email=shared,
                    password=tenant_a.password,
                    full_name="Ikki joyda",
                    organization=tenant.organization,
                    branch=tenant.branch,
                    role=tenant.role("org_owner"),
                )
                if tenant is tenant_b:
                    two_factor.start_setup(user)
                    two_factor.confirm(user=user, code=current_code(user.totp_secret))

        first = api_client.post(
            reverse("v1:auth-login"),
            {"email": shared, "password": tenant_a.password},
            format="json",
        )
        assert first.status_code == 200
        pending = first.json()["data"]["pending_token"]

        def choose(organization_id, code=None):
            payload = {"pending_token": pending, "organization_id": str(organization_id)}
            if code is not None:
                payload["code"] = code
            return api_client.post(reverse("v1:auth-select-organization"), payload, format="json")

        # 2FA yoqilmagan tashkilot — kodsiz kiradi.
        assert choose(tenant_a.organization.id).status_code == 200
        # Yoqilgan tashkilot — kod so'raydi.
        refused = choose(tenant_b.organization.id)
        assert refused.status_code == 401
        assert refused.json()["error"]["code"] == "TOTP_REQUIRED"

        with organization_context(tenant_b.organization.id):
            second = User.objects.get(email=shared)
        assert choose(tenant_b.organization.id, current_code(second.totp_secret)).status_code == 200


class TestAudit:
    def test_every_change_is_logged(self, tenant_a, api_client):
        from apps.audit.models import AuditLog

        codes = _enable(tenant_a)
        client = tenant_a.client()
        client.post(reverse("v1:auth-2fa-setup"))
        secret = client.post(reverse("v1:auth-2fa-setup")).json()["data"]["secret"]
        client.post(reverse("v1:auth-2fa-confirm"), {"code": current_code(secret)}, format="json")
        fresh = client.post(
            reverse("v1:auth-2fa-backup-codes"), {"password": tenant_a.password}, format="json"
        ).json()["data"]["backup_codes"]
        _login(api_client, tenant_a, fresh[0])
        client.post(reverse("v1:auth-2fa-disable"), {"password": tenant_a.password}, format="json")

        with organization_context(tenant_a.organization.id):
            actions = set(AuditLog.objects.values_list("action", flat=True))
        assert {
            "two_factor_enabled",
            "two_factor_codes_renewed",
            "two_factor_backup_used",
            "two_factor_disabled",
        } <= actions
        assert len(codes) == 10
