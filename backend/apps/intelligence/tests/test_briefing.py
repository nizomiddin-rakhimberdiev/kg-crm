"""
Brifing va uchidan-uchiga generatsiya (docs/07 §11, Appendix B).

Ikki savol: (1) "davomat to'liq" faqat HAR BIR bola yozilganda
yashilmi? (2) haqiqiy fakturalardan haqiqiy `payment_delay` qatori
chiqadimi — bu selektor + qoida + reconcile'ning birgalikdagi testi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.attendance import services as attendance
from apps.children import services as children
from apps.children.models import Child, Group
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan
from apps.intelligence import selectors, services
from apps.intelligence.models import Insight, InsightStatus

pytestmark = pytest.mark.django_db

MONDAY = date(2026, 9, 14)
SUNDAY = date(2026, 9, 13)


def _group(tenant, name="Quyosh", capacity=30) -> Group:
    return Group.objects.create(
        organization=tenant.organization, branch=tenant.branch, name=name, capacity=capacity
    )


def _child(tenant, name: str, group: Group | None = None, tariff=None) -> Child:
    child = Child.objects.create(
        organization=tenant.organization,
        branch=tenant.branch,
        first_name=name,
        last_name="Test",
        date_of_birth=date(2021, 5, 1),
        gender="female",
        tariff=tariff,
    )
    if group is not None:
        children.enroll_child(child=child, group=group, start_date=date(2026, 1, 12))
    return child


class TestAttendanceCompleteness:
    def test_complete_only_when_every_child_recorded(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            group = _group(tenant_a)
            kids = [_child(tenant_a, f"B{i}", group) for i in range(3)]

            # Guruhda "bitta yozuv bor" — lekin to'liq EMAS.
            attendance.mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=MONDAY,
                records=[{"child_id": kids[0].id, "status": "present"}],
            )
            check = selectors.attendance_completeness(branch_id=tenant_a.branch.id, day=MONDAY)
            assert check == {"expected": 3, "recorded": 1, "percent": 33, "complete": False}

            attendance.mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=MONDAY,
                records=[{"child_id": k.id, "status": "absent"} for k in kids[1:]],
            )
            check = selectors.attendance_completeness(branch_id=tenant_a.branch.id, day=MONDAY)
            assert check is not None and check["complete"] and check["recorded"] == 3

    def test_hidden_on_non_working_day(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _child(tenant_a, "A", _group(tenant_a))
            assert (
                selectors.attendance_completeness(branch_id=tenant_a.branch.id, day=SUNDAY) is None
            )

    def test_hidden_without_enrolled_children(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _child(tenant_a, "Guruhsiz")  # ro'yxatda bor, guruhda yo'q
            assert (
                selectors.attendance_completeness(branch_id=tenant_a.branch.id, day=MONDAY) is None
            )

    def test_children_of_other_branch_not_expected(self, tenant_a, tenant_b):
        with organization_context(tenant_b.organization.id):
            _child(tenant_b, "Begona", _group(tenant_b))
        with organization_context(tenant_a.organization.id):
            assert (
                selectors.attendance_completeness(branch_id=tenant_a.branch.id, day=MONDAY) is None
            )


class TestGenerateForBranch:
    def _tariff(self, tenant) -> TariffPlan:
        return TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Standart",
            amount=Decimal("1500000"),
        )

    def test_real_overdue_invoices_produce_payment_delay(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            tariff = self._tariff(tenant_a)
            group = _group(tenant_a)
            late = _child(tenant_a, "Kech", group, tariff)
            fresh = _child(tenant_a, "Yaqin", group, tariff)
            paid = _child(tenant_a, "To'lagan", group, tariff)
            as_of = date(2026, 9, 17)

            # 40 kun kechikkan — `status` hali `issued` (beat ishlamagan): qoida sanaga qaraydi.
            finance.issue_invoice(
                child=late,
                period_year=2026,
                period_month=8,
                issued_date=date(2026, 8, 1),
                due_date=as_of - timedelta(days=40),
            )
            # 10 kun — chegaradan (15) past.
            finance.issue_invoice(
                child=fresh,
                period_year=2026,
                period_month=9,
                issued_date=date(2026, 9, 1),
                due_date=as_of - timedelta(days=10),
            )
            # Eski, lekin to'langan.
            inv = finance.issue_invoice(
                child=paid,
                period_year=2026,
                period_month=8,
                issued_date=date(2026, 8, 1),
                due_date=as_of - timedelta(days=40),
            )
            finance.record_payment(child=paid, amount=inv.amount_due, method="cash")

            result = services.generate_for_branch(
                organization=tenant_a.organization, branch_id=tenant_a.branch.id, as_of=as_of
            )
            assert result.created == 1
            row = Insight.objects.get(type="payment_delay")
            assert row.status == InsightStatus.NEW
            assert row.subject_id == tenant_a.branch.id
            ev = row.evidence
            assert ev["children_count"] == 1
            assert ev["active_children"] == 3
            assert ev["max_days_overdue"] == 40
            assert ev["children"][0]["child_id"] == str(late.id)
            assert ev["children"][0]["group_id"] == str(group.id)
            assert Decimal(ev["total_overdue"]) == Decimal("1500000.00")

            # Qayta yuritish — bir xil qator, yangi emas.
            again = services.generate_for_branch(
                organization=tenant_a.organization, branch_id=tenant_a.branch.id, as_of=as_of
            )
            assert again.created == 0 and again.refreshed == 1
            assert Insight.objects.count() == 1

    def test_paying_off_closes_the_insight(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            tariff = self._tariff(tenant_a)
            child = _child(tenant_a, "Kech", _group(tenant_a), tariff)
            as_of = date(2026, 9, 17)
            inv = finance.issue_invoice(
                child=child,
                period_year=2026,
                period_month=8,
                issued_date=date(2026, 8, 1),
                due_date=as_of - timedelta(days=30),
            )
            gen = lambda: services.generate_for_branch(  # noqa: E731
                organization=tenant_a.organization, branch_id=tenant_a.branch.id, as_of=as_of
            )
            assert gen().created == 1
            finance.record_payment(child=child, amount=inv.amount_due, method="cash")
            assert gen().auto_resolved == 1
            assert Insight.objects.get().status == InsightStatus.AUTO_RESOLVED

    def test_no_debt_means_no_row(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _child(tenant_a, "Toza", _group(tenant_a), self._tariff(tenant_a))
            result = services.generate_for_branch(
                organization=tenant_a.organization, branch_id=tenant_a.branch.id
            )
            assert result.as_dict() == {
                "created": 0,
                "refreshed": 0,
                "auto_resolved": 0,
                "suppressed": 0,
                "episodes_ended": 0,
            }
            assert not Insight.objects.exists()


class TestTask:
    def test_task_walks_every_organization(self, tenant_a, tenant_b):
        from apps.intelligence.tasks import generate_insights

        for tenant in (tenant_a, tenant_b):
            with organization_context(tenant.organization.id):
                tariff = (
                    self._tariff(tenant)
                    if hasattr(self, "_tariff")
                    else TariffPlan.objects.create(
                        organization=tenant.organization,
                        branch=tenant.branch,
                        name="T",
                        amount=Decimal("1000000"),
                    )
                )
                child = _child(tenant, "Qarzdor", _group(tenant), tariff)
                finance.issue_invoice(
                    child=child,
                    period_year=2026,
                    period_month=7,
                    issued_date=date(2026, 7, 1),
                    due_date=timezone.localdate() - timedelta(days=30),
                )

        totals = generate_insights()
        assert totals["organizations"] == 2 and totals["created"] == 2
        for tenant in (tenant_a, tenant_b):
            with organization_context(tenant.organization.id):
                assert Insight.objects.filter(status=InsightStatus.NEW).count() == 1
