"""
Uch to'g'ri ko'rinish (Bosqich 13.2d, brif §3.3–3.5, testlar 3–7).

* **Foyda-zarar** — qaysi oyning daromadi va xarajati (tegishli oy).
* **Pul oqimi** — pul qachon harakatlangan.
* **Holat** — sanaga talablar va majburiyatlar.

Excel'dagi saboqlar: oylik to'langan oyga xarajat qilib yozilardi;
avans ikki oyda sanalardi; dividend xarajat bilan aralashardi;
konditsioner bir oyning foydasini "yeb" qo'yardi.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import CashAccount
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses.models import ExpenseCategory
from apps.finance import services as finance
from apps.finance.models import TariffPlan
from apps.hr.models import Employee
from apps.payroll import services as payroll
from apps.reports import money

pytestmark = pytest.mark.django_db

FEE = Decimal("3050000")


@pytest.fixture
def org(tenant_a: Any) -> Any:
    tenant_a.fund("500000000", kind="all")
    return tenant_a


def _ctx(tenant: Any) -> Any:
    return organization_context(tenant.organization.id)


def _pot(tenant: Any, kind: str) -> CashAccount:
    with _ctx(tenant):
        return CashAccount.objects.get(branch=tenant.branch, kind=kind, is_active=True)


def _pnl(tenant: Any, year: int, month: int) -> dict[str, Any]:
    with _ctx(tenant):
        return money.profit_and_loss(organization_id=tenant.organization.id, year=year, month=month)


def _flow(tenant: Any, year: int, month: int) -> dict[str, Any]:
    with _ctx(tenant):
        return money.cash_flow(organization_id=tenant.organization.id, year=year, month=month)


def _position(tenant: Any, as_of: date) -> dict[str, Any]:
    with _ctx(tenant):
        return money.position(organization_id=tenant.organization.id, as_of=as_of)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


# --- 3: iyul oyligi avgust–sentabrda to'langan ---


def test_3_july_salary_is_a_july_cost_paid_in_august_and_september(org: Any):
    with _ctx(org):
        employee = Employee.objects.create(
            organization=org.organization,
            branch=org.branch,
            first_name="Nilufar",
            last_name="Sodiqova",
            hire_date=date(2025, 1, 10),
            base_salary=Decimal("4000000"),
        )
        run = payroll.create_run(
            organization=org.organization, branch=org.branch, period_year=2026, period_month=7
        )
        payroll.finalize_run(run=run)
        item = run.items.get(employee=employee)
        till = _pot(org, "cash")
        for day in (date(2026, 8, 28), date(2026, 9, 8)):
            payroll.pay_run(
                run=run,
                payouts=[
                    {
                        "payroll_item_id": item.id,
                        "part": "cash",
                        "amount": "2000000",
                        "cash_account_id": till.id,
                    }
                ],
                paid_on=day,
            )
            run.refresh_from_db()

    july, august = _pnl(org, 2026, 7), _pnl(org, 2026, 8)
    assert _d(july["payroll"]) == Decimal("4000000")
    assert july["payroll_estimated"] is False

    # Avgustda hisoblash YOʻQ — va oylik nol emas, TAXMINIY (audit,
    # 2026-10-30). Ilgari bu yerda 0 turardi va qoralama oyda foyda
    # oyliksiz chiqardi: xodim ishlagan, xarajat esa koʻrinmasdi.
    # Javob buni ochiq aytadi, ekran esa banner koʻrsatadi.
    assert _d(august["payroll"]) == Decimal("4000000")
    assert august["payroll_estimated"] is True

    assert _d(_flow(org, 2026, 8)["outflows"]["payroll"]) == Decimal("2000000")
    assert _d(_flow(org, 2026, 9)["outflows"]["payroll"]) == Decimal("2000000")

    assert _d(_position(org, date(2026, 7, 31))["liabilities"]["unpaid_payroll"]) == Decimal(
        "4000000"
    )
    assert _d(_position(org, date(2026, 8, 31))["liabilities"]["unpaid_payroll"]) == Decimal(
        "2000000"
    )
    assert _d(_position(org, date(2026, 9, 30))["liabilities"]["unpaid_payroll"]) == 0


# --- 4: avgustda olingan sentabr to'lovi ---


def test_4_an_august_payment_for_september_is_counted_once(org: Any):
    with _ctx(org):
        tariff = TariffPlan.objects.create(
            organization=org.organization, branch=org.branch, name="Asosiy", amount=FEE
        )
        child = Child.objects.create(
            organization=org.organization,
            branch=org.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            is_existing_client=True,
            enrolled_on=date(2025, 9, 1),
        )
        finance.record_payment(
            child=child,
            amount=FEE,
            method="bank_transfer",
            paid_at=timezone.make_aware(datetime.combine(date(2026, 8, 24), time(10))),
            backdate_reason="Test tarixi",
        )
        finance.issue_invoice(child=child, period_year=2026, period_month=9)

    assert _d(_flow(org, 2026, 8)["inflows"]["tuition"]) == FEE
    assert _d(_flow(org, 2026, 9)["inflows"]["tuition"]) == 0
    assert _d(_position(org, date(2026, 8, 31))["liabilities"]["advances"]) == FEE
    assert _d(_pnl(org, 2026, 9)["revenue"]["tuition"]) == FEE


# --- 5: konditsioner — investitsiya, 12 oyga ---


def test_5_an_air_conditioner_is_spread_over_twelve_months(org: Any):
    with _ctx(org):
        category = ExpenseCategory.objects.create(
            organization=org.organization, branch=org.branch, name="Taʼmir"
        )
    response = org.client().post(
        "/api/v1/expenses",
        {
            "category_id": str(category.id),
            "amount": "12000000",
            "expense_date": "2026-09-10",
            "cash_account_id": str(_pot(org, "bank").id),
            "is_capex": True,
            "amortize_months": 12,
        },
        format="json",
    )
    assert response.status_code == 201, response.json()

    september, october, august = _pnl(org, 2026, 9), _pnl(org, 2026, 10), _pnl(org, 2026, 8)
    assert _d(september["amortization"]) == Decimal("1000000")
    assert _d(october["amortization"]) == Decimal("1000000")
    assert _d(august["amortization"]) == 0
    assert _d(september["operating_expenses"]) == 0
    assert _d(_flow(org, 2026, 9)["outflows"]["capex"]) == Decimal("12000000")


def test_an_investment_not_spread_sits_on_its_own_line(org: Any):
    with _ctx(org):
        category = ExpenseCategory.objects.create(
            organization=org.organization, branch=org.branch, name="Mebel"
        )
    org.client().post(
        "/api/v1/expenses",
        {
            "category_id": str(category.id),
            "amount": "5000000",
            "expense_date": "2026-09-10",
            "cash_account_id": str(_pot(org, "bank").id),
            "is_capex": True,
        },
        format="json",
    )
    september = _pnl(org, 2026, 9)
    assert _d(september["capex"]) == Decimal("5000000")
    assert _d(september["operating_expenses"]) == 0
    assert _d(september["operating_profit"]) == 0


# --- 6: dividend ---


def test_6_a_dividend_is_outside_profit_and_leaves_a_tax_liability(org: Any):
    with _ctx(org):
        cash.record_operation(
            kind="owner_draw",
            subtype="dividend",
            account=_pot(org, "bank"),
            amount=Decimal("60000000"),
            occurred_on=date(2026, 9, 20),
            reason="Taʼsischilar qarori",
        )
    september = _pnl(org, 2026, 9)
    assert _d(september["operating_profit"]) == 0
    assert _d(september["owner_draws"]) == Decimal("60000000")
    assert _d(_flow(org, 2026, 9)["outflows"]["owner_draws"]) == Decimal("60000000")
    assert _d(_position(org, date(2026, 9, 30))["liabilities"]["taxes"]) == Decimal("3000000")


# --- 7: inkassa ---


def test_7_cash_collection_is_neither_income_nor_expense(org: Any):
    with _ctx(org):
        cash.transfer(
            source=_pot(org, "cash"),
            target=_pot(org, "bank"),
            amount=Decimal("40000000"),
            description="Inkassa",
            occurred_at=timezone.make_aware(datetime.combine(date(2026, 9, 15), time(12))),
        )
    flow = _flow(org, 2026, 9)
    assert _d(flow["inflows"]["total"]) == 0
    assert _d(flow["outflows"]["total"]) == 0
    assert _d(flow["transfers"]["in"]) == _d(flow["transfers"]["out"]) == Decimal("40000000")


# --- Ko'prik va holat tengligi ---


def test_the_cash_flow_bridges_opening_to_closing(org: Any):
    with _ctx(org):
        cash.record_operation(
            kind="loan_in",
            account=_pot(org, "bank"),
            amount=Decimal("10000000"),
            occurred_on=date(2026, 9, 3),
            reason="Bank krediti",
        )
    flow = _flow(org, 2026, 9)
    assert _d(flow["opening"]) + _d(flow["inflows"]["total"]) - _d(flow["outflows"]["total"]) == _d(
        flow["closing"]
    )
    assert _d(_position(org, date(2026, 9, 30))["liabilities"]["loans"]) == Decimal("10000000")


def test_a_credit_purchase_is_a_payable_until_paid(org: Any):
    from apps.inventory.models import Supplier

    with _ctx(org):
        supplier = Supplier.objects.create(
            organization=org.organization, branch=org.branch, name="Goʻsht doʻkoni"
        )
        category = ExpenseCategory.objects.create(
            organization=org.organization, branch=org.branch, name="Goʻsht"
        )
    response = org.client().post(
        "/api/v1/expenses",
        {
            "category_id": str(category.id),
            "amount": "4500000",
            "expense_date": "2026-09-25",
            "on_credit": True,
            "supplier_id": str(supplier.id),
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    assert _d(_position(org, date(2026, 9, 30))["liabilities"]["suppliers"]) == Decimal("4500000")
    assert _d(_pnl(org, 2026, 9)["operating_expenses"]) == Decimal("4500000")


# --- API ---


def test_the_three_views_are_served_to_the_owner(org: Any):
    client = org.client()
    for url in (
        "/api/v1/reports/pnl?year=2026&month=9",
        "/api/v1/reports/cash-flow?year=2026&month=9",
        "/api/v1/reports/position?as_of=2026-09-30",
    ):
        assert client.get(url).status_code == 200, url


def test_a_cashier_does_not_see_them(org: Any):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with _ctx(org):
        user = User.objects.create_user(
            email="kassir@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Kassir",
            organization=org.organization,
            role=org.role("cashier"),
            branch=org.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/v1/reports/pnl?year=2026&month=9").status_code == 403


@pytest.mark.tenancy
def test_another_tenants_money_never_shows(org: Any, tenant_b: Any):
    with _ctx(org):
        cash.record_operation(
            kind="loan_in",
            account=_pot(org, "bank"),
            amount=Decimal("10000000"),
            occurred_on=date(2026, 9, 3),
            reason="Bank krediti",
        )
    data = (
        tenant_b.client()
        .get(f"/api/v1/reports/position?as_of=2026-09-30&branch={org.branch.id}")
        .json()["data"]
    )
    assert Decimal(data["liabilities"]["loans"]) == 0
