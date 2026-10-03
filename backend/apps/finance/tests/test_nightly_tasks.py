"""
Tungi vazifalar — hech kim kuzatmaydigan, lekin pul yozadigan kod.

Ular servislarning yupqa o'ramlari, lekin ikkita narsa FAQAT shu yerda:
tenantlar bo'ylab sikl va bitta mijozning xatosi qolganlarini
to'xtatmasligi. 7-bo'lim (≥90 % qamrov) o'lchovida bu fayllar 0 % edi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _child_with_tariff(tenant) -> None:
    from apps.children.models import Child
    from apps.finance.models import TariffPlan

    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="T",
            amount=Decimal("1000000"),
        )
        Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2022, 1, 1),
            gender="male",
            tariff=tariff,
            enrolled_on=date(2026, 8, 1),
        )


class TestInvoiceGeneration:
    def test_every_organization_gets_its_invoices(self, tenant_a, tenant_b):
        from apps.finance.tasks import generate_monthly_invoices_task

        _child_with_tariff(tenant_a)
        _child_with_tariff(tenant_b)
        results = generate_monthly_invoices_task(period_year=2026, period_month=9)
        created = {row["organization"]: row["created"] for row in results}
        assert created[tenant_a.organization.slug] == 1
        assert created[tenant_b.organization.slug] == 1

    def test_one_broken_organization_does_not_stop_the_others(
        self, tenant_a, tenant_b, monkeypatch
    ):
        from apps.finance import services
        from apps.finance.tasks import generate_monthly_invoices_task

        _child_with_tariff(tenant_a)
        _child_with_tariff(tenant_b)
        real = services.generate_monthly_invoices

        def flaky(*, organization, **kwargs):  # type: ignore[no-untyped-def]
            if organization.id == tenant_a.organization.id:
                raise RuntimeError("bitta mijozdagi nosozlik")
            return real(organization=organization, **kwargs)

        monkeypatch.setattr(services, "generate_monthly_invoices", flaky)
        results = {
            row["organization"]: row
            for row in generate_monthly_invoices_task(period_year=2026, period_month=9)
        }
        assert results[tenant_a.organization.slug]["error"] is True
        assert results[tenant_b.organization.slug]["created"] == 1

    def test_overdue_marking_runs_across_organizations(self, tenant_a):
        from apps.finance.models import Invoice
        from apps.finance.tasks import generate_monthly_invoices_task, mark_overdue_invoices_task

        _child_with_tariff(tenant_a)
        generate_monthly_invoices_task(period_year=2026, period_month=8)
        assert mark_overdue_invoices_task() >= 1
        with organization_context(tenant_a.organization.id):
            assert Invoice.objects.filter(status="overdue").count() == 1


class TestSubscriptionJobs:
    def test_the_daily_peak_is_measured_for_every_subscription(self, tenant_a, tenant_b):
        from apps.subscriptions.models import UsageSnapshot
        from apps.subscriptions.tasks import record_daily_peak

        assert record_daily_peak()["measured"] == 2
        with organization_context(tenant_a.organization.id):
            assert UsageSnapshot.objects.exists()

    def test_an_ended_period_is_closed_invoiced_and_rolled(self, tenant_a):
        from apps.subscriptions.models import Subscription, SubscriptionInvoice
        from apps.subscriptions.tasks import close_periods_and_invoice

        today = timezone.localdate()
        with organization_context(tenant_a.organization.id):
            Subscription.objects.filter(organization=tenant_a.organization).update(
                status="active",
                current_period_start=today - timedelta(days=31),
                current_period_end=today - timedelta(days=1),
            )
        assert close_periods_and_invoice() == {"closed": 1, "invoiced": 1}
        with organization_context(tenant_a.organization.id):
            subscription = Subscription.objects.get(organization=tenant_a.organization)
            assert subscription.current_period_start == today
            assert SubscriptionInvoice.objects.count() == 1

    def test_a_trial_is_not_closed_early(self, tenant_a):
        from apps.subscriptions.tasks import close_periods_and_invoice

        assert close_periods_and_invoice() == {"closed": 0, "invoiced": 0}

    def test_trial_expiry_and_dunning_return_their_counts(self, tenant_a):
        from apps.subscriptions.tasks import dunning_task, expire_trials_task

        assert expire_trials_task() == 0
        assert dunning_task() == {"past_due": 0, "suspended": 0}
