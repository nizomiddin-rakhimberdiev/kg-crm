"""
Bola holati va arxivi — PLAN 2.1, 2.2 (Q5, Q6).

Auditda ikkita bo'shliq bor edi:
  * holatni o'zgartirganda na sana, na sabab so'ralardi — keyin
    "qachondan buyon?" degan savolga javob yo'q edi;
  * yagona vosita `is_active=False` bo'lib, u "o'chirilgan" degani
    ham, "arxivlangan" degani ham bo'lishi mumkin edi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.children import services
from apps.children.models import Child, EnrollmentStatus
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


@pytest.fixture
def tariff(tenant_a) -> TariffPlan:
    with organization_context(tenant_a.organization.id):
        return TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )


@pytest.fixture
def child(tenant_a, tariff) -> Child:
    with organization_context(tenant_a.organization.id):
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Robiya",
            last_name="Ibragimova",
            date_of_birth=date(2021, 3, 14),
            gender="female",
            tariff=tariff,
            enrolled_on=date(2026, 1, 15),
        )


class TestStatusChange:
    def test_the_date_and_the_reason_are_recorded(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            services.change_status(
                child=child,
                status=EnrollmentStatus.WITHDRAWN,
                on_date=date(2026, 9, 20),
                reason="Oila boshqa shaharga koʻchdi",
            )
            child.refresh_from_db()

        assert child.enrollment_status == EnrollmentStatus.WITHDRAWN
        assert child.status_changed_on == date(2026, 9, 20)
        assert child.status_reason == "Oila boshqa shaharga koʻchdi"

    def test_a_reason_is_required(self, tenant_a, child):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="sabab"),
        ):
            services.change_status(
                child=child,
                status=EnrollmentStatus.WITHDRAWN,
                on_date=date(2026, 9, 20),
                reason="   ",
            )

    def test_the_date_cannot_be_in_the_future(self, tenant_a, child):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="kelajakda"),
        ):
            services.change_status(
                child=child,
                status=EnrollmentStatus.WITHDRAWN,
                on_date=timezone.localdate() + timedelta(days=1),
                reason="Ketdi",
            )


class TestBillingAfterLeaving:
    def test_no_invoice_after_the_month_the_child_left(self, tenant_a, child):
        """Q5: shu sanadan keyin faktura yozilmaydi."""
        with organization_context(tenant_a.organization.id):
            services.change_status(
                child=child,
                status=EnrollmentStatus.WITHDRAWN,
                on_date=date(2026, 9, 20),
                reason="Ketdi",
            )
            assert not services.is_billable_for(child, period_year=2026, period_month=10)

    def test_the_month_the_child_left_is_still_billed(self, tenant_a, child):
        """
        Oy o'rtasida ketgan bolaga o'sha oy uchun hujjat yoziladi: u
        oyning bir qismida bog'chada bo'lgan. Pulni qaytarish —
        ALOHIDA qaror (Q5), tizimning taxmini emas.
        """
        with organization_context(tenant_a.organization.id):
            services.change_status(
                child=child,
                status=EnrollmentStatus.WITHDRAWN,
                on_date=date(2026, 9, 20),
                reason="Ketdi",
            )
            assert services.is_billable_for(child, period_year=2026, period_month=9)

    def test_an_active_child_is_always_billable(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            assert services.is_billable_for(child, period_year=2026, period_month=10)

    def test_the_generation_run_skips_an_archived_child(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            services.archive_child(child=child)
            preview = finance.preview_monthly_invoices(
                organization=tenant_a.organization, period_year=2026, period_month=10
            )
        assert preview.will_create == 0


class TestArchive:
    def test_archiving_keeps_the_money_history(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            invoice = finance.issue_invoice(child=child, period_year=2026, period_month=9)
            services.archive_child(child=child)
            child.refresh_from_db()

            assert child.archived_at is not None
            assert not child.is_active
            # Hujjat joyida: u bog'chaning moliyaviy tarixi.
            invoice.refresh_from_db()
            assert invoice.child_id == child.id

    def test_restoring_undoes_an_accidental_archive(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            services.archive_child(child=child)
            services.restore_child(child=child)
            child.refresh_from_db()

        assert child.archived_at is None
        assert child.is_active

    def test_archiving_twice_is_harmless(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            services.archive_child(child=child)
            first = Child.objects.get(pk=child.pk).archived_at
            services.archive_child(child=child)
            assert Child.objects.get(pk=child.pk).archived_at == first


class TestHardDelete:
    def test_a_fresh_mistake_can_be_deleted(self, tenant_a, child):
        """Q6: "TEST Sinov" deb yozib yuborilgan yozuvni abadiy saqlash toʻgʻri emas."""
        with organization_context(tenant_a.organization.id):
            assert services.deletion_blockers(child) == []
            services.delete_child(child=child)
            assert not Child.objects.filter(pk=child.pk).exists()

    def test_a_child_with_money_cannot_be_deleted(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            finance.issue_invoice(child=child, period_year=2026, period_month=9)
            blockers = services.deletion_blockers(child)

            assert blockers
            with pytest.raises(BusinessRuleViolation, match="ARXIVGA"):
                services.delete_child(child=child)

    def test_an_old_record_cannot_be_deleted(self, tenant_a, child):
        """24 soatdan keyin faqat arxiv qoladi."""
        with organization_context(tenant_a.organization.id):
            Child.objects.filter(pk=child.pk).update(
                created_at=timezone.now() - timedelta(hours=25)
            )
            child.refresh_from_db()
            assert "24 soatdan eski yozuv" in " ".join(services.deletion_blockers(child))


class TestEndpoints:
    def test_change_status_requires_a_reason(self, tenant_a, child):
        response = tenant_a.client().post(
            reverse("v1:child-change-status", args=[child.id]),
            {"enrollment_status": "withdrawn", "status_changed_on": "2026-09-20"},
            format="json",
        )
        assert response.status_code == 400
        assert "status_reason" in str(response.data)

    def test_delete_archives_instead_of_removing(self, tenant_a, child):
        """`DELETE` = arxiv (Q6): bolalar hech qachon fizik oʻchirilmaydi."""
        response = tenant_a.client().delete(reverse("v1:child-detail", args=[child.id]))
        assert response.status_code == 204

        with organization_context(tenant_a.organization.id):
            child.refresh_from_db()
            assert child.archived_at is not None

    def test_another_tenant_cannot_change_the_status(self, tenant_a, tenant_b, child):
        response = tenant_b.client().post(
            reverse("v1:child-change-status", args=[child.id]),
            {
                "enrollment_status": "withdrawn",
                "status_changed_on": "2026-09-20",
                "status_reason": "Begona",
            },
            format="json",
        )
        assert response.status_code == 404


class TestSearchKey:
    """
    Qidiruv kaliti — Q11, PLAN 2.7.

    Mudira bolani qaysi alifboda yozsa ham topishi kerak. Topa olmasa,
    u "bu bola tizimda yoʻq" deb ikkinchi marta kiritadi — va bitta
    bola ikkita balansda qoladi.
    """

    @pytest.fixture
    def ulugbek(self, tenant_a, tariff) -> Child:
        with organization_context(tenant_a.organization.id):
            return Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Ulugʻbek",
                last_name="Choriyev",
                date_of_birth=date(2021, 3, 14),
                gender="male",
                tariff=tariff,
            )

    def test_the_key_is_filled_on_save(self, tenant_a, ulugbek):
        with organization_context(tenant_a.organization.id):
            ulugbek.refresh_from_db()
        assert ulugbek.search_key == "choriyevulugbek"

    @pytest.mark.parametrize("term", ["Ulugʻbek", "Ulugʻbek", "Улугбек", "ulugbek", "CHORIYEV"])
    def test_every_spelling_finds_the_child(self, tenant_a, ulugbek, term):
        response = tenant_a.client().get(reverse("v1:child-list"), {"q": term})
        assert response.status_code == 200
        names = [row["first_name"] for row in response.json()["data"]]
        assert "Ulugʻbek" in names, f"{term!r} boʻyicha topilmadi"

    def test_a_guardian_is_found_by_phone(self, tenant_a):
        from apps.children.models import Guardian

        with organization_context(tenant_a.organization.id):
            guardian = Guardian.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Dilnoza",
                last_name="Choriyeva",
                phone="+998901234567",
            )
            guardian.refresh_from_db()

        # Mudira ko'pincha ota-onani RAQAMI bo'yicha qidiradi.
        assert "998901234567" in guardian.search_key

    def test_the_key_follows_a_rename(self, tenant_a, ulugbek):
        with organization_context(tenant_a.organization.id):
            ulugbek.first_name = "Bekzod"
            ulugbek.save()
            ulugbek.refresh_from_db()

        assert ulugbek.search_key == "choriyevbekzod"


class TestGuardianLink:
    """Vasiy bogʻlanishini tahrirlash va uzish — PLAN 2.1."""

    @pytest.fixture
    def linked(self, tenant_a, child):
        response = tenant_a.client().post(
            reverse("v1:child-add-guardian", args=[child.id]),
            {
                "phone": "+998901234567",
                "first_name": "Dilnoza",
                "last_name": "Ibragimova",
                "relation": "mother",
                "is_primary": True,
            },
            format="json",
        )
        assert response.status_code == 201
        return response.data["id"]

    def test_the_relation_can_be_corrected(self, tenant_a, child, linked):
        response = tenant_a.client().patch(
            reverse("v1:child-guardian-link", args=[child.id, linked]),
            {"relation": "guardian"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["relation"] == "guardian"

    def test_only_one_guardian_stays_primary(self, tenant_a, child, linked):
        """Asosiy vasiy bitta: aks holda SMS kimga ketishi noaniq."""
        created = tenant_a.client().post(
            reverse("v1:child-add-guardian", args=[child.id]),
            {"phone": "+998901234568", "first_name": "Akmal", "last_name": "Ibragimov"},
            format="json",
        )
        assert created.status_code == 201, created.data
        second = created.data["id"]

        patched = tenant_a.client().patch(
            reverse("v1:child-guardian-link", args=[child.id, second]),
            {"is_primary": True},
            format="json",
        )
        assert patched.status_code == 200, patched.data

        with organization_context(tenant_a.organization.id):
            primaries = child.guardian_links.filter(is_primary=True)
            assert primaries.count() == 1
            assert str(primaries.first().id) == second

    def test_unlinking_keeps_the_guardian(self, tenant_a, child, linked):
        """Vasiy boshqa bolaning ham vasiysi boʻlishi mumkin."""
        from apps.children.models import Guardian

        response = tenant_a.client().delete(
            reverse("v1:child-guardian-link", args=[child.id, linked])
        )
        assert response.status_code == 204

        with organization_context(tenant_a.organization.id):
            assert not child.guardian_links.exists()
            assert Guardian.objects.filter(phone="+998901234567").exists()

    def test_another_tenant_cannot_touch_the_link(self, tenant_a, tenant_b, child, linked):
        response = tenant_b.client().delete(
            reverse("v1:child-guardian-link", args=[child.id, linked])
        )
        assert response.status_code == 404
