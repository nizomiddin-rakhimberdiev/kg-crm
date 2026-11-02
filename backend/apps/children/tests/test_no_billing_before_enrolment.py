"""
Bola kelmagan oyga hujjat yozilmaydi (audit, 2026-10-30).

Auditda: 09.10.2026 da qabul qilingan bolaning profilida may–sentabr
uchun 0 soʻmlik fakturalar va 01.05 dan boshlab davomat yozuvlari
turardi. Sabab — hisob-faktura nomzodlari faqat holatga qarardi,
qabul SANASIGA emas: oldingi oylarga toʻliq baza yozilib, ustiga
−100% chegirma qoʻyilardi.

Natija 0 soʻm boʻlgani uchun kassaga tegmasdi, lekin hisobotdagi
yalpi baza +176 950 000 ga, "qayta hisob" esa −84 985 000 ga sunʼiy
oshgan edi — yaʼni bogʻcha oʻz tarixini notoʻgʻri koʻrardi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.children import services as children_services
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


@pytest.fixture
def child(tenant_a) -> Child:
    """09.10.2026 da qabul qilingan bola."""
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Madina",
            last_name="Nazarova",
            date_of_birth=date(2021, 5, 4),
            gender="female",
            tariff=tariff,
            enrolled_on=date(2026, 10, 9),
        )


def test_months_before_the_enrolment_are_not_billable(tenant_a, child):
    with organization_context(tenant_a.organization.id):
        for month in (5, 6, 7, 8, 9):
            assert not children_services.is_billable_for(
                child, period_year=2026, period_month=month
            ), month


def test_the_enrolment_month_is_billable(tenant_a, child):
    with organization_context(tenant_a.organization.id):
        assert children_services.is_billable_for(child, period_year=2026, period_month=10)


def test_the_preview_leaves_earlier_months_out(tenant_a, child):
    with organization_context(tenant_a.organization.id):
        preview = finance.preview_monthly_invoices(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=5,
        )
    assert all(row.full_name != child.full_name for row in preview.rows)


def test_an_invoice_before_the_enrolment_is_refused(tenant_a, child):
    with organization_context(tenant_a.organization.id), pytest.raises(BusinessRuleViolation):
        finance.issue_invoice(child=child, period_year=2026, period_month=5)


def test_attendance_before_the_enrolment_is_refused(tenant_a, child):
    from apps.attendance import services as attendance
    from apps.children.models import Enrollment, Group

    with organization_context(tenant_a.organization.id):
        group = Group.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Quyoshcha",
            capacity=20,
        )
        Enrollment.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            child=child,
            group=group,
            start_date=date(2026, 10, 9),
            status="active",
        )
        with pytest.raises(BusinessRuleViolation):
            attendance.mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=date(2026, 5, 1),
                records=[{"child_id": child.id, "status": "present"}],
                recorded_by=tenant_a.owner,
            )
