"""
Oylik hisoblash testlari (docs/03 §14, docs/04 §11.2).

Asosiy savol: "yakunlangan hisoblash oʻzgarib qola oladimi?" — xodim
"oʻtgan oyda menga qancha hisoblangan edi?" deb so'raganda javob bir xil
bo'lishi kerak.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.hr.models import Employee, Position
from apps.payroll import services
from apps.payroll.models import PayrollItem, PayrollRun, PayrollStatus

pytestmark = pytest.mark.django_db

SALARY = Decimal("4000000.00")


@pytest.fixture
def employees(tenant_a) -> list[Employee]:
    with organization_context(tenant_a.organization.id):
        position = Position.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            title="Tarbiyachi",
        )
        return [
            Employee.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name=f"Xodim{index}",
                last_name="Testov",
                position=position,
                hire_date=date(2024, 1, 1),
                base_salary=SALARY,
            )
            for index in range(3)
        ]


@pytest.fixture
def run(tenant_a, employees) -> PayrollRun:
    with organization_context(tenant_a.organization.id):
        return services.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=7,
        )


class TestRunCreation:
    def test_populates_items_from_active_employees(self, tenant_a, run, employees):
        with organization_context(tenant_a.organization.id):
            assert PayrollItem.objects.filter(payroll_run=run).count() == 3
            assert run.total_gross == SALARY * 3
            assert run.total_net == SALARY * 3

    def test_salary_is_snapshotted_not_referenced(self, tenant_a, run, employees):
        """
        Maosh SNAPSHOT sifatida ko'chiriladi.

        Keyin maosh oshsa, o'tgan oyning hisoblashi o'zgarmasligi kerak —
        aks holda "oʻtgan oy qancha edi?" degan savolga javob vaqt o'tishi
        bilan o'zgarardi.
        """
        with organization_context(tenant_a.organization.id):
            Employee.objects.filter(pk=employees[0].pk).update(base_salary=Decimal("9000000"))
            item = PayrollItem.objects.get(payroll_run=run, employee=employees[0])
        assert item.base_amount == SALARY

    def test_duplicate_period_is_rejected(self, tenant_a, run):
        """Bir filial — bir davr — bitta hisoblash (ikki marta toʻlamaslik)."""
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="allaqachon mavjud"),
        ):
            services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=7,
            )

    def test_database_blocks_duplicate_period(self, tenant_a, run):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            PayrollRun.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=7,
            )

    def test_terminated_employees_are_excluded(self, tenant_a, employees):
        with organization_context(tenant_a.organization.id):
            Employee.objects.filter(pk=employees[0].pk).update(employment_status="terminated")
            new_run = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=8,
            )
            assert PayrollItem.objects.filter(payroll_run=new_run).count() == 2


class TestItemEditing:
    def test_bonus_and_deduction_recompute_gross_and_net(self, tenant_a, run):
        with organization_context(tenant_a.organization.id):
            item = PayrollItem.objects.filter(payroll_run=run).first()
            services.update_item(item=item, bonus=Decimal("500000"), deduction=Decimal("200000"))
            item.refresh_from_db()
            run.refresh_from_db()

        assert item.gross == Decimal("4500000.00")
        assert item.net == Decimal("4300000.00")
        assert run.total_net == SALARY * 2 + Decimal("4300000.00")

    def test_deduction_cannot_exceed_gross(self, tenant_a, run):
        """
        Sof maosh manfiy bo'lolmaydi — xodim bog'chaga qarzdor bo'lib
        qolishi oylik hisoblashda ifodalanmaydigan holat.
        """
        with organization_context(tenant_a.organization.id):
            item = PayrollItem.objects.filter(payroll_run=run).first()
            with pytest.raises(BusinessRuleViolation, match="oshib ketdi"):
                services.update_item(item=item, deduction=Decimal("99000000"))

    def test_negative_bonus_is_rejected(self, tenant_a, run):
        with organization_context(tenant_a.organization.id):
            item = PayrollItem.objects.filter(payroll_run=run).first()
            with pytest.raises(BusinessRuleViolation, match="manfiy"):
                services.update_item(item=item, bonus=Decimal("-1"))

    def test_totals_are_recomputed_not_incremented(self, tenant_a, run):
        """Yigʻindi keshi buzilsa, keyingi tahrirda tuzaladi."""
        with organization_context(tenant_a.organization.id):
            PayrollRun.objects.filter(pk=run.pk).update(total_net=Decimal("1"))
            item = PayrollItem.objects.filter(payroll_run=run).first()
            services.update_item(item=item, bonus=Decimal("0"))
            run.refresh_from_db()
        assert run.total_net == SALARY * 3


class TestStateMachine:
    def test_finalize_locks_the_run(self, tenant_a, run):
        with organization_context(tenant_a.organization.id):
            services.finalize_run(run=run)
            run.refresh_from_db()
            assert run.status == PayrollStatus.FINALIZED
            assert run.finalized_at is not None

            item = PayrollItem.objects.filter(payroll_run=run).first()
            with pytest.raises(BusinessRuleViolation, match="oʻzgartirib boʻlmaydi"):
                services.update_item(item=item, bonus=Decimal("100000"))

    def test_empty_run_cannot_be_finalized(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            empty = services.create_run(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                period_year=2026,
                period_month=9,
            )
            with pytest.raises(BusinessRuleViolation, match="Boʻsh"):
                services.finalize_run(run=empty)

    def test_double_finalize_is_rejected(self, tenant_a, run):
        with organization_context(tenant_a.organization.id):
            services.finalize_run(run=run)
            with pytest.raises(BusinessRuleViolation, match="qoralama"):
                services.finalize_run(run=run)

    def test_mark_paid_requires_finalized(self, tenant_a, run):
        """Holat tartibi bir tomonlama: draft → finalized → paid."""
        with organization_context(tenant_a.organization.id):
            with pytest.raises(BusinessRuleViolation, match="yakunlangan"):
                services.mark_run_paid(run=run)

            services.finalize_run(run=run)
            services.mark_run_paid(run=run)
            run.refresh_from_db()
        assert run.status == PayrollStatus.PAID
        assert run.paid_at is not None


class TestPayslip:
    def test_reflects_the_run_not_current_salary(self, tenant_a, run, employees):
        with organization_context(tenant_a.organization.id):
            item = PayrollItem.objects.get(payroll_run=run, employee=employees[0])
            services.update_item(item=item, bonus=Decimal("300000"), note="Qoʻshimcha smena")
            Employee.objects.filter(pk=employees[0].pk).update(base_salary=Decimal("9000000"))
            item.refresh_from_db()
            slip = services.payslip(item=item)

        assert slip["base_amount"] == "4000000.00"  # o'sha oyning maoshi
        assert slip["bonus"] == "300000.00"
        assert slip["net"] == "4300000.00"
        assert slip["note"] == "Qoʻshimcha smena"


class TestEndpoints:
    def test_full_workflow(self, tenant_a, employees):
        client = tenant_a.client()

        created = client.post(
            reverse("v1:payroll-run-list"),
            {"period_year": 2026, "period_month": 7},
            format="json",
        )
        assert created.status_code == 201
        run_id = created.json()["data"]["id"]
        item_id = created.json()["data"]["items"][0]["id"]

        edited = client.patch(
            reverse("v1:payroll-run-update-item", args=[run_id, item_id]),
            {"bonus": "500000"},
            format="json",
        )
        assert edited.status_code == 200
        assert edited.json()["data"]["net"] == "4500000.00"

        finalized = client.post(reverse("v1:payroll-run-finalize", args=[run_id]))
        assert finalized.status_code == 200
        assert finalized.json()["data"]["status"] == "finalized"

        # Yakunlangandan keyin tahrirlash rad etiladi.
        blocked = client.patch(
            reverse("v1:payroll-run-update-item", args=[run_id, item_id]),
            {"bonus": "999"},
            format="json",
        )
        assert blocked.status_code == 422

        paid = client.post(reverse("v1:payroll-run-mark-paid", args=[run_id]))
        assert paid.json()["data"]["status"] == "paid"

    def test_runs_cannot_be_patched_directly(self, tenant_a, run):
        client = tenant_a.client()
        url = reverse("v1:payroll-run-detail", args=[run.id])
        # `PATCH` marshrutda bor, lekin biznes qoidasi bilan rad etiladi (422);
        # `DELETE` esa umuman ro'yxatdan o'tmagan (405).
        assert client.patch(url, {"status": "paid"}, format="json").status_code == 422
        assert client.delete(url).status_code == 405

    def test_payslip_endpoint(self, tenant_a, run, employees):
        response = tenant_a.client().get(
            reverse("v1:payroll-run-payslip", args=[run.id, employees[0].id])
        )
        assert response.status_code == 200
        assert response.json()["data"]["net"] == "4000000.00"

    def test_cashier_cannot_access_payroll(self, tenant_a):
        """Kassirda `payroll` yoʻq (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="kassir@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Kassir",
                organization=tenant_a.organization,
                role=tenant_a.role("cashier"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(cashier)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert client.get(reverse("v1:employee-list")).status_code == 403
        assert client.get(reverse("v1:payroll-run-list")).status_code == 403


class TestEmployeeLifecycle:
    def test_employee_with_payroll_history_is_terminated_not_deleted(
        self, tenant_a, run, employees
    ):
        """
        Oylik tarixi bo'lgan xodim o'chirilmaydi — ishdan bo'shatiladi.

        O'chirilsa, o'tgan oylarning hisoblashi buzilardi; `RESTRICT` buni
        bazada ham to'sadi.
        """
        response = tenant_a.client().delete(reverse("v1:employee-detail", args=[employees[0].id]))
        assert response.status_code == 204

        with organization_context(tenant_a.organization.id):
            employees[0].refresh_from_db()
            assert employees[0].employment_status == "terminated"
            assert PayrollItem.objects.filter(employee=employees[0]).exists()
