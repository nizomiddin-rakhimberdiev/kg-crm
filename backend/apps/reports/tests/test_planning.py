"""
Reja, prognoz, xavfsiz olish summasi, ko'rsatkichlar, trendlar va yillik
hisobot (Bosqich 13.7, brif §5.3-12, §6; test 11).

Prognoz — taxmin, lekin har qatorining asosi yozilgan: qaysi qarz, qaysi
oylik, qaysi nasiya, qaysi o'rtacha. Xavfsiz olish summasi = kassa + bank +
yo'ldagi pul − kelgusi 30 kun majburiyatlari − zaxira.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import CashAccount
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db

TODAY = date(2026, 9, 15)
FEE = Decimal("3050000")
M = Decimal("1000000")


def _ctx(tenant: Any) -> Any:
    return organization_context(tenant.organization.id)


def _at(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(10)))


def _pot(tenant: Any, kind: str) -> CashAccount:
    with _ctx(tenant):
        return CashAccount.objects.get(branch=tenant.branch, kind=kind, is_active=True)


def _put_money(tenant: Any, kind: str, amount: Decimal, day: date = date(2026, 9, 1)) -> None:
    with _ctx(tenant):
        cash.adjust_balance(
            account=_pot(tenant, kind),
            amount=amount,
            reason="Test: boshlangʻich qoldiq",
            opening=True,
            occurred_at=_at(day),
        )


def _setting(tenant: Any, key: str, value: Any) -> None:
    from apps.settings_app.services import set_setting

    with _ctx(tenant):
        set_setting(organization=tenant.organization, key=key, value=value)


def _credit(tenant: Any, amount: Decimal, due: date, day: date = date(2026, 9, 10)) -> Any:
    from apps.expenses.models import Expense, ExpenseCategory
    from apps.expenses.services import approve_expense
    from apps.inventory.models import Supplier

    with _ctx(tenant):
        supplier, _ = Supplier.objects.get_or_create(
            organization=tenant.organization, branch=tenant.branch, name="Goʻsht doʻkoni"
        )
        category, _ = ExpenseCategory.objects.get_or_create(
            organization=tenant.organization, branch=tenant.branch, name="Oziq-ovqat"
        )
        expense = Expense.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            category=category,
            amount=amount,
            expense_date=day,
            on_credit=True,
            supplier=supplier,
            due_date=due,
            receipt="r.png",
        )
        approve_expense(expense=expense, approved_by=tenant.owner)
        return expense


def _forecast(tenant: Any, day: date = TODAY) -> dict[str, Any]:
    from apps.reports import forecast

    with _ctx(tenant):
        return forecast.forecast(organization_id=tenant.organization.id, as_of=day)


def _children(tenant: Any, count: int, months: list[int]) -> list[Child]:
    with _ctx(tenant):
        tariff, _ = TariffPlan.objects.get_or_create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Asosiy",
            defaults={"amount": FEE},
        )
        kids = [
            Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name=f"Bola{index}",
                last_name="Valiyev",
                date_of_birth=date(2021, 3, 14),
                gender="male",
                tariff=tariff,
                is_existing_client=True,
                enrolled_on=date(2025, 9, 1),
            )
            for index in range(count)
        ]
        for month in months:
            for child in kids:
                finance.issue_invoice(child=child, period_year=2026, period_month=month)
        return kids


def _pay(tenant: Any, child: Child, amount: Decimal, day: date) -> None:
    with _ctx(tenant):
        finance.record_payment(
            child=child, amount=amount, method="cash", paid_at=_at(day), backdate_reason="Tarix"
        )


# --- 11: xavfsiz olish summasi ---


def test_11_safe_withdrawal_is_money_minus_30_days_minus_reserve(tenant_a: Any):
    _put_money(tenant_a, "cash", 100 * M)
    _put_money(tenant_a, "bank", 80 * M)
    _credit(tenant_a, 110 * M, due=TODAY + timedelta(days=20))
    _setting(tenant_a, "forecast.reserve_amount", 30000000)

    safe = _forecast(tenant_a)["safe_withdrawal"]

    assert Decimal(safe["money"]) == 180 * M
    assert Decimal(safe["obligations_30"]) == 110 * M
    assert Decimal(safe["reserve"]) == 30 * M
    assert Decimal(safe["amount"]) == 40 * M


def test_safe_withdrawal_never_goes_below_zero(tenant_a: Any):
    _put_money(tenant_a, "cash", 10 * M)
    _credit(tenant_a, 50 * M, due=TODAY + timedelta(days=5))

    safe = _forecast(tenant_a)["safe_withdrawal"]

    assert Decimal(safe["amount"]) == 0
    assert Decimal(safe["shortfall"]) == 40 * M


def test_the_default_reserve_is_half_a_month_of_payroll(tenant_a: Any):
    from apps.hr.models import Employee
    from apps.payroll import services as payroll

    _put_money(tenant_a, "cash", 100 * M)
    with _ctx(tenant_a):
        Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Nilufar",
            last_name="Sodiqova",
            hire_date=date(2025, 1, 10),
            base_salary=Decimal("8000000"),
        )
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=8,
        )
        payroll.finalize_run(run=run)

    safe = _forecast(tenant_a)["safe_withdrawal"]

    assert Decimal(safe["reserve"]) == Decimal("4000000")


# --- 30 / 60 / 90 ---


def test_a_supplier_due_in_40_days_falls_in_the_60_day_window(tenant_a: Any):
    _credit(tenant_a, 7 * M, due=TODAY + timedelta(days=40))

    data = _forecast(tenant_a)
    buckets = {row["days"]: row for row in data["buckets"]}

    assert Decimal(buckets[30]["outflows"]["suppliers"]) == 0
    assert Decimal(buckets[60]["outflows"]["suppliers"]) == 7 * M
    assert Decimal(buckets[90]["outflows"]["suppliers"]) == 7 * M


def test_an_overdue_supplier_is_due_now(tenant_a: Any):
    _credit(tenant_a, 3 * M, due=TODAY - timedelta(days=3))
    buckets = {row["days"]: row for row in _forecast(tenant_a)["buckets"]}
    assert Decimal(buckets[30]["outflows"]["suppliers"]) == 3 * M


def test_unpaid_payroll_is_due_within_30_days(tenant_a: Any):
    from apps.hr.models import Employee
    from apps.payroll import services as payroll

    with _ctx(tenant_a):
        Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Nilufar",
            last_name="Sodiqova",
            hire_date=date(2025, 1, 10),
            base_salary=Decimal("4000000"),
        )
        run = payroll.create_run(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=2026,
            period_month=8,
        )
        payroll.finalize_run(run=run)

    buckets = {row["days"]: row for row in _forecast(tenant_a)["buckets"]}
    assert Decimal(buckets[30]["outflows"]["payroll"]) >= Decimal("4000000")


def test_expected_receipts_follow_the_collection_history(tenant_a: Any):
    _setting(tenant_a, "finance.backdate_days", 400)  # tarixni bugundan oldin yozamiz
    kids = _children(tenant_a, 4, months=[6, 7, 8, 9])
    for month in (6, 7, 8):
        for kid in kids[:3]:  # tarixda 75 % yig'iladi
            _pay(tenant_a, kid, FEE, date(2026, month, 10))

    data = _forecast(tenant_a)
    buckets = {row["days"]: row for row in data["buckets"]}

    # Sentabr: 4 × 3 050 000 × 75 % = 9 150 000 kutiladi, hali hech narsa yo'q.
    assert Decimal(buckets[30]["inflows"]["tuition"]) >= Decimal("9150000")
    assert data["basis"]["collection_rate"] == "75.0"
    for row in data["buckets"]:
        assert Decimal(row["closing"]) == Decimal(data["opening"]) + Decimal(
            row["inflows"]["total"]
        ) - Decimal(row["outflows"]["total"])


def test_every_forecast_line_states_its_basis(tenant_a: Any):
    _credit(tenant_a, 2 * M, due=TODAY + timedelta(days=10))
    data = _forecast(tenant_a)
    assert data["lines"]
    for line in data["lines"]:
        assert line["basis"]
        assert line["date"]


# --- Byudjet ---


def test_budget_against_actual(tenant_a: Any):
    from apps.expenses.models import ExpenseCategory

    kids = _children(tenant_a, 2, months=[9])
    with _ctx(tenant_a):
        food = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Oziq-ovqat 2"
        )
    client = tenant_a.client()
    saved = client.put(
        "/api/v1/reports/budget",
        {
            "year": 2026,
            "month": 9,
            "lines": [
                {"kind": "revenue", "amount": "7000000"},
                {"kind": "category", "category_id": str(food.id), "amount": "1500000"},
                {"kind": "payroll", "amount": "0"},
            ],
        },
        format="json",
    )
    assert saved.status_code == 200, saved.content

    data = client.get("/api/v1/reports/budget", {"year": 2026, "month": 9}).json()["data"]
    revenue = next(row for row in data["lines"] if row["kind"] == "revenue")
    assert Decimal(revenue["plan"]) == Decimal("7000000")
    assert Decimal(revenue["actual"]) == 2 * FEE
    assert Decimal(revenue["difference"]) == 2 * FEE - Decimal("7000000")
    assert len(kids) == 2

    copied = client.post(
        "/api/v1/reports/budget/copy",
        {"from_year": 2026, "from_month": 9, "year": 2026, "month": 10},
        format="json",
    )
    assert copied.status_code == 200
    october = client.get("/api/v1/reports/budget", {"year": 2026, "month": 10}).json()["data"]
    assert Decimal(next(r for r in october["lines"] if r["kind"] == "revenue")["plan"]) == 7 * M


def test_the_pack_shows_plan_and_forecast(tenant_a: Any):
    from apps.reports import pack

    tenant_a.client().put(
        "/api/v1/reports/budget",
        {"year": 2026, "month": 9, "lines": [{"kind": "revenue", "amount": "5000000"}]},
        format="json",
    )
    with _ctx(tenant_a):
        data = pack.build(organization_id=tenant_a.organization.id, year=2026, month=9)
    plan = next(section for section in data["sections"] if section["key"] == "plan")
    assert plan["available"] is True
    assert any(row["kind"] == "revenue" for row in plan["budget"])
    assert "safe_withdrawal" in plan["forecast"]


def test_a_manager_cannot_change_the_budget(tenant_a: Any):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import Permission, RolePermission, User

    with _ctx(tenant_a):
        role = tenant_a.role("manager")
        RolePermission.objects.get_or_create(
            role=role, permission=Permission.objects.get(code="reports.finance")
        )
        user = User.objects.create_user(
            email="m@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Menejer",
            organization=tenant_a.organization,
            role=role,
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/v1/reports/budget", {"year": 2026, "month": 9}).status_code == 200
    response = client.put(
        "/api/v1/reports/budget",
        {"year": 2026, "month": 9, "lines": [{"kind": "revenue", "amount": "1"}]},
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.tenancy
def test_a_foreign_category_cannot_be_budgeted(tenant_a: Any, tenant_b: Any):
    from apps.expenses.models import ExpenseCategory

    with organization_context(tenant_b.organization.id):
        foreign = ExpenseCategory.objects.create(
            organization=tenant_b.organization, branch=tenant_b.branch, name="Begona"
        )
    response = tenant_a.client().put(
        "/api/v1/reports/budget",
        {
            "year": 2026,
            "month": 9,
            "lines": [{"kind": "category", "category_id": str(foreign.id), "amount": "1"}],
        },
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.tenancy
def test_another_tenants_budget_never_shows(tenant_a: Any, tenant_b: Any):
    tenant_a.client().put(
        "/api/v1/reports/budget",
        {"year": 2026, "month": 9, "lines": [{"kind": "revenue", "amount": "9000000"}]},
        format="json",
    )
    data = tenant_b.client().get("/api/v1/reports/budget", {"year": 2026, "month": 9}).json()
    revenue = next(row for row in data["data"]["lines"] if row["kind"] == "revenue")
    assert Decimal(revenue["plan"]) == 0


# --- Trendlar, ko'rsatkichlar, yillik hisobot ---


def test_trends_cover_twelve_months_and_match_the_pnl(tenant_a: Any):
    from apps.reports import money

    _children(tenant_a, 2, months=[8, 9])
    data = (
        tenant_a.client().get("/api/v1/reports/trends", {"year": 2026, "month": 9}).json()["data"]
    )
    assert len(data["months"]) == 12
    assert data["months"][-1]["period"] == "2026-09"
    assert data["months"][0]["period"] == "2025-10"
    with _ctx(tenant_a):
        pnl = money.profit_and_loss(organization_id=tenant_a.organization.id, year=2026, month=9)
    assert data["months"][-1]["revenue"] == pnl["revenue"]["total"]
    assert data["months"][-1]["operating_profit"] == pnl["operating_profit"]


def test_every_kpi_has_a_definition(tenant_a: Any):
    data = tenant_a.client().get("/api/v1/reports/kpi", {"year": 2026, "month": 9}).json()["data"]
    ids = {row["id"] for row in data["items"]}
    assert {
        "occupancy",
        "average_per_child",
        "benefit_share",
        "collection_rate",
        "payroll_share",
        "food_per_child_day",
        "operating_margin",
        "break_even_children",
        "churn_rate",
        "average_stay_months",
        "marketing_per_new_child",
        "safe_withdrawal",
    } <= ids
    for row in data["items"]:
        assert row["title"]
        assert row["definition"]


def test_the_annual_report_sums_the_months(tenant_a: Any):
    from apps.reports import money

    kids = _children(tenant_a, 2, months=[3, 9])
    _pay(tenant_a, kids[0], FEE, date(2026, 9, 12))
    client = tenant_a.client()
    data = client.get("/api/v1/reports/annual", {"year": 2026}).json()["data"]
    with _ctx(tenant_a):
        months = [
            money.profit_and_loss(organization_id=tenant_a.organization.id, year=2026, month=m)
            for m in range(1, 13)
        ]
    totals = next(s for s in data["sections"] if s["key"] == "pnl")["total"]
    assert Decimal(totals["revenue"]) == sum(Decimal(m["revenue"]["total"]) for m in months)
    assert Decimal(totals["revenue"]) == 4 * FEE
    assert len(next(s for s in data["sections"] if s["key"] == "months")["rows"]) == 12

    pdf = client.get("/api/v1/reports/annual/pdf", {"year": 2026})
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"
    xlsx = client.get("/api/v1/reports/annual/xlsx", {"year": 2026})
    assert xlsx.status_code == 200


def test_a_cashier_sees_no_forecast(tenant_a: Any):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with _ctx(tenant_a):
        user = User.objects.create_user(
            email="k@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Kassir",
            organization=tenant_a.organization,
            role=tenant_a.role("cashier"),
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/v1/reports/forecast").status_code == 403
    assert client.get("/api/v1/reports/trends").status_code == 403


def test_home_answers_how_much_can_i_take(tenant_a: Any):
    _put_money(tenant_a, "cash", 20 * M)
    data = tenant_a.client().get("/api/v1/reports/home").json()["data"]
    profit = next(card for card in data["cards"] if card["key"] == "profit")
    assert "safe_withdrawal" in profit
