"""
Xavfsizlik ko'rigi — hujumchi nuqtai nazaridan (docs/06 Sprint 11).

Cross-tenant sweep har bir endpointni bir xil naqsh bo'yicha tekshiradi.
Bu fayl esa boshqa savol beradi: **agar men ataylab urinsam, nima
qilishim mumkin?** Naqsh emas, stsenariy.

Uchta hujum turi:
  1. ID enumeratsiyasi — boshqa mijozning ID'lari mavjudligini aniqlash
  2. Login orakuli — email qaysi bog'chalarda borligini bilib olish
  3. Tenant qochish — token, parametr yoki filtr orqali chegaradan o'tish
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance

pytestmark = [pytest.mark.django_db, pytest.mark.tenancy]

PASSWORD = "Juda-Kuchli-Parol-2026"  # noqa: S105


def _child(tenant, name: str = "Ali") -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Testov",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


class TestIdEnumeration:
    """
    Mavjud va mavjud bo'lmagan ID bir xil javob berishi kerak.

    Farq bo'lsa, hujumchi ID'larni tanlab, qaysilari "bor" ekanini
    aniqlaydi — bu allaqachon ma'lumot: mijozlar soni, o'sish sur'ati,
    va aniq nishonlar.
    """

    def test_existing_and_missing_ids_look_identical(self, tenant_a, tenant_b):
        foreign = _child(tenant_b, "Begona")
        missing = uuid.uuid4()

        client = tenant_a.client()
        existing_response = client.get(f"/api/v1/children/{foreign.id}")
        missing_response = client.get(f"/api/v1/children/{missing}")

        assert existing_response.status_code == missing_response.status_code == 404
        assert existing_response.json() == missing_response.json()

    def test_delete_reveals_nothing_either(self, tenant_a, tenant_b):
        foreign = _child(tenant_b, "Begona")
        client = tenant_a.client()
        assert (
            client.delete(f"/api/v1/children/{foreign.id}").status_code
            == client.delete(f"/api/v1/children/{uuid.uuid4()}").status_code
        )

    def test_malformed_id_is_a_clean_404_not_a_500(self, tenant_a):
        """
        Buzuq ID `500` bermasligi kerak.

        `500` stek izini va ichki tuzilmani oshkor qilishi mumkin, va
        u hujumchiga "bu yerda kutilmagan narsa bo'ldi" deb aytadi —
        ya'ni qazishni davom ettirish uchun signal.
        """
        response = tenant_a.client().get("/api/v1/children/not-a-uuid")
        assert response.status_code == 404


class TestLoginOracle:
    """
    Login "bu email qaysi bog'chalarda bor?" degan savolga javob
    BERMASLIGI kerak.

    Bu savol raqobatchi uchun ham, ijtimoiy muhandislik uchun ham
    qimmatli: bir odam ikki bog'chada ishlashi mumkin va uni bilish
    hujum yo'lini ochadi (docs/04 §5).
    """

    def test_wrong_password_never_lists_organizations(self, tenant_a, tenant_b):
        with organization_context(tenant_b.organization.id):
            User.objects.create_user(
                email=tenant_a.owner.email,
                password=PASSWORD,
                full_name="Bir xil email",
                organization=tenant_b.organization,
                role=tenant_b.role("cashier"),
                branch=tenant_b.branch,
            )

        response = APIClient().post(
            "/api/v1/auth/login",
            {"email": tenant_a.owner.email, "password": "xato-parol"},
            format="json",
        )
        assert response.status_code == 401
        assert "organizations" not in str(response.json())

    def test_unknown_and_known_email_give_the_same_answer(self, tenant_a):
        client = APIClient()
        known = client.post(
            "/api/v1/auth/login",
            {"email": tenant_a.owner.email, "password": "xato"},
            format="json",
        )
        unknown = client.post(
            "/api/v1/auth/login",
            {"email": "umuman-yoq@example.uz", "password": "xato"},
            format="json",
        )
        assert known.status_code == unknown.status_code == 401
        assert known.json() == unknown.json()

    def test_signup_does_not_reveal_an_existing_email(self, tenant_a):
        """
        Ro'yxatdan o'tish "bu email band" demasligi kerak.

        Email tashkilot ichida unikal, global emas — shuning uchun
        boshqa tenantda bor emailni "band" deb ko'rsatish o'sha
        tenantning mavjudligini oshkor qilardi (docs/03 §10.6).
        """
        response = APIClient().post(
            "/api/v1/auth/signup",
            {
                "organization_name": "Yangi Bog'cha",
                "contact_email": tenant_a.owner.email,
                "full_name": "Yangi Egasi",
                "password": PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 201


class TestTenantEscape:
    def test_organization_id_in_the_body_is_ignored(self, tenant_a, tenant_b):
        """
        So'rov tanasidagi `organization_id` E'TIBORGA OLINMAYDI.

        Tashkilot HAR DOIM tokendan olinadi. Aks holda bu eng oddiy
        IDOR bo'lardi: bitta maydonni o'zgartirib, boshqa mijozning
        ma'lumotiga yozish (docs/04 §1).
        """
        response = tenant_a.client().post(
            "/api/v1/tariffs",
            {
                "name": "Sinov",
                "amount": "1000000",
                "organization": str(tenant_b.organization.id),
                "organization_id": str(tenant_b.organization.id),
            },
            format="json",
        )
        assert response.status_code == 201

        from apps.finance.models import TariffPlan

        with organization_context(tenant_a.organization.id):
            tariff = TariffPlan.objects.get(pk=response.json()["data"]["id"])
            assert tariff.organization_id == tenant_a.organization.id

    def test_branch_filter_cannot_reach_another_tenant(self, tenant_a, tenant_b):
        """
        `?branch=` boshqa tashkilotning filialiga ishora qilsa — bo'sh
        natija, xato emas.

        Bo'sh natija to'g'ri javob: queryset allaqachon tashkilot bilan
        cheklangan, ya'ni begona filial ID'si shunchaki hech narsaga
        mos kelmaydi. Xato qaytarish esa "bunday filial bor" deb
        aytardi.
        """
        _child(tenant_a, "Ozimniki")
        response = tenant_a.client().get("/api/v1/children", {"branch": str(tenant_b.branch.id)})
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_a_forged_token_organization_is_rejected(self, tenant_a, tenant_b):
        """
        Tokendagi tashkilotni almashtirish ishlamaydi.

        Token imzolangan, ya'ni uni o'zgartirish imkonsiz. Lekin agar
        imzo kaliti sizib chiqsa ham, foydalanuvchi ko'rsatilgan
        tashkilotda topilmaydi va so'rov `401` oladi — himoya bir
        emas, ikki qavatli (apps/core/authentication.py).
        """
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken()
        token["user_id"] = str(tenant_a.owner.id)
        token["organization_id"] = str(tenant_b.organization.id)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        assert client.get("/api/v1/children").status_code == 401

    def test_token_without_an_organization_is_rejected(self, tenant_a):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken()
        token["user_id"] = str(tenant_a.owner.id)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        assert client.get("/api/v1/children").status_code == 401

    def test_ordering_parameter_cannot_leak_across_tenants(self, tenant_a, tenant_b):
        """
        Tartiblash parametri ham chegaradan o'tolmaydi.

        Filtrlash va tartiblash backend'lari querysetdan KEYIN
        qo'llanadi, ya'ni ular allaqachon cheklangan to'plam ustida
        ishlaydi.
        """
        _child(tenant_b, "Begona")
        response = tenant_a.client().get("/api/v1/children", {"ordering": "-created_at"})
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_search_cannot_reach_another_tenant(self, tenant_a, tenant_b):
        _child(tenant_b, "Begona")
        response = tenant_a.client().get("/api/v1/children", {"search": "Begona"})
        assert response.json()["data"] == []


class TestPrivilegeEscalation:
    def test_a_cashier_cannot_grant_themselves_a_role(self, tenant_a):
        """
        Kassir o'z rolini o'zgartira olmaydi.

        Aks holda eng past huquqli hisob bir so'rov bilan eng yuqorisiga
        aylanardi va RBAC'ning ma'nosi qolmasdi.
        """
        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="kassir-eskalatsiya@alfa.uz",
                password=PASSWORD,
                full_name="Kassir",
                organization=tenant_a.organization,
                role=tenant_a.role("cashier"),
                branch=tenant_a.branch,
            )
            owner_role = tenant_a.role("org_owner")
            tokens = issue_token_pair(cashier)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = client.patch(
            f"/api/v1/users/{cashier.id}",
            {"role_id": str(owner_role.id)},
            format="json",
        )
        assert response.status_code in (403, 404)

        with organization_context(tenant_a.organization.id):
            cashier.refresh_from_db()
            assert cashier.role.code == "cashier"

    def test_a_user_cannot_be_moved_to_another_organization(self, tenant_a, tenant_b):
        """
        `organization_id` o'zgarmas — buni DB trigger ta'minlaydi.

        Foydalanuvchini boshqa tashkilotga ko'chirish, keyin qaytarish —
        ma'lumot o'g'irlashning eng oddiy yo'li bo'lardi.
        """
        from django.db import IntegrityError, transaction

        with organization_context(tenant_a.organization.id):
            user = tenant_a.owner
            with pytest.raises(IntegrityError), transaction.atomic():
                User.auth_objects.filter(pk=user.pk).update(
                    organization_id=tenant_b.organization.id
                )


class TestMoneyBoundaries:
    def test_a_payment_cannot_be_attached_to_another_tenants_invoice(self, tenant_a, tenant_b):
        """
        Begona hisob-fakturaga to'lov yozib bo'lmaydi.

        Bu nafaqat sizib chiqish, balki boshqa mijozning moliyaviy
        holatini BUZISH yo'li bo'lardi.
        """
        from apps.finance.models import TariffPlan

        with organization_context(tenant_b.organization.id):
            tariff = TariffPlan.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                name="Begona tarif",
                amount=Decimal("1000000"),
            )
            child_b = Child.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                first_name="Begona",
                last_name="Bola",
                date_of_birth=date(2021, 1, 1),
                gender="male",
                tariff=tariff,
            )
            foreign_invoice = finance.issue_invoice(child=child_b, period_year=2026, period_month=7)

        child_a = _child(tenant_a, "Ozimniki")
        response = tenant_a.client().post(
            "/api/v1/payments",
            {
                "child_id": str(child_a.id),
                "invoice_id": str(foreign_invoice.id),
                "amount": "100000",
                "method": "cash",
            },
            format="json",
        )
        assert response.status_code == 400

        with organization_context(tenant_b.organization.id):
            foreign_invoice.refresh_from_db()
            assert foreign_invoice.amount_paid == Decimal("0.00")

    def test_ledger_cannot_be_written_through_the_api(self, tenant_a):
        """
        Ledger'ga API orqali yozib bo'lmaydi (D3).

        Balans faqat servis qatlami orqali o'zgaradi; to'g'ridan-to'g'ri
        yozish imkoniyati butun moliyaviy modelni bekor qilardi.
        """
        child = _child(tenant_a)
        response = tenant_a.client().post(
            "/api/v1/ledger",
            {"child_id": str(child.id), "amount": "1000000", "direction": "credit"},
            format="json",
        )
        assert response.status_code == 405
