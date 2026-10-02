"""Audit jurnali testlari (docs/02 §20.3)."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.tenancy import organization_context, platform_context

pytestmark = pytest.mark.django_db

PASSWORD = "Juda-Kuchli-Parol-2026"  # noqa: S105


class TestAuthAuditing:
    def test_opening_an_account_is_logged_for_the_customer(self):
        """
        Akkauntni vendor ochadi — va bu MIJOZNING jurnalida ko'rinadi.

        Avval bu test ochiq `/auth/signup` ni tekshirardi. Eshik vendor
        konsoliga ko'chdi, lekin talab o'zgarmadi: bog'cha o'z akkaunti
        qachon va kim tomonidan ochilganini ko'ra olishi kerak.
        """
        from apps.core.totp import generate_secret
        from apps.platform import services as platform_services
        from apps.platform.models import PlatformRole, PlatformUser

        with platform_context():
            actor = PlatformUser(
                email="admin@kg-crm.uz",
                full_name="Vendor",
                role=PlatformRole.ADMIN,
                totp_secret=generate_secret(),
                totp_confirmed_at=timezone.now(),
            )
            actor.set_password(PASSWORD)
            actor.save()

        platform_services.create_organization(
            actor=actor,
            organization_name="Audit Bogʻcha",
            contact_email="owner@audit.uz",
            full_name="Egasi",
        )

        # Yozuv TASHKILOTGA tegishli, shuning uchun uni o'sha tashkilot
        # kontekstida o'qiymiz. Platforma rejimi bu yerda yordam bermaydi
        # va bermasligi ham kerak: vendor mijozning audit qatorlarini
        # ko'rmaydi (ADR-10).
        from apps.organizations.models import Organization

        with platform_context():
            organization = Organization.objects.get(contact_email="owner@audit.uz")
        with organization_context(organization.id):
            entry = AuditLog.objects.filter(action="create", entity_type="organization").first()
            assert entry is not None
            # `entry.organization` EMAS, `organization_id`: FK'ga
            # murojaat kontekstdan tashqarida dangasa so'rov yuborardi
            # va RLS uni bo'sh qaytarardi.
            assert entry.organization_id == organization.id
        assert entry.entity_type == "organization"

    def test_successful_login_is_logged(self, api_client, tenant_a):
        api_client.post(
            reverse("v1:auth-login"),
            {"email": tenant_a.owner.email, "password": PASSWORD},
            format="json",
        )
        with organization_context(tenant_a.organization.id):
            assert AuditLog.objects.filter(action="login", actor=tenant_a.owner).exists()

    def test_failed_login_is_logged_without_actor(self, api_client):
        """
        Muvaffaqiyatsiz urinish ham yoziladi, lekin `actor` bo'sh.

        Aktyor yozilmasligi muhim: agar email mavjud bo'lmasa, uni
        foydalanuvchiga bog'lash mumkin emas, va bog'lashga urinish
        mavjudlik haqidagi ma'lumotni jurnalga olib kirardi.
        """
        api_client.post(
            reverse("v1:auth-login"),
            {"email": "yoq@example.uz", "password": "xato"},
            format="json",
        )
        # `organization` NULL — kim urinayotgani noma'lum. Bunday
        # qatorni MIJOZ ko'rmaydi (ADR-10), shuning uchun uni o'qish
        # ham kontekstsiz, filtrsiz manager orqali bo'ladi.
        with platform_context(), organization_context(None):
            entry = AuditLog.objects.filter(action="login_failed").first()
        assert entry is not None
        assert entry.actor is None
        assert entry.actor_email == "yoq@example.uz"

    def test_password_change_is_logged(self, tenant_a):
        tenant_a.client().post(
            reverse("v1:auth-password-change"),
            {"current_password": PASSWORD, "new_password": "Yangi-Kuchli-Parol-2026"},
            format="json",
        )
        # So'rov tugagach kontekst tozalanadi (P0-001) — o'qish uchun qayta ochamiz.
        with organization_context(tenant_a.organization.id):
            assert AuditLog.objects.filter(action="password_change", actor=tenant_a.owner).exists()


class TestMutationAuditing:
    def test_user_creation_is_logged(self, tenant_a):
        tenant_a.client().post(
            reverse("v1:user-list"),
            {
                "full_name": "Yangi",
                "email": "yangi@alfa.uz",
                "password": PASSWORD,
                "role_id": str(tenant_a.role("cashier").id),
                "branch_id": str(tenant_a.branch.id),
            },
            format="json",
        )
        # So'rov tugagach kontekst tozalanadi (P0-001) — o'qish uchun qayta ochamiz.
        with organization_context(tenant_a.organization.id):
            entry = AuditLog.objects.filter(action="create", entity_type="user").first()
            assert entry is not None
            assert entry.actor == tenant_a.owner
            assert entry.organization == tenant_a.organization

    def test_branch_creation_is_logged(self, tenant_a):
        tenant_a.client().post(
            reverse("v1:branch-list"), {"name": "Ikkinchi", "code": "B2"}, format="json"
        )
        # So'rov tugagach kontekst tozalanadi (P0-001) — o'qish uchun qayta ochamiz.
        with organization_context(tenant_a.organization.id):
            assert AuditLog.objects.filter(action="create", entity_type="branch").exists()

    def test_audit_captures_ip_and_user_agent(self, tenant_a):
        client = tenant_a.client()
        client.post(
            reverse("v1:branch-list"),
            {"name": "Uchinchi", "code": "B3"},
            format="json",
            HTTP_USER_AGENT="pytest-agent/1.0",
        )
        # So'rov tugagach kontekst tozalanadi (P0-001) — o'qish uchun qayta ochamiz.
        with organization_context(tenant_a.organization.id):
            entry = AuditLog.objects.filter(entity_type="branch").first()
            assert entry.user_agent == "pytest-agent/1.0"
            assert entry.ip is not None


class TestAuditImmutability:
    def test_log_has_no_updated_at(self):
        """Append-only jadvalda `updated_at`/`is_active` boʻlmasligi kerak (D3)."""
        fields = {f.name for f in AuditLog._meta.get_fields()}
        assert "updated_at" not in fields
        assert "is_active" not in fields
