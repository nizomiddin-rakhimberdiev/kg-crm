"""
Tashkilotni o'chirish testlari (docs/03 §7, §21).

Bu — qaytarib bo'lmaydigan amal, shuning uchun testlar avvalo uning
**bajarilmasligini** tekshiradi: noto'g'ri tasdiq, faol tashkilot,
tugamagan eksport oynasi.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context, platform_context
from apps.organizations.models import Organization
from apps.platform.purge import DERIVED_PURGE, PURGE_ORDER, purge_organization

pytestmark = pytest.mark.django_db


def _prepare(tenant, *, cancelled: bool = True) -> None:
    """Tashkilotni o'chirishga tayyorlaydi: ma'lumot + bekor qilingan holat."""
    with organization_context(tenant.organization.id):
        Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )
    if cancelled:
        with platform_context():
            Organization.objects.filter(pk=tenant.organization.id).update(
                is_active=False, updated_at=timezone.now() - timedelta(days=45)
            )


class TestGuards:
    def test_wrong_confirmation_is_refused(self, tenant_a):
        _prepare(tenant_a)
        with pytest.raises(BusinessRuleViolation, match="Tasdiq"):
            purge_organization(organization_id=tenant_a.organization.id, confirm_slug="xato")

    def test_active_organization_is_refused(self, tenant_a):
        """
        Faol tashkilotni o'chirib bo'lmaydi.

        Avval obuna bekor qilinishi kerak — ya'ni tijorat qarori
        texnik amaldan OLDIN keladi.
        """
        _prepare(tenant_a, cancelled=False)
        with pytest.raises(BusinessRuleViolation, match="Faol tashkilotni"):
            purge_organization(
                organization_id=tenant_a.organization.id,
                confirm_slug=tenant_a.organization.slug,
            )

    def test_export_window_is_respected(self, tenant_a):
        """
        Eksport oynasi tugamaguncha o'chirilmaydi.

        Mijoz ketgan bo'lsa ham uning ma'lumoti unga tegishli va u
        30 kun davomida yuklab olish huquqiga ega (docs/01 §4.4).
        """
        _prepare(tenant_a, cancelled=False)
        with platform_context():
            Organization.objects.filter(pk=tenant_a.organization.id).update(is_active=False)

        with pytest.raises(BusinessRuleViolation, match="Eksport oynasi"):
            purge_organization(
                organization_id=tenant_a.organization.id,
                confirm_slug=tenant_a.organization.slug,
            )


class TestPurge:
    def test_everything_is_deleted_in_the_right_order(self, tenant_a, tenant_b):
        _prepare(tenant_a)
        organization_id = tenant_a.organization.id
        slug = tenant_a.organization.slug

        deleted = purge_organization(organization_id=organization_id, confirm_slug=slug)

        assert deleted["organization"] == 1
        assert deleted.get("child") == 1
        with platform_context():
            assert not Organization.objects.filter(pk=organization_id).exists()

    def test_an_organization_with_audit_rows_can_be_purged(self, tenant_a):
        """
        Audit qatorlari bor tashkilot ham o'chirilishi kerak.

        Bu holat AMALDA har doim yuz beradi: har bir kirish, har bir
        yozuv audit jurnaliga tushadi, ya'ni haqiqiy mijozda o'nlab
        yoki minglab qator bo'ladi. Test esa audit qatorsiz tashkilot
        bilan ishlagan — shuning uchun u yashil turaverdi.

        Xato: `audit_log` PLATFORMA rejimida o'chirilardi, u yerda esa
        siyosat faqat `organization_id IS NULL` qatorlarni ochadi
        (ADR-10 — vendor mijozning audit yozuvlarini ko'rmaydi). Ya'ni
        `DELETE` hech narsa topmasdi, xato bermasdi, va oxirida
        `organization.delete()` FK cheklovi bilan yiqilardi.
        """
        from apps.audit.models import AuditLog

        _prepare(tenant_a)
        organization_id = tenant_a.organization.id

        with organization_context(organization_id):
            for index in range(3):
                AuditLog.objects.create(
                    organization=tenant_a.organization,
                    actor=tenant_a.owner,
                    actor_email=tenant_a.owner.email,
                    action="update",
                    entity_type="child",
                    changes={"n": index},
                )
            assert AuditLog.objects.count() >= 3

        deleted = purge_organization(
            organization_id=organization_id, confirm_slug=tenant_a.organization.slug
        )

        assert deleted["audit_log"] >= 3, "mijozning audit qatorlari o'chirilmadi"
        with platform_context():
            assert not Organization.objects.filter(pk=organization_id).exists()

    def test_the_other_tenant_is_untouched(self, tenant_a, tenant_b):
        """
        O'chirish FAQAT bitta tashkilotga tegadi.

        Bu eng qo'rqinchli xato bo'lardi: bitta mijozni o'chirishda
        boshqasining ma'lumoti ham ketishi. RLS bu yerda ham ishlaydi —
        so'rovlar tashkilot kontekstida bajariladi.
        """
        _prepare(tenant_a)
        _prepare(tenant_b, cancelled=False)

        purge_organization(
            organization_id=tenant_a.organization.id, confirm_slug=tenant_a.organization.slug
        )

        with organization_context(tenant_b.organization.id):
            assert Child.objects.count() == 1
        with platform_context():
            assert Organization.objects.filter(pk=tenant_b.organization.id).exists()

    def test_the_deletion_itself_leaves_a_record(self, tenant_a):
        """
        O'chirish ham hodisa — u ham yozuv qoldiradi.

        Mijozning audit qatorlari o'chiriladi (ular ham shaxsiy
        ma'lumot), lekin O'CHIRISH FAKTI platforma tekisligida qoladi.
        """
        from apps.audit.models import AuditLog

        slug = tenant_a.organization.slug
        _prepare(tenant_a)
        purge_organization(organization_id=tenant_a.organization.id, confirm_slug=slug)

        with platform_context():
            entry = AuditLog.objects.filter(
                action="delete", entity_type="organization", organization__isnull=True
            ).first()
        assert entry is not None
        assert entry.changes["slug"] == slug
        assert entry.changes["deleted_rows"]["child"] == 1

    def test_force_skips_the_export_window(self, tenant_a):
        """`force` — sud qarori yoki GDPR talabi uchun; jurnalda ko'rinadi."""
        from apps.audit.models import AuditLog

        _prepare(tenant_a, cancelled=False)
        purge_organization(
            organization_id=tenant_a.organization.id,
            confirm_slug=tenant_a.organization.slug,
            force=True,
        )
        with platform_context():
            entry = AuditLog.objects.filter(action="delete", entity_type="organization").first()
        assert entry.changes["forced"] is True


class TestOrderIsComplete:
    def test_every_tenant_model_is_in_the_purge_order(self):
        """
        Ro'yxat modellar bilan sinxron.

        Yangi tenant model qo'shilib, bu yerga yozilmasa — o'chirish
        FK cheklovida yiqilardi yoki (yomoni) yetim qatorlar qolardi.
        """
        from django.apps import apps as django_apps

        from apps.core.models import TenantScopedModel

        listed = set()
        for path in (*PURGE_ORDER, *DERIVED_PURGE):
            module, name = path.rsplit(".", 1)
            listed.add(f"{module.split('.')[-1]}.{name}")

        # Metama'lumot va tenant bo'lmagan jadvallar bu ro'yxatda emas.
        skip = {"platform_console.SupportGrant"}
        missing = []
        for model in django_apps.get_models():
            if not issubclass(model, TenantScopedModel):
                continue
            if model._meta.db_table.startswith("test_"):
                continue
            label = f"{model._meta.app_label}.{model.__name__}"
            if label not in listed and label not in skip:
                missing.append(label)

        assert not missing, (
            f"Bu modellar `PURGE_ORDER` da yo'q: {sorted(missing)}. "
            f"Ular o'chirilmay qolardi yoki FK cheklovini buzardi."
        )
