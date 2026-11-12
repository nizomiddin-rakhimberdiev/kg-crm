"""
Kassa qoldig'i — "ayni paytda qo'limizda qancha pul bor" (ADR-17).

Manba — `cash_movement`, ya'ni pul HAQIQATAN qimirlagan yozuvlar.
Shuning uchun bu raqam foyda-zarar hisobotidan farq qilishi mumkin va
bu to'g'ri: hisobot hisoblash usulida (yakunlangan oylik — xarajat),
bu esa kassa usulida (berilgan oylik — chiqim). Quyidagi testlar aynan
shu farqni qotirib qo'yadi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses import services as expense_services
from apps.expenses.models import Expense, ExpenseCategory
from apps.finance import services as finance
from apps.hr.models import Employee
from apps.payroll import services as payroll
from apps.reports import selectors

pytestmark = pytest.mark.django_db


def _child(tenant: Any) -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Kassa",
            last_name="Bolasi",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


def _expense(tenant: Any, amount: str) -> Expense:
    """Tasdiqlangan chiqim — aynan tasdiqlash pulni kassadan chiqaradi."""
    with organization_context(tenant.organization.id):
        category, _ = ExpenseCategory.objects.get_or_create(
            organization=tenant.organization, branch=tenant.branch, name="Kommunal"
        )
        expense = Expense.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            category=category,
            amount=Decimal(amount),
            expense_date=timezone.localdate(),
        )
        return expense_services.approve_expense(expense=expense, approved_by=None)


def _employee(tenant: Any, salary: str = "4000000") -> Employee:
    with organization_context(tenant.organization.id):
        return Employee.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Xodim",
            last_name="Testov",
            hire_date=date(2026, 1, 10),
            base_salary=Decimal(salary),
        )


def _position(tenant: Any) -> dict[str, Any]:
    with organization_context(tenant.organization.id):
        return selectors.cash_position(organization_id=tenant.organization.id)


def test_balance_is_money_in_minus_money_out(tenant_a: Any):
    child = _child(tenant_a)
    employee = _employee(tenant_a)

    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("10000000"), method="cash")
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=timezone.localdate().year,
            period_month=timezone.localdate().month,
        )
        payroll.finalize_run(run=run)
        payroll.pay_run(run=run)

    _expense(tenant_a, "1500000")
    # Kutilayotgan so'rov hali pul emas — tasdiqlanmagan.
    with organization_context(tenant_a.organization.id):
        category = ExpenseCategory.objects.get(name="Kommunal")
        Expense.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            amount=Decimal("9000000"),
            expense_date=timezone.localdate(),
        )

    position = _position(tenant_a)
    assert position["income"] == "10000000.00"
    assert position["expenses"] == "1500000.00"
    assert position["payroll"] == "4000000.00"
    assert position["balance"] == "4500000.00"
    assert employee.base_salary == Decimal("4000000.00")


def test_a_finalized_but_unpaid_run_is_still_in_the_till(tenant_a: Any):
    """
    Hisoblangan, lekin hali berilmagan oylik — kassada turgan pul.

    Eski hisob uni chiqim deb sanardi va bog'chani o'zida bor pulni
    yo'q deb ishontirardi. Foyda-zarar hisoboti esa uni xarajat deb
    sanashda davom etadi — ikkalasi ham o'z savoliga to'g'ri javob.
    """
    child = _child(tenant_a)
    _employee(tenant_a, "3000000")
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("5000000"), method="cash")
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=timezone.localdate().year,
            period_month=timezone.localdate().month,
        )
        payroll.finalize_run(run=run)

    position = _position(tenant_a)
    assert position["payroll"] == "0.00"
    assert position["balance"] == "5000000.00"


def test_an_advance_leaves_the_till_the_day_it_is_handed_over(tenant_a: Any):
    child = _child(tenant_a)
    employee = _employee(tenant_a)
    today = timezone.localdate()

    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("5000000"), method="cash")
        payroll.record_advance(
            employee=employee, amount=Decimal("700000"), paid_on=today.replace(day=10)
        )

    position = _position(tenant_a)
    assert position["payroll"] == "700000.00"
    assert position["balance"] == "4300000.00"


def test_an_advance_is_not_counted_twice_when_the_run_is_paid(tenant_a: Any):
    """
    Avans sof maoshdan ayrilgan, ya'ni "sof + avans" = yalpi.

    Kassa jurnalida esa ikkala harakat ham alohida yozuv — biri
    avans berilganda, ikkinchisi qolgani to'langanda. Qo'shimcha
    hisob-kitob shart emas: yig'indi o'zi to'g'ri chiqadi.
    """
    child = _child(tenant_a)
    employee = _employee(tenant_a)
    today = timezone.localdate()

    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("10000000"), method="cash")
        payroll.record_advance(
            employee=employee,
            amount=Decimal("1000000"),
            paid_on=today.replace(day=min(15, today.day)),
        )
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=today.year,
            period_month=today.month,
        )
        payroll.finalize_run(run=run)
        run.refresh_from_db()
        assert run.total_net == Decimal("3000000.00"), "avans sof maoshdan ayrilgan"
        payroll.pay_run(run=run)

    position = _position(tenant_a)
    assert position["payroll"] == "4000000.00"
    assert position["balance"] == "6000000.00"


def test_reversed_payments_are_not_income(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(child=child, amount=Decimal("1500000"), method="cash")
        finance.record_payment(child=child, amount=Decimal("500000"), method="terminal")
        finance.reverse_payment(payment=payment, reason="Xato summa")

        revenue = selectors.revenue_report(
            organization_id=tenant_a.organization.id,
            date_from=timezone.localdate(),
            date_to=timezone.localdate(),
        )

    position = _position(tenant_a)
    # Tushum yalpi; terminal komissiyasi (0,2 % = 1 000) — alohida xarajat
    # (Bosqich 12.5), shuning uchun qoldiq 499 000.
    assert position["income"] == "500000.00"
    assert position["expenses"] == "1000.00"
    assert position["balance"] == "499000.00"
    # Tushum hisoboti ham, usul kesimi ham qaytarilganni sanamaydi.
    assert revenue["total"] == "500000.00"
    assert [row["method"] for row in revenue["by_method"]] == ["terminal"]


def test_the_balance_is_broken_down_by_pot(tenant_a: Any):
    """Mijozning aynan soʻragan kesimi: naqd qancha, plastikda qancha."""
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(child=child, amount=Decimal("1400000"), method="cash")
        finance.record_payment(child=child, amount=Decimal("100000"), method="terminal")
        finance.record_payment(child=child, amount=Decimal("300000"), method="bank_transfer")

    position = _position(tenant_a)
    by_kind = {row["kind"]: row["balance"] for row in position["accounts"]}
    # Ikki qop (2026-10-14): terminal va oʻtkazma — ikkalasi ham bankda.
    # "Nimadan qancha keldi" esa tushum hisobotining usul kesimida qoladi.
    # Bankdan terminal komissiyasi 200 chiqdi (Bosqich 12.5).
    assert by_kind == {"cash": "1400000.00", "bank": "399800.00"}
    assert position["balance"] == "1799800.00"
