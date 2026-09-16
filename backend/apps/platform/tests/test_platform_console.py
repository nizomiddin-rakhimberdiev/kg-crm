"""
Platforma konsoli testlari (docs/04 §19, ADR-10).

Bu fayldagi eng muhim testlar — **vendor NIMANI KO'RA OLMASLIGI**
haqida. Konsolning ishlashi oson tekshiriladi va u ishlamasa darrov
ma'lum bo'ladi. Ortiqcha kirish esa jimgina yashaydi: hamma narsa
normal ishlaydi, faqat kimdir ko'rmasligi kerak narsani ko'rib turadi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.children.models import Child
from apps.core.tenancy import organization_context, platform_context
from apps.platform import services
from apps.platform.authentication import issue_platform_token
from apps.platform.models import PlatformRole, PlatformUser, SupportGrant
from apps.platform.totp import current_code, generate_secret

pytestmark = pytest.mark.django_db

PASSWORD = "Platforma-Juda-Kuchli-2026"  # noqa: S105


def _platform_user(role: str = PlatformRole.ADMIN, email: str = "admin@kg-crm.uz") -> PlatformUser:
    secret = generate_secret()
    with platform_context():
        user = PlatformUser(
            email=email,
            full_name="Vendor Xodimi",
            role=role,
            totp_secret=secret,
            totp_confirmed_at=timezone.now(),
        )
        user.set_password(PASSWORD)
        user.save()
    return user


def _client(user: PlatformUser) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_platform_token(user)}")
    return client


def _add_children(tenant, count: int) -> None:
    with organization_context(tenant.organization.id):
        for index in range(count):
            Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name=f"Bola{index}",
                last_name="Testov",
                date_of_birth=date(2021, 3, 14),
                gender="male",
            )


class TestPlatformLogin:
    def test_login_requires_all_three_factors(self, tenant_a):
        user = _platform_user()
        client = APIClient()
        url = "/api/v1/platform/auth/login"

        # Kod bo'lmasa — validatsiya xatosi.
        assert client.post(url, {"email": user.email, "password": PASSWORD}).status_code == 400
        # Noto'g'ri kod bilan — 401.
        assert (
            client.post(
                url, {"email": user.email, "password": PASSWORD, "code": "000000"}
            ).status_code
            == 401
        )
        # Uchtasi ham to'g'ri — kiradi.
        response = client.post(
            url,
            {
                "email": user.email,
                "password": PASSWORD,
                "code": current_code(user.totp_secret),
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["access"]

    def test_error_message_never_says_which_factor_failed(self, tenant_a):
        """
        Xato xabari HAR DOIM bir xil.

        "Parol noto'g'ri" va "kod noto'g'ri" ni ajratish hujumchiga
        qaysi bosqichda ekanini aytardi — ya'ni parolni topganini
        tasdiqlardi.
        """
        user = _platform_user()
        client = APIClient()
        url = "/api/v1/platform/auth/login"

        wrong_password = client.post(
            url, {"email": user.email, "password": "xato", "code": current_code(user.totp_secret)}
        )
        wrong_code = client.post(url, {"email": user.email, "password": PASSWORD, "code": "123456"})
        unknown_email = client.post(
            url, {"email": "yoq@kg-crm.uz", "password": PASSWORD, "code": "123456"}
        )

        messages = {
            wrong_password.json()["error"]["message"],
            wrong_code.json()["error"]["message"],
            unknown_email.json()["error"]["message"],
        }
        assert len(messages) == 1, f"Xabarlar farq qilyapti: {messages}"

    def test_account_without_2fa_cannot_log_in(self, tenant_a):
        """
        2FA sozlanmagan hisob umuman kira olmaydi.

        "Keyin yoqaman" degan holat yo'q: vendor hisobining buzilishi
        BARCHA mijozlarga tegadigan yagona hodisa (ADR-10).
        """
        with platform_context():
            user = PlatformUser(email="no2fa@kg-crm.uz", full_name="X")
            user.set_password(PASSWORD)
            user.save()

        response = APIClient().post(
            "/api/v1/platform/auth/login",
            {"email": user.email, "password": PASSWORD, "code": "123456"},
        )
        assert response.status_code == 401


class TestPlaneSeparation:
    def test_customer_token_cannot_reach_the_console(self, tenant_a):
        """
        Mijoz tokeni platforma konsoliga KIRMAYDI.

        Ikki tekislik tokenlari hech qachon almashinmaydi. Aks holda
        bitta mijozning egasi butun platformaga kirish yo'lini
        qidirishni boshlardi (ADR-10).
        """
        response = tenant_a.client().get("/api/v1/platform/organizations")
        assert response.status_code == 401

    def test_platform_token_cannot_reach_the_customer_api(self, tenant_a):
        """
        Teskarisi ham: vendor tokeni mijoz API'siga kirmaydi.

        Vendor tokenida `organization_id` yo'q, ya'ni tenant konteksti
        o'rnatilmaydi va so'rov 401 oladi. Bu tasodifiy emas — mijoz
        API'si tashkilotni TOKENDAN oladi.
        """
        user = _platform_user()
        response = _client(user).get("/api/v1/children")
        assert response.status_code == 401

    def test_anonymous_cannot_reach_the_console(self):
        assert APIClient().get("/api/v1/platform/organizations").status_code == 401


class TestMetadataOnly:
    """
    Konsol metama'lumotni beradi, mijoz ma'lumotini BERMAYDI.

    Bu chegara ikki joyda mustaqil qo'llanadi: bu yerda (endpoint
    umuman mavjud emas) va bazada (RLS operatsion jadvallarni platforma
    rejimida yopadi — `apps/core/tests/test_rls.py`).
    """

    def test_organization_list_returns_counts_not_rows(self, tenant_a, tenant_b):
        _add_children(tenant_a, 7)
        rows = _client(_platform_user()).get("/api/v1/platform/organizations").json()["data"]

        assert len(rows) >= 2
        alfa = next(row for row in rows if row["id"] == str(tenant_a.organization.id))
        assert alfa["billable_children"] == 7

        # Javobda bolalar ro'yxati bo'lmasligi kerak — hech qanday
        # ko'rinishda.
        serialized = str(rows)
        assert "Bola0" not in serialized
        assert "Testov" not in serialized

    def test_organization_detail_has_no_operational_rows(self, tenant_a):
        _add_children(tenant_a, 3)
        with organization_context(tenant_a.organization.id):
            from apps.finance import services as finance

            child = Child.objects.first()
            finance.record_payment(child=child, amount=Decimal("500000"), method="cash")

        detail = (
            _client(_platform_user())
            .get(f"/api/v1/platform/organizations/{tenant_a.organization.id}")
            .json()["data"]
        )
        assert detail["billable_children"] == 3
        assert set(detail) == {
            "id",
            "name",
            "slug",
            "contact_email",
            "contact_phone",
            "is_active",
            "created_at",
            "subscription",
            "billable_children",
            "usage_history",
            "invoices",
        }
        assert "Testov" not in str(detail)
        assert "500000" not in str(detail)

    def test_there_is_no_endpoint_that_lists_children(self, tenant_a):
        """
        Konsolda bolalar ro'yxatini beradigan endpoint YO'Q.

        Bu testning maqsadi — kelajakda kimdir "qulay bo'lardi" deb
        qo'shishga urinsa, u avval shu testni o'chirishi kerak bo'ladi.
        Ongli qaror qabul qilishga majbur qilish — himoyaning bir turi.
        """
        client = _client(_platform_user())
        for path in (
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/children",
            "/api/v1/platform/children",
            "/api/v1/platform/payments",
        ):
            assert client.get(path).status_code == 404, f"{path} mavjud bo'lib qoldi"


class TestSupportGrants:
    def test_grant_requires_a_reason(self, tenant_a):
        response = _client(_platform_user()).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/support-grant",
            {"reason": "", "hours": 2},
            format="json",
        )
        assert response.status_code == 400

    def test_grant_is_time_boxed(self, tenant_a):
        """
        Ruxsat o'zi tugaydi.

        "Doimiy kirish" degan tushuncha yo'q: muddatsiz ruxsat vaqt
        o'tib oddiy imtiyozga aylanadi va uni qaytarib olishni hech kim
        eslamaydi.
        """
        user = _platform_user()
        response = _client(user).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/support-grant",
            {"reason": "Mijoz hisob-fakturada xato haqida yozdi", "hours": 2},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["is_active"] is True

        with platform_context():
            grant = SupportGrant.objects.get(pk=data["id"])
        assert (grant.expires_at - timezone.now()).total_seconds() <= 2 * 3600 + 5

    def test_grant_is_visible_to_the_customer(self, tenant_a):
        """
        Mijoz vendor kirishini KO'RADI.

        Ko'rinmaydigan kirish ishonchni texnik jihatdan emas, ijtimoiy
        jihatdan buzadi: "bizning ma'lumotimizga kim qaraydi?" degan
        savolga javob mijozning o'zida bo'lishi kerak (ADR-10).
        """
        user = _platform_user()
        _client(user).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/support-grant",
            {"reason": "To'lov bo'yicha murojaat", "hours": 1},
            format="json",
        )

        rows = tenant_a.client().get("/api/v1/audit-logs/platform-access").json()["data"]
        assert len(rows) == 1
        assert rows[0]["entity_type"] == "support_grant"
        assert rows[0]["actor_email"] == user.email
        assert rows[0]["changes"]["reason"] == "To'lov bo'yicha murojaat"

    def test_another_organization_does_not_see_the_grant(self, tenant_a, tenant_b):
        _client(_platform_user()).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/support-grant",
            {"reason": "Tekshiruv", "hours": 1},
            format="json",
        )
        rows = tenant_b.client().get("/api/v1/audit-logs/platform-access").json()["data"]
        assert rows == []

    def test_grant_does_not_by_itself_open_customer_data(self, tenant_a):
        """
        Ruxsat berilgani bilan konsol mijoz ma'lumotini KO'RSATMAYDI.

        Ruxsat oddiy mijoz API'si orqali ishlash huquqini beradi —
        alohida, imtiyozli kod yo'li ochmaydi. Ya'ni audit qilinadigan
        yagona yo'l bor va u allaqachon sinalgan (docs/04 §19).
        """
        _add_children(tenant_a, 4)
        user = _platform_user()
        client = _client(user)
        client.post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/support-grant",
            {"reason": "Tekshiruv", "hours": 1},
            format="json",
        )
        detail = client.get(f"/api/v1/platform/organizations/{tenant_a.organization.id}").json()[
            "data"
        ]
        assert "Testov" not in str(detail)


class TestCommercialActions:
    def test_support_staff_cannot_suspend(self, tenant_a):
        """
        Qo'llab-quvvatlash xodimi obunani to'xtata olmaydi.

        To'xtatish — tijorat qarori, texnik yordam emas. Bu ajratish
        "yordam berayotgan xodim tasodifan mijozni ishdan to'xtatdi"
        holatini imkonsiz qiladi.
        """
        support = _platform_user(role=PlatformRole.SUPPORT, email="support@kg-crm.uz")
        response = _client(support).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/suspend",
            {"reason": "Test"},
            format="json",
        )
        assert response.status_code == 422

    def test_admin_can_suspend_and_reactivate(self, tenant_a):
        admin = _platform_user()
        client = _client(admin)
        base = f"/api/v1/platform/organizations/{tenant_a.organization.id}"

        suspended = client.post(f"{base}/suspend", {"reason": "To'lov yo'q"}, format="json")
        assert suspended.json()["data"]["status"] == "suspended"

        # Mijoz endi yozolmaydi, lekin O'QIY oladi (docs/03 §20.6).
        assert tenant_a.client().get("/api/v1/children").status_code == 200
        assert (
            tenant_a.client()
            .post("/api/v1/tariffs", {"name": "X", "amount": "1"}, format="json")
            .status_code
            == 402
        )

        restored = client.post(f"{base}/reactivate")
        assert restored.json()["data"]["status"] == "active"
        assert (
            tenant_a.client()
            .post("/api/v1/tariffs", {"name": "Y", "amount": "1"}, format="json")
            .status_code
            == 201
        )

    def test_suspension_reason_is_recorded_and_visible(self, tenant_a):
        admin = _platform_user()
        _client(admin).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/suspend",
            {"reason": "Uch oy to'lov yo'q"},
            format="json",
        )
        rows = tenant_a.client().get("/api/v1/audit-logs/platform-access").json()["data"]
        assert any(row["changes"].get("reason") == "Uch oy to'lov yo'q" for row in rows)

    def test_extend_trial_requires_a_reason(self, tenant_a):
        response = _client(_platform_user()).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/extend-trial",
            {"days": 7},
            format="json",
        )
        assert response.status_code == 400

    def test_extend_trial_moves_the_deadline(self, tenant_a):
        from apps.subscriptions.models import Subscription

        with organization_context(tenant_a.organization.id):
            before = Subscription.objects.get(organization=tenant_a.organization).trial_ends_at

        response = _client(_platform_user()).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/extend-trial",
            {"days": 7, "reason": "Mijoz bayramda ishlamadi"},
            format="json",
        )
        assert response.status_code == 200

        with organization_context(tenant_a.organization.id):
            after = Subscription.objects.get(organization=tenant_a.organization).trial_ends_at
        assert (after - before).days == 7


class TestWorkList:
    def test_expiring_shows_trials_and_overdue(self, tenant_a, tenant_b):
        data = (
            _client(_platform_user()).get("/api/v1/platform/subscriptions/expiring").json()["data"]
        )
        assert data["counts"]["trialing"] >= 2
        assert "unpaid_total" in data
        # Bu ro'yxat ham metama'lumot: tashkilot nomi va sana, boshqa
        # hech narsa.
        assert all(
            set(row) <= {"organization", "organization_id", "trial_ends_at"}
            for row in data["trials_ending"]
        )


class TestAudit:
    def test_every_platform_action_is_logged(self, tenant_a):
        from apps.audit.models import AuditLog

        admin = _platform_user()
        _client(admin).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/support-grant",
            {"reason": "Tekshiruv", "hours": 1},
            format="json",
        )
        with organization_context(tenant_a.organization.id):
            entry = AuditLog.objects.filter(entity_type="support_grant").first()
        assert entry is not None
        assert entry.actor is None, "Vendor `accounts.User` sifatida yozilmasligi kerak"
        assert entry.actor_email == admin.email
        assert entry.changes["platform_user"] == str(admin.id)

    def test_platform_login_is_logged_without_an_organization(self):
        from apps.audit.models import AuditLog

        user = _platform_user()
        APIClient().post(
            "/api/v1/platform/auth/login",
            {"email": user.email, "password": PASSWORD, "code": current_code(user.totp_secret)},
        )
        with platform_context():
            entry = AuditLog.objects.filter(
                action="login", actor_email=user.email, organization__isnull=True
            ).first()
        assert entry is not None


class TestTotp:
    def test_a_code_from_the_previous_step_still_works(self):
        """
        Bir qadam farq qabul qilinadi.

        Telefon soati bir necha soniya farq qilishi normal holat va uni
        "noto'g'ri kod" deb ko'rsatish foydalanuvchini tizimdan
        chiqarib yuborardi.
        """
        from apps.platform.totp import PERIOD, verify

        secret = generate_secret()
        now = timezone.now().timestamp()
        assert verify(secret, current_code(secret, at=now - PERIOD), at=now)

    def test_a_code_from_five_minutes_ago_is_rejected(self):
        from apps.platform.totp import verify

        secret = generate_secret()
        now = timezone.now().timestamp()
        assert not verify(secret, current_code(secret, at=now - 300), at=now)

    def test_garbage_is_rejected(self):
        from apps.platform.totp import verify

        secret = generate_secret()
        for value in ("", "abcdef", "12345", None):
            assert not verify(secret, value or "")


class TestGrantHelper:
    def test_active_grant_is_found_and_expired_is_not(self, tenant_a):
        user = _platform_user()
        grant = services.create_support_grant(
            actor=user,
            organization_id=tenant_a.organization.id,
            reason="Tekshiruv",
            hours=1,
        )
        assert (
            services.active_grant(platform_user=user, organization_id=tenant_a.organization.id)
            is not None
        )

        services.revoke_support_grant(actor=user, grant=grant)
        assert (
            services.active_grant(platform_user=user, organization_id=tenant_a.organization.id)
            is None
        )


class TestOrganizationCreation:
    """
    Mijozni VENDOR ochadi — ochiq `/auth/signup` o'rniga.

    Bu sinfdagi testlar `apps/accounts/tests/test_auth.py::TestSignup` dan
    ko'chirilgan: tekshiriladigan xulq-atvor o'zgarmadi (tashkilot, filial,
    egasi, rollar, sinov obunasi bir tranzaksiyada yaratiladi), faqat
    eshik ko'chdi — endi u ochiq emas, vendor konsolida.
    """

    URL = "/api/v1/platform/organizations/create"

    def _payload(self, **overrides):
        payload = {
            "organization_name": "Yangi Bog'cha",
            "contact_email": "owner@yangi.uz",
            "full_name": "Aziz Karimov",
            "password": "Mijoz-Juda-Kuchli-2026",
        }
        payload.update(overrides)
        return payload

    def test_creates_organization_branch_owner_and_roles(self):
        response = _client(_platform_user()).post(self.URL, self._payload(), format="json")
        assert response.status_code == 201, response.content
        data = response.json()["data"]

        assert data["name"] == "Yangi Bog'cha"
        assert data["owner_email"] == "owner@yangi.uz"
        assert data["slug"] == "yangi-bogcha"
        assert data["login_url"].endswith("/t/yangi-bogcha/login")

        from apps.accounts.models import Role, User
        from apps.branches.models import Branch
        from apps.organizations.models import Organization

        with platform_context():
            organization = Organization.objects.get(slug="yangi-bogcha")

        with organization_context(organization.id):
            owner = User.objects.get(email="owner@yangi.uz")
            # Egasi org_owner rolini oladi va barcha modullarga kiradi
            # (docs/02 §11.2) — bu avval signup javobida tekshirilardi.
            assert owner.role.code == "org_owner"
            assert Role.objects.filter(organization=organization).count() == 5
            assert Branch.objects.filter(organization=organization).count() == 1

    def test_the_trial_starts_with_the_account(self):
        """Obunasiz tashkilot — hisob-kitobi yo'q mijoz degani."""
        response = _client(_platform_user()).post(self.URL, self._payload(), format="json")
        assert response.status_code == 201

        from apps.subscriptions.models import Subscription

        with platform_context():
            subscription = Subscription.all_objects.get(organization__slug="yangi-bogcha")
        assert subscription.status == "trialing"
        assert subscription.trial_ends_at is not None

    def test_weak_password_rejected(self):
        response = _client(_platform_user()).post(
            self.URL, self._payload(password="123"), format="json"
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_creation_is_atomic(self, monkeypatch):
        """
        Yarim yaratilgan tashkilot qolmasligi shart.

        Aks holda kirib bo'lmaydigan, lekin mavjud tenant paydo bo'ladi
        va uni qo'lda tozalash kerak bo'ladi.
        """
        from apps.accounts import services as account_services

        def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise RuntimeError("seed muvaffaqiyatsiz")

        monkeypatch.setattr(account_services, "seed_system_roles", boom)

        response = _client(_platform_user()).post(
            self.URL, self._payload(organization_name="Yiqiladigan"), format="json"
        )
        assert response.status_code == 500
        assert "seed muvaffaqiyatsiz" not in response.content.decode()

        from apps.organizations.models import Organization

        with platform_context():
            assert not Organization.objects.filter(name="Yiqiladigan").exists()

    # --- Manzil (slug) ---

    def test_the_vendor_can_choose_the_address(self):
        response = _client(_platform_user()).post(
            self.URL, self._payload(slug="Quyosh Bog'chasi"), format="json"
        )
        assert response.status_code == 201
        assert response.json()["data"]["slug"] == "quyosh-bogchasi"

    def test_a_reserved_address_is_refused(self):
        """
        `www`, `api`, `admin` kabi nomlar bugun zarar qilmaydi, lekin
        subdomenga o'tilganda infratuzilma bilan urishadi. Ro'yxatni
        keyin qo'shish kech bo'ladi — mijoz allaqachon o'sha manzilda
        ishlab turgan bo'ladi.
        """
        response = _client(_platform_user()).post(
            self.URL, self._payload(slug="api"), format="json"
        )
        assert response.status_code == 422
        assert "band nom" in response.json()["error"]["message"]

    def test_a_taken_address_is_refused(self, tenant_a):
        with platform_context():
            taken = tenant_a.organization.slug
        response = _client(_platform_user()).post(
            self.URL, self._payload(slug=taken), format="json"
        )
        assert response.status_code == 422

    # --- Kim ocha oladi ---

    def test_support_staff_cannot_create_a_customer(self):
        """
        Yangi tenant — yangi obuna, yangi hisob-kitob va O'CHIRILMAYDIGAN
        ma'lumot. Qo'llab-quvvatlash xodimi buni yaratmasligi kerak.
        """
        support = _platform_user(role=PlatformRole.SUPPORT, email="support@kg-crm.uz")
        response = _client(support).post(self.URL, self._payload(), format="json")
        assert response.status_code == 422

        from apps.organizations.models import Organization

        with platform_context():
            assert not Organization.objects.filter(slug="yangi-bogcha").exists()

    def test_a_customer_token_cannot_open_accounts(self, tenant_a):
        """Ikki tekislik tokenlari hech qachon almashinmaydi (ADR-10)."""
        response = tenant_a.client().post(self.URL, self._payload(), format="json")
        assert response.status_code in (401, 403)

    def test_the_customer_sees_who_opened_their_account(self):
        """
        Yozuv MIJOZNING audit jurnalida ko'rinadi.

        Vendor mijozning tashkilotiga tegsa, mijoz buni bilishi kerak —
        akkauntni ochish ham shunga kiradi.
        """
        assert (
            _client(_platform_user()).post(self.URL, self._payload(), format="json").status_code
            == 201
        )

        from apps.audit.models import AuditLog
        from apps.organizations.models import Organization

        with platform_context():
            organization = Organization.objects.get(slug="yangi-bogcha")

        with organization_context(organization.id):
            entry = AuditLog.objects.filter(entity_type="organization", action="create").first()
            assert entry is not None
            assert entry.organization_id == organization.id
            assert entry.changes["slug"] == "yangi-bogcha"


class TestSupportSession:
    """
    Ruxsat endi HAQIQIY kirish beradi — va u qattiq cheklangan.

    Bu sinf `SupportGrant` ning yetishmayotgan yarmini qoplaydi. Avval
    ruxsat yozilardi va mijoz uni ko'rardi, lekin u hech narsa ochmasdi:
    `active_grant()` ishlab chiqarish kodida chaqirilmasdi. Amalda bu
    qo'llab-quvvatlashni mijozning parolini bilishga majbur qilardi —
    ya'ni audit jurnali vendor amalini bog'chaning o'z egasi deb
    yozadigan holatga.

    Eng muhim testlar — sessiya NIMA QILA OLMASLIGI haqida.
    """

    def _session(self, tenant, user=None, hours: int = 2):
        """Ruxsat oladi va kirish tokenini qaytaradi."""
        actor = user or _platform_user()
        services.create_support_grant(
            actor=actor,
            organization_id=tenant.organization.id,
            reason="Mijoz to'lov ko'rinmayapti deb yozdi",
            hours=hours,
        )
        client = _client(actor)
        response = client.post(
            f"/api/v1/platform/organizations/{tenant.organization.id}/support-session"
        )
        assert response.status_code == 200, response.content
        return actor, response.json()["data"]

    def _as_support(self, token: str) -> APIClient:
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    # --- Kirish ishlaydi ---

    def test_the_session_can_read_the_customers_data(self, tenant_a):
        _add_children(tenant_a, 3)
        _, session = self._session(tenant_a)

        assert session["read_only"] is True
        assert session["app_url"].endswith(f"/t/{session['slug']}")

        response = self._as_support(session["access"]).get("/api/v1/children")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 3

    def test_entering_is_written_to_the_customers_audit_log(self, tenant_a):
        self._session(tenant_a)

        from apps.audit.models import AuditLog

        with organization_context(tenant_a.organization.id):
            entry = AuditLog.objects.filter(entity_type="support_session").first()
            assert entry is not None
            assert entry.organization_id == tenant_a.organization.id
            # Sabab yozuvda qoladi: "nega kirdingiz?" savoli keyin emas,
            # kirishdan oldin javob olgan.
            assert "to'lov" in entry.changes["reason"]

    # --- Kirish CHEKLANGAN ---

    def test_the_session_cannot_write_anything(self, tenant_a):
        """
        Faqat o'qish. Yozish mijozning ma'lumotini uning xabarisiz
        o'zgartirardi — va audit jurnalida bu bog'chaning O'Z egasi
        nomidan ko'rinardi, chunki sessiya uning hisobi orqali ishlaydi.
        """
        _add_children(tenant_a, 1)
        _, session = self._session(tenant_a)
        client = self._as_support(session["access"])

        with organization_context(tenant_a.organization.id):
            child_id = Child.objects.first().id

        payloads = [
            ("post", "/api/v1/children", {"first_name": "Yangi", "last_name": "Bola"}),
            ("patch", f"/api/v1/children/{child_id}", {"first_name": "O'zgargan"}),
            ("delete", f"/api/v1/children/{child_id}", None),
        ]
        for method, url, body in payloads:
            response = getattr(client, method)(url, body, format="json")
            assert response.status_code == 403, f"{method.upper()} {url} → {response.status_code}"

        with organization_context(tenant_a.organization.id):
            assert Child.objects.filter(pk=child_id, is_active=True).exists()

    def test_revoking_the_grant_closes_the_session_immediately(self, tenant_a):
        """
        Tokenning o'z muddati yetarli emas.

        Ruxsat bekor qilinganda kirish DARHOL yopilishi kerak — 30
        daqiqadan keyin emas. Aks holda "bekor qilish" tugmasi yolg'on
        tinchlik berardi.
        """
        actor, session = self._session(tenant_a)
        client = self._as_support(session["access"])
        assert client.get("/api/v1/children").status_code == 200

        with platform_context():
            grant = SupportGrant.objects.filter(platform_user=actor).first()
        services.revoke_support_grant(actor=actor, grant=grant)

        assert client.get("/api/v1/children").status_code == 401

    def test_an_expired_grant_closes_the_session(self, tenant_a):
        actor, session = self._session(tenant_a)
        client = self._as_support(session["access"])

        with platform_context():
            grant = SupportGrant.objects.filter(platform_user=actor).first()
            grant.expires_at = timezone.now() - timedelta(minutes=1)
            grant.save(update_fields=["expires_at"])

        assert client.get("/api/v1/children").status_code == 401

    def test_without_a_grant_there_is_no_session(self, tenant_a):
        """Sababsiz ruxsat — sababsiz kirish."""
        response = _client(_platform_user()).post(
            f"/api/v1/platform/organizations/{tenant_a.organization.id}/support-session"
        )
        assert response.status_code == 422
        assert "ruxsat yo'q" in response.json()["error"]["message"]

    def test_a_grant_for_one_customer_does_not_open_another(self, tenant_a, tenant_b):
        """Ruxsat BITTA tashkilotga beriladi (ADR-9)."""
        _add_children(tenant_b, 2)
        actor = _platform_user()
        self._session(tenant_a, user=actor)

        response = _client(actor).post(
            f"/api/v1/platform/organizations/{tenant_b.organization.id}/support-session"
        )
        assert response.status_code == 422

    def test_the_session_token_cannot_enter_the_vendor_console(self, tenant_a):
        """
        Ikki tekislik tokenlari almashinmaydi (ADR-10).

        Sessiya tokeni — MIJOZ tekisligining tokeni. U bilan konsolga
        qaytib kirish mumkin bo'lsa, u yerdan boshqa bog'chalarga ruxsat
        olish yo'li ochilardi.
        """
        _, session = self._session(tenant_a)
        response = self._as_support(session["access"]).get("/api/v1/platform/organizations")
        assert response.status_code in (401, 403)

    def test_the_session_sees_only_that_customer(self, tenant_a, tenant_b):
        """RLS sessiya uchun ham xuddi mijoz uchundek ishlaydi."""
        _add_children(tenant_a, 2)
        _add_children(tenant_b, 5)
        _, session = self._session(tenant_a)

        response = self._as_support(session["access"]).get("/api/v1/children")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 2
