"""
Oylik moliyaviy hisobot paketi (Bosqich 13.5, brif §5.3, §8, testlar 10,
15, 16, 19, 20).

Bitta deterministik funksiya — (tashkilot, filial, davr) → JSON. Web, PDF,
Excel va arxiv o'sha JSON'dan. Tuzilma har oy bir xil (16 bo'lim);
o'zgarmas nusxa — JSON + nazorat summasi; keyin ma'lumot o'zgarsa
"o'zgarish bor" va raqamlar darajasida farq.
"""

from __future__ import annotations

import io
import time as clock
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash import services as cash
from apps.cash.models import CashAccount
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Payment, TariffPlan
from apps.reports import pack

pytestmark = pytest.mark.django_db

YEAR, MONTH = 2026, 9
FEE = Decimal("3050000")


@pytest.fixture
def org(tenant_a: Any) -> Any:
    tenant_a.fund("500000000", kind="all")
    return tenant_a


def _ctx(tenant: Any) -> Any:
    return organization_context(tenant.organization.id)


def _at(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(10)))


def _children(tenant: Any, count: int, *, enrolled: date = date(2025, 9, 1)) -> list[Child]:
    with _ctx(tenant):
        tariff, _ = TariffPlan.objects.get_or_create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Asosiy",
            defaults={"amount": FEE},
        )
        return [
            Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name=f"Bola{index}",
                last_name="Valiyev",
                date_of_birth=date(2021, 3, 14),
                gender="male",
                tariff=tariff,
                is_existing_client=True,
                enrolled_on=enrolled,
            )
            for index in range(count)
        ]


def _issue(tenant: Any, children: list[Child], month: int = MONTH) -> None:
    with _ctx(tenant):
        for child in children:
            finance.issue_invoice(child=child, period_year=YEAR, period_month=month)


def _pay(tenant: Any, child: Child, amount: Decimal, day: date, method: str = "cash") -> Payment:
    with _ctx(tenant):
        return finance.record_payment(
            child=child,
            amount=amount,
            method=method,
            paid_at=_at(day),
            backdate_reason="Test tarixi",
        )


def _build(tenant: Any, month: int = MONTH) -> dict[str, Any]:
    with _ctx(tenant):
        return pack.build(organization_id=tenant.organization.id, year=YEAR, month=month)


def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
    return next(section for section in data["sections"] if section["key"] == key)


# --- Tuzilma ---


def test_the_pack_always_has_the_same_sixteen_sections(org: Any):
    data = _build(org)
    assert [section["key"] for section in data["sections"]] == [
        "summary",
        "children",
        "revenue",
        "receipts",
        "debts",
        "expenses",
        "payroll",
        "cash_bank",
        "pnl",
        "profit_vs_cash",
        "position",
        "plan",
        "taxes",
        "checks",
        "attention",
        "appendix",
    ]
    for section in data["sections"]:
        assert section["title"]


# --- Daromad zanjiri (test 2 tuzilmasi) ---


def test_the_revenue_chain_holds_and_its_ratios_are_defined(org: Any):
    kids = _children(org, 4)
    _issue(org, kids)
    for kid in kids[:3]:
        _pay(org, kid, FEE, date(2026, 9, 10))

    revenue = _section(_build(org), "revenue")
    chain = {row["id"]: Decimal(row["value"]) for row in revenue["chain"]}

    assert chain["charged"] + chain["benefits"] + chain["recalculations"] == chain["due"]
    assert chain["collected"] + chain["debt"] == chain["due"]
    kpi = revenue["kpi"]
    assert Decimal(kpi["collection_rate"]) == Decimal("75.0")
    assert Decimal(kpi["average_per_child"]) == FEE


# --- 15: farq omillarga ajraladi ---


def test_15_revenue_factors_add_up_to_the_change(org: Any):
    from apps.finance.models import Discount

    august_kids = _children(org, 3)
    _issue(org, august_kids, 8)
    new_kids = _children(org, 2)
    with _ctx(org):
        Discount.objects.create(
            organization=org.organization,
            branch=org.branch,
            child=new_kids[0],
            kind="staff_child",
            discount_type="percent",
            value=Decimal("0"),
            reason="Oshpaz farzandi",
            valid_from=date(2026, 9, 1),
        )
    _issue(org, august_kids + new_kids, 9)

    factors = _section(_build(org), "revenue")["factors"]
    total = Decimal(factors["total_change"])
    parts = sum(Decimal(row["value"]) for row in factors["items"])
    assert total == parts
    keys = {row["id"] for row in factors["items"]}
    assert keys == {"children", "price", "benefits", "recalculations"}


# --- 10: foyda ≠ pul ko'prigi ---


def test_10_profit_bridges_to_the_change_in_money_exactly(org: Any):
    from apps.expenses.models import Expense, ExpenseCategory
    from apps.expenses.services import approve_expense
    from apps.inventory.models import Supplier

    kids = _children(org, 3)
    _issue(org, kids)
    _pay(org, kids[0], FEE, date(2026, 9, 5))
    _pay(org, kids[1], Decimal("1000000"), date(2026, 9, 6), method="terminal")
    with _ctx(org):
        till = CashAccount.objects.get(branch=org.branch, kind="cash", is_active=True)
        bank = CashAccount.objects.get(branch=org.branch, kind="bank", is_active=True)
        food = ExpenseCategory.objects.create(
            organization=org.organization, branch=org.branch, name="Oziq-ovqat"
        )
        for amount, extra in (
            ("2000000", {}),
            ("12000000", {"is_capex": True, "amortize_months": 12}),
        ):
            expense = Expense.objects.create(
                organization=org.organization,
                branch=org.branch,
                category=food,
                amount=Decimal(amount),
                expense_date=date(2026, 9, 12),
                cash_account=bank,
                **extra,
            )
            approve_expense(expense=expense, approved_by=org.owner)
        supplier = Supplier.objects.create(
            organization=org.organization, branch=org.branch, name="Goʻsht"
        )
        credit = Expense.objects.create(
            organization=org.organization,
            branch=org.branch,
            category=food,
            amount=Decimal("1500000"),
            expense_date=date(2026, 9, 20),
            on_credit=True,
            supplier=supplier,
        )
        approve_expense(expense=credit, approved_by=org.owner)
        cash.record_operation(
            kind="owner_draw",
            subtype="dividend",
            account=bank,
            amount=Decimal("5000000"),
            occurred_on=date(2026, 9, 25),
            reason="Dividend",
        )
        cash.record_operation(
            kind="loan_in",
            account=bank,
            amount=Decimal("3000000"),
            occurred_on=date(2026, 9, 26),
            reason="Kredit",
        )
        cash.transfer(
            source=till,
            target=bank,
            amount=Decimal("1000000"),
            description="Inkassa",
            occurred_at=_at(date(2026, 9, 27)),
        )

    bridge = _section(_build(org), "profit_vs_cash")
    steps = sum(Decimal(row["value"]) for row in bridge["steps"])
    assert Decimal(bridge["operating_profit"]) + steps == Decimal(bridge["money_change"])
    assert bridge["check"]["ok"] is True


# --- 16: topshirilgandan keyingi o'zgarish ---


def test_16_a_change_after_the_snapshot_shows_and_versions_differ(org: Any):
    kids = _children(org, 2)
    _issue(org, kids)
    payment = _pay(org, kids[0], FEE, date(2026, 9, 10))
    client = org.client()

    first = client.post(
        "/api/v1/reports/pack/snapshot", {"year": YEAR, "month": MONTH}, format="json"
    )
    assert first.status_code == 201, first.json()
    assert first.json()["data"]["version"] == 1
    live = client.get("/api/v1/reports/pack", {"year": YEAR, "month": MONTH}).json()["data"]
    assert live["changed_since_snapshot"] is False

    with _ctx(org):
        finance.reverse_payment(payment=payment, reason="Xato kiritilgan")

    live = client.get("/api/v1/reports/pack", {"year": YEAR, "month": MONTH}).json()["data"]
    assert live["changed_since_snapshot"] is True
    second = client.post(
        "/api/v1/reports/pack/snapshot", {"year": YEAR, "month": MONTH}, format="json"
    )
    assert second.json()["data"]["version"] == 2

    diff = client.get(
        "/api/v1/reports/pack/diff", {"year": YEAR, "month": MONTH, "from": 1, "to": 2}
    ).json()["data"]
    changed = {row["path"] for row in diff["changes"]}
    assert any("collected" in path for path in changed)
    versions = client.get("/api/v1/reports/pack/versions", {"year": YEAR, "month": MONTH}).json()[
        "data"
    ]
    assert [row["version"] for row in versions] == [2, 1]
    assert all(len(row["checksum"]) == 64 for row in versions)


def test_an_unchanged_month_does_not_create_a_new_version(org: Any):
    client = org.client()
    client.post("/api/v1/reports/pack/snapshot", {"year": YEAR, "month": MONTH}, format="json")
    again = client.post(
        "/api/v1/reports/pack/snapshot", {"year": YEAR, "month": MONTH}, format="json"
    )
    assert again.json()["data"]["version"] == 1


# --- 19: raqam modul ekranidagi raqamga teng, manbasi ochiladi ---


def test_19_the_pack_matches_the_module_screens_and_opens_its_sources(org: Any):
    from apps.finance.selectors import monthly_summary
    from apps.reports.money import profit_and_loss

    kids = _children(org, 3)
    _issue(org, kids)
    _pay(org, kids[0], FEE, date(2026, 9, 10))
    data = _build(org)
    with _ctx(org):
        summary = monthly_summary(organization_id=org.organization.id, year=YEAR, month=MONTH)
        pnl = profit_and_loss(organization_id=org.organization.id, year=YEAR, month=MONTH)
    chain = {row["id"]: row for row in _section(data, "revenue")["chain"]}
    assert Decimal(chain["due"]["value"]) == Decimal(summary["invoiced"]["amount_due"])
    assert Decimal(chain["collected"]["value"]) == Decimal(summary["collected_for_month"]["total"])
    assert _section(data, "pnl")["current"]["operating_profit"] == pnl["operating_profit"]

    source = (
        org.client()
        .get(
            "/api/v1/reports/pack/source",
            {"year": YEAR, "month": MONTH, "key": chain["collected"]["source"]},
        )
        .json()["data"]
    )
    assert sum(Decimal(row["amount"]) for row in source["rows"]) == Decimal(
        chain["collected"]["value"]
    )


# --- Eksport, log, huquq ---


def test_the_pack_prints_to_pdf_and_excel(org: Any):
    from openpyxl import load_workbook

    _issue(org, _children(org, 1))
    client = org.client()
    pdf = client.get("/api/v1/reports/pack/pdf", {"year": YEAR, "month": MONTH})
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"
    assert b"".join(pdf.streaming_content).startswith(b"%PDF")

    xlsx = client.get("/api/v1/reports/pack/xlsx", {"year": YEAR, "month": MONTH})
    assert xlsx.status_code == 200
    workbook = load_workbook(io.BytesIO(b"".join(xlsx.streaming_content)))
    assert len(workbook.sheetnames) >= 16


def test_opening_the_pack_is_logged(org: Any):
    from apps.audit.models import AuditLog

    org.client().get("/api/v1/reports/pack", {"year": YEAR, "month": MONTH})
    with _ctx(org):
        assert AuditLog.objects.filter(entity_type="report_pack", action="view").exists()


def test_a_cashier_cannot_open_the_pack(org: Any):
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
    assert client.get("/api/v1/reports/pack", {"year": YEAR, "month": MONTH}).status_code == 403


@pytest.mark.tenancy
def test_another_tenants_snapshot_never_shows(org: Any, tenant_b: Any):
    org.client().post(
        "/api/v1/reports/pack/snapshot", {"year": YEAR, "month": MONTH}, format="json"
    )
    versions = (
        tenant_b.client()
        .get("/api/v1/reports/pack/versions", {"year": YEAR, "month": MONTH})
        .json()["data"]
    )
    assert versions == []


# --- 20: tezlik ---


def test_20_a_month_of_300_children_and_3000_operations_builds_in_under_3_seconds(org: Any):
    from apps.cash.models import CashMovement
    from apps.finance.models import Invoice, InvoiceLine, PaymentAllocation

    kids = _children(org, 300)
    with _ctx(org):
        till = CashAccount.objects.get(branch=org.branch, kind="cash", is_active=True)
        invoices = Invoice.objects.bulk_create(
            [
                Invoice(
                    organization=org.organization,
                    branch=org.branch,
                    child=kid,
                    number=f"INV-202609-{index:04d}",
                    period_year=YEAR,
                    period_month=MONTH,
                    issued_date=date(2026, 9, 1),
                    due_date=date(2026, 9, 10),
                    amount_due=FEE,
                    amount_paid=FEE,
                    status="paid",
                )
                for index, kid in enumerate(kids)
            ]
        )
        InvoiceLine.objects.bulk_create(
            [
                InvoiceLine(
                    invoice=invoice,
                    kind="base",
                    description="Asosiy",
                    unit_amount=FEE,
                    line_total=FEE,
                )
                for invoice in invoices
            ]
        )
        share = (FEE / 10).quantize(Decimal("0.01"))
        payments = Payment.objects.bulk_create(
            [
                Payment(
                    organization=org.organization,
                    branch=org.branch,
                    child=invoice.child,
                    amount=share,
                    method="cash",
                    paid_at=_at(date(2026, 9, 1 + part)),
                )
                for invoice in invoices
                for part in range(10)
            ]
        )
        PaymentAllocation.objects.bulk_create(
            [
                PaymentAllocation(
                    organization=org.organization,
                    branch=org.branch,
                    payment=payment,
                    invoice=invoices[index // 10],
                    amount=share,
                    allocated_at=payment.paid_at,
                )
                for index, payment in enumerate(payments)
            ]
        )
        CashMovement.objects.bulk_create(
            [
                CashMovement(
                    organization=org.organization,
                    branch=org.branch,
                    cash_account=till,
                    direction="in",
                    amount=payment.amount,
                    source_type="payment",
                    source_id=payment.id,
                    occurred_at=payment.paid_at,
                )
                for payment in payments
            ]
        )

    # Haqiqiy bazada statistika autovacuum bilan yangilanadi; bulk yozilgan
    # test jadvallarida esa yo'q — rejalashtiruvchi adashmasin.
    from django.db import connection as db

    with db.cursor() as cursor:
        cursor.execute(
            "ANALYZE invoice, invoice_line, payment, payment_allocation, cash_movement, child"
        )

    started = clock.perf_counter()
    _build(org)
    assert clock.perf_counter() - started < 3.0


def test_a_reports_reader_without_payroll_rights_cannot_open_the_pack(org: Any):
    """Menejerda `reports.read` bor, `payroll.read` yo'q — paket yopiq."""
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with _ctx(org):
        user = User.objects.create_user(
            email="menejer@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Menejer",
            organization=org.organization,
            role=org.role("manager"),
            branch=org.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/v1/reports/pack", {"year": YEAR, "month": MONTH}).status_code == 403
