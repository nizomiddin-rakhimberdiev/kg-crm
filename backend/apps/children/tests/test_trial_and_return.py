"""
Sinov muddati va qaytib kelgan bola (mijoz soʻrovi, 2026-10-28).

Mijoz bolaning yoʻlini shunday aytdi: **yangi → sinov (3 kun) → faol**,
keyin **ketdi** (sababi roʻyxatdan) va baʼzan **qaytib keldi**.

Ikkita joy pulga tegadi, va test aynan ularni qoʻriqlaydi:

* sinovdagi bolaga hisob-faktura YOZILMAYDI — uch kun kelib koʻrgan
  bola uchun oylik chiqarish bogʻchani ham, ota-onani ham ishontirmaydi;
* qaytib kelgan bola yana hisoblanadi — "ketgan" holat uning tarixida
  qolgani uchun uni qayta yozish kerak emas.

Ketish sababi erkin matn emas: bogʻcha "nega ketishyapti?" degan
savolga oylar boʻyicha javob olishi uchun roʻyxat qatʼiy, izoh esa
yoniga yoziladi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.children import services
from apps.children.models import Child, EnrollmentStatus, WithdrawReason
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


@pytest.fixture
def child(tenant_a) -> Child:
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
            first_name="Aziza",
            last_name="Safarova",
            date_of_birth=date(2021, 5, 4),
            gender="female",
            tariff=tariff,
        )


def test_a_trial_child_is_not_invoiced(tenant_a, child: Child):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        services.change_status(
            child=child,
            status=EnrollmentStatus.TRIAL,
            on_date=today,
            reason="Uch kunlik sinov",
        )
        assert not services.is_billable_for(child, period_year=today.year, period_month=today.month)


def test_the_trial_ends_three_days_later(tenant_a, child: Child):
    start = timezone.localdate() - timedelta(days=5)
    with organization_context(tenant_a.organization.id):
        services.change_status(
            child=child,
            status=EnrollmentStatus.TRIAL,
            on_date=start,
            reason="Uch kunlik sinov",
        )
        child.refresh_from_db()
        assert child.trial_until == start + timedelta(days=services.TRIAL_DAYS)
        # Besh kun oldin boshlangan sinov allaqachon tugagan — ekran buni
        # aytishi kerak, aks holda bola "sinovda" boʻlib qolib ketadi.
        assert services.trial_is_over(child)


def test_a_returned_child_is_billed_again(tenant_a, child: Child):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        services.change_status(
            child=child,
            status=EnrollmentStatus.WITHDRAWN,
            on_date=today - timedelta(days=60),
            reason="Boshqa joyga koʻchdi",
            reason_code=WithdrawReason.RELOCATION,
        )
        assert not services.is_billable_for(child, period_year=today.year, period_month=today.month)

        services.change_status(
            child=child,
            status=EnrollmentStatus.RETURNED,
            on_date=today,
            reason="Qaytib keldi",
        )
        assert services.is_billable_for(child, period_year=today.year, period_month=today.month)


def test_a_returned_child_counts_as_enrolled(tenant_a, child: Child):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        services.change_status(
            child=child,
            status=EnrollmentStatus.RETURNED,
            on_date=today,
            reason="Qaytib keldi",
        )
        assert child.enrollment_status in services.ENROLLED_STATUSES


def test_leaving_keeps_the_reason_from_the_catalogue(tenant_a, child: Child):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        services.change_status(
            child=child,
            status=EnrollmentStatus.WITHDRAWN,
            on_date=today,
            reason="Davlat bogʻchasidan joy chiqdi",
            reason_code=WithdrawReason.STATE_KINDERGARTEN,
        )
        child.refresh_from_db()
        assert child.status_reason_code == WithdrawReason.STATE_KINDERGARTEN


def test_an_unknown_reason_code_is_refused(tenant_a, child: Child):
    with organization_context(tenant_a.organization.id), pytest.raises(BusinessRuleViolation):
        services.change_status(
            child=child,
            status=EnrollmentStatus.WITHDRAWN,
            on_date=timezone.localdate(),
            reason="Sabab",
            reason_code="kosmosga_uchdi",
        )


def test_the_endpoint_accepts_the_new_statuses(tenant_a, child: Child):
    response = tenant_a.client().post(
        reverse("v1:child-change-status", args=[child.id]),
        {
            "enrollment_status": EnrollmentStatus.TRIAL,
            "status_changed_on": str(timezone.localdate()),
            "status_reason": "Uch kunlik sinov",
        },
        format="json",
    )
    assert response.status_code == 200, response.data
    assert response.data["enrollment_status"] == EnrollmentStatus.TRIAL
    assert response.data["trial_until"]
