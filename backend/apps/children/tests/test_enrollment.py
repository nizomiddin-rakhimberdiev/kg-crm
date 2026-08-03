"""Guruhga yozish qoidalari (docs/03 §11.5)."""

from __future__ import annotations

from datetime import date

import pytest

from apps.children.models import Child, Enrollment, Group
from apps.children.services import end_enrollment, enroll_child, recount_group
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def child(tenant_a) -> Child:
    with organization_context(tenant_a.organization.id):
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


@pytest.fixture
def group(tenant_a) -> Group:
    with organization_context(tenant_a.organization.id):
        return Group.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Quyoshlar",
            capacity=2,
        )


class TestEnrollment:
    def test_enroll_creates_open_enrollment(self, tenant_a, child, group):
        with organization_context(tenant_a.organization.id):
            enrollment = enroll_child(child=child, group=group)
        assert enrollment.end_date is None
        assert enrollment.status == "active"

    def test_second_enrollment_closes_the_first(self, tenant_a, child, group):
        """
        Guruhdan guruhga ko'chirishda eski a'zolik YOPILADI.

        Aks holda bola ikki guruhda bir vaqtda faol bo'lib qolardi va
        sig'im hisobi ham, davomat ham buzilardi.
        """
        with organization_context(tenant_a.organization.id):
            second_group = Group.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Yulduzlar",
                capacity=5,
            )
            first = enroll_child(child=child, group=group)
            enroll_child(child=child, group=second_group)

            first.refresh_from_db()
            open_count = Enrollment.objects.filter(
                child=child, end_date__isnull=True, status="active"
            ).count()

        assert first.end_date is not None
        assert first.status == "transferred"
        assert open_count == 1

    def test_capacity_is_enforced(self, tenant_a, group):
        with organization_context(tenant_a.organization.id):
            for index in range(2):
                kid = Child.objects.create(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    first_name=f"Bola{index}",
                    last_name="Testov",
                    date_of_birth=date(2021, 1, 1),
                    gender="male",
                )
                enroll_child(child=kid, group=group)

            overflow = Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Ortiqcha",
                last_name="Testov",
                date_of_birth=date(2021, 1, 1),
                gender="female",
            )
            with pytest.raises(BusinessRuleViolation, match="to'lgan"):
                enroll_child(child=overflow, group=group)

    def test_zero_capacity_means_unlimited(self, tenant_a, child):
        """`capacity=0` — cheklov yo'q (yangi guruh uchun default)."""
        with organization_context(tenant_a.organization.id):
            open_group = Group.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Cheksiz",
                capacity=0,
            )
            enroll_child(child=child, group=open_group)  # xato bermasligi kerak

    @pytest.mark.tenancy
    def test_cannot_enroll_into_another_tenants_group(self, tenant_a, tenant_b, child):
        with organization_context(tenant_b.organization.id):
            foreign_group = Group.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                name="Begona",
                capacity=10,
            )
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="tashkilotga"),
        ):
            enroll_child(child=child, group=foreign_group)


class TestEnrolledCountCache:
    def test_cache_tracks_enrollments(self, tenant_a, child, group):
        with organization_context(tenant_a.organization.id):
            enroll_child(child=child, group=group)
            group.refresh_from_db()
            assert group.enrolled_count == 1

            enrollment = Enrollment.objects.get(child=child, end_date__isnull=True)
            end_enrollment(enrollment=enrollment)
            group.refresh_from_db()
            assert group.enrolled_count == 0

    def test_cache_can_always_be_rebuilt(self, tenant_a, child, group):
        """
        Kesh haqiqat manbai emas (D3) — u har doim qayta hisoblanadi.

        Bu test keshni ataylab buzib, tiklanishini tekshiradi.
        """
        with organization_context(tenant_a.organization.id):
            enroll_child(child=child, group=group)
            Group.objects.filter(pk=group.pk).update(enrolled_count=999)  # buzamiz
            assert recount_group(group) == 1
            group.refresh_from_db()
            assert group.enrolled_count == 1
