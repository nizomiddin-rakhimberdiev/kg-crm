"""
Qonunchilik sozlamalari — 1-qism (Bosqich 13.8a, brif §9; testlar 13, 14).

* Fiskal chek: naqd va karta (terminal) to'lovida bog'cha chek beradi;
  Click/Payme chekini to'lov tizimi beradi. Har to'lovda chek holati —
  raqam yoki QR, kim bergani, turi (avans / sotuv / kredit). Qoplanganlik
  nazorati "Diqqat" va tekshiruvda.
* To'lovchi — ota-onaning ish beruvchisi (nomi, STIR); bank ko'chirmasidan
  o'zi aniqlanadi.
* Ota-onaga yillik to'lovlar ma'lumotnomasi (PDF), JShDS imtiyozi limiti bilan.
"""

from __future__ import annotations

import io
import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from openpyxl import Workbook

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Payment, TariffPlan

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()
FEE = Decimal("3050000")


def _ctx(tenant: Any) -> Any:
    return organization_context(tenant.organization.id)


def _setting(tenant: Any, key: str, value: Any) -> None:
    from apps.settings_app.services import set_setting

    with _ctx(tenant):
        set_setting(organization=tenant.organization, key=key, value=value)


def _child(tenant: Any, first: str = "Ali", last: str = "Valiyev") -> Child:
    with _ctx(tenant):
        tariff, _ = TariffPlan.objects.get_or_create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Asosiy",
            defaults={"amount": FEE},
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=first,
            last_name=last,
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff=tariff,
            is_existing_client=True,
            enrolled_on=date(2025, 9, 1),
        )


def _pay(tenant: Any, child: Child, method: str, amount: Decimal, day: date = TODAY) -> Payment:
    with _ctx(tenant):
        return finance.record_payment(
            child=child,
            amount=amount,
            method=method,
            paid_at=None if day == TODAY else timezone.make_aware(datetime.combine(day, time(10))),
            backdate_reason="Tarix",
        )


def _attention(tenant: Any) -> list[dict[str, Any]]:
    from apps.intelligence import control

    with _ctx(tenant):
        return control.attention(
            organization_id=tenant.organization.id, year=TODAY.year, month=TODAY.month
        )


def _check(tenant: Any, key: str) -> dict[str, Any]:
    from apps.intelligence import control

    with _ctx(tenant):
        rows = control.checks(
            organization_id=tenant.organization.id, year=TODAY.year, month=TODAY.month
        )
    return next(row for row in rows if row["id"] == key)


@pytest.fixture
def fiscal_on(tenant_a: Any) -> Any:
    _setting(tenant_a, "fiscal.control_from", TODAY.replace(day=1).isoformat())
    return tenant_a


# --- 13: fiskal chek ---


def test_13_a_cash_payment_without_a_fiscal_receipt_needs_attention(fiscal_on: Any):
    _pay(fiscal_on, _child(fiscal_on), "cash", FEE)

    rules = [item["rule"] for item in _attention(fiscal_on)]
    assert "payment_without_fiscal" in rules
    assert _check(fiscal_on, "fiscal_receipts")["status"] == "fail"


def test_13_a_click_payment_is_covered_by_the_providers_receipt(fiscal_on: Any):
    _pay(fiscal_on, _child(fiscal_on), "click", FEE)

    assert "payment_without_fiscal" not in [item["rule"] for item in _attention(fiscal_on)]
    assert _check(fiscal_on, "fiscal_receipts")["status"] == "ok"


def test_recording_the_receipt_clears_the_attention(fiscal_on: Any):
    payment = _pay(fiscal_on, _child(fiscal_on), "terminal", FEE)
    response = fiscal_on.client().post(
        f"/api/v1/payments/{payment.id}/fiscal",
        {"number": "UZ-000123", "qr": "https://ofd.soliq.uz/check?t=abc"},
        format="json",
    )
    assert response.status_code == 201, response.content
    data = response.json()["data"]
    assert data["issuer"] == "kindergarten"
    assert data["kind"] in ("advance", "sale", "credit")

    assert "payment_without_fiscal" not in [item["rule"] for item in _attention(fiscal_on)]
    assert _check(fiscal_on, "fiscal_receipts")["status"] == "ok"

    detail = fiscal_on.client().get(f"/api/v1/payments/{payment.id}").json()["data"]
    assert detail["fiscal"]["number"] == "UZ-000123"


def test_a_receipt_needs_a_number_or_a_qr(fiscal_on: Any):
    payment = _pay(fiscal_on, _child(fiscal_on), "cash", FEE)
    response = fiscal_on.client().post(
        f"/api/v1/payments/{payment.id}/fiscal", {"number": "", "qr": ""}, format="json"
    )
    assert response.status_code == 422


def test_the_receipt_kind_follows_the_month_paid_for(fiscal_on: Any):
    from apps.finance.fiscal import receipt_kind

    child = _child(fiscal_on)
    month = TODAY.replace(day=1)
    previous = (month - timedelta(days=1)).replace(day=1)
    following = (month + timedelta(days=32)).replace(day=1)
    with _ctx(fiscal_on):
        old = finance.issue_invoice(
            child=child, period_year=previous.year, period_month=previous.month
        )
        now = finance.issue_invoice(child=child, period_year=month.year, period_month=month.month)
        ahead = finance.issue_invoice(
            child=child, period_year=following.year, period_month=following.month
        )
    _setting(fiscal_on, "finance.backdate_days", 400)
    for invoice in (old, now, ahead):
        with _ctx(fiscal_on):
            payment = finance.record_payment(
                child=child,
                amount=invoice.amount_due,
                method="cash",
                invoice=invoice,
                allocation_reason="Test",
            )
            assert receipt_kind(payment) == {old: "credit", now: "sale", ahead: "advance"}[invoice]


def test_payments_before_the_control_date_are_not_counted(tenant_a: Any):
    _setting(tenant_a, "fiscal.control_from", (TODAY + timedelta(days=1)).isoformat())
    _pay(tenant_a, _child(tenant_a), "cash", FEE)
    assert "payment_without_fiscal" not in [item["rule"] for item in _attention(tenant_a)]


def test_the_pack_shows_fiscal_coverage(fiscal_on: Any):
    from apps.reports import pack

    child = _child(fiscal_on)
    _pay(fiscal_on, child, "cash", FEE)
    _pay(fiscal_on, child, "click", FEE)
    with _ctx(fiscal_on):
        data = pack.build(
            organization_id=fiscal_on.organization.id, year=TODAY.year, month=TODAY.month
        )
    taxes = next(section for section in data["sections"] if section["key"] == "taxes")
    coverage = taxes["fiscal_coverage"]
    assert coverage["required"] == 1
    assert coverage["covered"] == 0
    assert coverage["provider"] == 1


@pytest.mark.tenancy
def test_another_tenant_cannot_record_a_receipt(fiscal_on: Any, tenant_b: Any):
    payment = _pay(fiscal_on, _child(fiscal_on), "cash", FEE)
    response = tenant_b.client().post(
        f"/api/v1/payments/{payment.id}/fiscal", {"number": "X-1"}, format="json"
    )
    assert response.status_code == 404


# --- 14: ish beruvchi to'lovchi ---


def _statement(rows: list[list[Any]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Sana", "Debet", "Kredit", "Toʻlov maqsadi", "Kontragent", "STIR", "Hujjat №"])
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_14_an_employer_transfer_becomes_an_employer_payment(tenant_a: Any):
    from apps.cash.models import CashAccount

    child = _child(tenant_a, "Malika", "Karimova")
    with _ctx(tenant_a):
        bank = CashAccount.objects.get(branch=tenant_a.branch, kind="bank", is_active=True)
    day = TODAY - timedelta(days=2)
    response = tenant_a.client().post(
        "/api/v1/bank-statements",
        {
            "file": SimpleUploadedFile(
                "v.xlsx",
                _statement(
                    [
                        [
                            day,
                            0,
                            3050000,
                            "Karimova Malika uchun bogʻcha toʻlovi",
                            "UZTELECOM AJ",
                            "201234567",
                            "77",
                        ]
                    ]
                ),
            ),
            "cash_account_id": str(bank.id),
            "mapping": json.dumps(
                {
                    "date": "Sana",
                    "debit": "Debet",
                    "credit": "Kredit",
                    "purpose": "Toʻlov maqsadi",
                    "counterparty": "Kontragent",
                    "counterparty_tin": "STIR",
                    "reference": "Hujjat №",
                }
            ),
        },
        format="multipart",
    )
    assert response.status_code == 201, response.content
    with _ctx(tenant_a):
        payment = Payment.objects.get(child=child)
    assert payment.payer_kind == "employer"
    assert payment.payer_name == "UZTELECOM AJ"
    assert payment.payer_tin == "201234567"


def test_an_employer_payer_can_be_entered_by_hand(tenant_a: Any):
    child = _child(tenant_a)
    client = tenant_a.client()
    bad = client.post(
        "/api/v1/payments",
        {
            "child_id": str(child.id),
            "amount": "1000000",
            "method": "bank_transfer",
            "payer_kind": "employer",
            "payer_org": "Artel MChJ",
            "payer_tin": "12ab",
        },
        format="json",
    )
    assert bad.status_code in (400, 422)
    good = client.post(
        "/api/v1/payments",
        {
            "child_id": str(child.id),
            "amount": "1000000",
            "method": "bank_transfer",
            "payer_kind": "employer",
            "payer_org": "Artel MChJ",
            "payer_tin": "301234567",
        },
        format="json",
    )
    assert good.status_code == 201, good.content
    assert good.json()["data"]["payer_kind"] == "employer"
    assert good.json()["data"]["payer_name"] == "Artel MChJ"


# --- Yillik ma'lumotnoma ---


def test_14_the_parent_gets_an_annual_statement(tenant_a: Any):
    from apps.finance.statement import annual_statement

    child = _child(tenant_a)
    _setting(tenant_a, "finance.backdate_days", 400)
    year = TODAY.year
    _pay(tenant_a, child, "cash", Decimal("3500000"), date(year, 1, 10))
    _pay(tenant_a, child, "cash", Decimal("1000000"), date(year, 2, 10))
    _pay(tenant_a, child, "click", Decimal("500000"), date(year, 2, 20))

    with _ctx(tenant_a):
        data = annual_statement(child=child, year=year)
    months = {row["month"]: row for row in data["months"]}
    assert Decimal(months[1]["paid"]) == Decimal("3500000")
    assert Decimal(months[1]["exempt"]) == Decimal("3000000")
    assert Decimal(months[2]["paid"]) == Decimal("1500000")
    assert Decimal(data["total_paid"]) == Decimal("5000000")
    assert Decimal(data["total_exempt"]) == Decimal("4500000")

    pdf = tenant_a.client().get(f"/api/v1/children/{child.id}/annual-statement", {"year": year})
    assert pdf.status_code == 200
    assert pdf["Content-Type"] == "application/pdf"


@pytest.mark.tenancy
def test_another_tenants_child_has_no_statement(tenant_a: Any, tenant_b: Any):
    child = _child(tenant_a)
    response = tenant_b.client().get(
        f"/api/v1/children/{child.id}/annual-statement", {"year": TODAY.year}
    )
    assert response.status_code == 404


# --- 13.8b: soliq presetlari va taqvimi ---


def _employee_run(tenant: Any, salary: str, year: int, month: int) -> Any:
    from apps.hr.models import Employee
    from apps.payroll import services as payroll

    with _ctx(tenant):
        Employee.objects.get_or_create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Nilufar",
            last_name="Sodiqova",
            # Soliq rasmiy oylikdan (ADR-18) — hammasi rasmiy.
            defaults={
                "hire_date": date(2025, 1, 10),
                "base_salary": Decimal(salary),
                "official_salary": Decimal(salary),
            },
        )
        run = payroll.create_run(
            organization=tenant.organization,
            branch=tenant.branch,
            period_year=year,
            period_month=month,
        )
        payroll.finalize_run(run=run)
        return run


def test_the_pq403_preset_sets_the_rates(tenant_a: Any):
    from apps.settings_app.services import get_setting

    client = tenant_a.client()
    presets = client.get("/api/v1/settings/tax-presets").json()["data"]
    assert {row["id"] for row in presets["presets"]} >= {"pq403", "general", "turnover"}
    response = client.post("/api/v1/settings/tax-presets/apply", {"preset": "pq403"}, format="json")
    assert response.status_code == 200, response.content
    with _ctx(tenant_a):
        assert str(get_setting(key="tax.regime")) == "pq403"
        assert Decimal(str(get_setting(key="payroll.income_tax_rate"))) == 12
        assert Decimal(str(get_setting(key="payroll.pension_rate"))) == Decimal("0.1")
        assert Decimal(str(get_setting(key="payroll.social_tax_rate"))) == 12


def test_an_unknown_preset_is_refused(tenant_a: Any):
    response = tenant_a.client().post(
        "/api/v1/settings/tax-presets/apply", {"preset": "offshore"}, format="json"
    )
    assert response.status_code == 422


def test_the_tax_calendar_follows_the_payroll_run(tenant_a: Any):
    tenant_a.client().post("/api/v1/settings/tax-presets/apply", {"preset": "pq403"}, format="json")
    previous = (TODAY.replace(day=1) - timedelta(days=1)).replace(day=1)
    _employee_run(tenant_a, "4000000", previous.year, previous.month)

    rows = tenant_a.client().get("/api/v1/reports/tax-calendar", {"year": previous.year})
    assert rows.status_code == 200, rows.content
    items = {(row["kind"], row["period"]): row for row in rows.json()["data"]["items"]}
    period = f"{previous.year}-{previous.month:02d}"
    assert Decimal(items[("income_tax", period)]["amount"]) == Decimal("480000")
    assert Decimal(items[("pension", period)]["amount"]) == Decimal("4000")
    assert Decimal(items[("social_tax", period)]["amount"]) == Decimal("480000")
    due = items[("social_tax", period)]["due_date"]
    assert due == date(TODAY.year, TODAY.month, 15).isoformat()
    assert items[("social_tax", period)]["status"] in ("upcoming", "due", "overdue")


def test_paying_an_obligation_moves_money_and_closes_it(tenant_a: Any):
    from apps.cash.models import CashAccount, MoneyOperation

    tenant_a.fund("10000000", kind="bank")
    tenant_a.client().post("/api/v1/settings/tax-presets/apply", {"preset": "pq403"}, format="json")
    previous = (TODAY.replace(day=1) - timedelta(days=1)).replace(day=1)
    _employee_run(tenant_a, "4000000", previous.year, previous.month)
    client = tenant_a.client()
    items = client.get("/api/v1/reports/tax-calendar", {"year": previous.year}).json()["data"][
        "items"
    ]
    social = next(row for row in items if row["kind"] == "social_tax")
    with _ctx(tenant_a):
        bank = CashAccount.objects.get(branch=tenant_a.branch, kind="bank", is_active=True)
    paid = client.post(
        f"/api/v1/reports/tax-calendar/{social['id']}/pay",
        {"cash_account_id": str(bank.id)},
        format="json",
    )
    assert paid.status_code == 200, paid.content
    assert paid.json()["data"]["status"] == "paid"
    with _ctx(tenant_a):
        operation = MoneyOperation.objects.get(kind="tax_payment")
    assert operation.subtype == "social_tax"
    assert operation.amount == Decimal("480000")

    again = client.post(
        f"/api/v1/reports/tax-calendar/{social['id']}/pay",
        {"cash_account_id": str(bank.id)},
        format="json",
    )
    assert again.status_code == 422


def test_a_dividend_creates_its_tax_obligation(tenant_a: Any):
    from apps.cash import services as cash
    from apps.cash.models import CashAccount

    tenant_a.fund("100000000", kind="bank")
    with _ctx(tenant_a):
        bank = CashAccount.objects.get(branch=tenant_a.branch, kind="bank", is_active=True)
        cash.record_operation(
            kind="owner_draw",
            subtype="dividend",
            account=bank,
            amount=Decimal("60000000"),
            occurred_on=TODAY,
            reason="Dividend",
        )
    items = (
        tenant_a.client()
        .get("/api/v1/reports/tax-calendar", {"year": TODAY.year})
        .json()["data"]["items"]
    )
    dividend = next(row for row in items if row["kind"] == "dividend_tax")
    assert Decimal(dividend["amount"]) == Decimal("3000000")


def test_tax_reminders_go_once_before_and_once_after(tenant_a: Any, monkeypatch: Any):
    from types import SimpleNamespace

    from apps.accounts.models import User
    from apps.intelligence import alerts
    from apps.reports import tasks

    sent: list[str] = []
    monkeypatch.setattr(alerts, "_send", lambda chat, text: sent.append(text))
    monkeypatch.setattr(alerts, "transaction", SimpleNamespace(on_commit=lambda fn: fn()))
    with _ctx(tenant_a):
        User.objects.filter(pk=tenant_a.owner.pk).update(telegram_chat_id="9001")
    tenant_a.client().post("/api/v1/settings/tax-presets/apply", {"preset": "pq403"}, format="json")
    previous = (TODAY.replace(day=1) - timedelta(days=1)).replace(day=1)
    _employee_run(tenant_a, "4000000", previous.year, previous.month)
    due = date(TODAY.year, TODAY.month, 15)

    monkeypatch.setattr(tasks.timezone, "localdate", lambda: due - timedelta(days=3))
    assert tasks.remind_taxes()["reminded"] >= 1
    count = len(sent)
    assert tasks.remind_taxes()["reminded"] == 0
    monkeypatch.setattr(tasks.timezone, "localdate", lambda: due + timedelta(days=1))
    assert tasks.remind_taxes()["reminded"] >= 1
    assert len(sent) > count
    assert tasks.remind_taxes()["reminded"] == 0


@pytest.mark.tenancy
def test_another_tenants_obligation_cannot_be_paid(tenant_a: Any, tenant_b: Any):
    from apps.cash.models import CashAccount

    tenant_a.client().post("/api/v1/settings/tax-presets/apply", {"preset": "pq403"}, format="json")
    previous = (TODAY.replace(day=1) - timedelta(days=1)).replace(day=1)
    _employee_run(tenant_a, "4000000", previous.year, previous.month)
    items = (
        tenant_a.client()
        .get("/api/v1/reports/tax-calendar", {"year": previous.year})
        .json()["data"]["items"]
    )
    with organization_context(tenant_b.organization.id):
        bank = CashAccount.objects.get(branch=tenant_b.branch, kind="bank", is_active=True)
    response = tenant_b.client().post(
        f"/api/v1/reports/tax-calendar/{items[0]['id']}/pay",
        {"cash_account_id": str(bank.id)},
        format="json",
    )
    assert response.status_code == 404


def test_state_support_is_other_income(tenant_a: Any):
    from apps.cash.models import OPERATION_SUBTYPES, OperationKind

    assert {"subsidy", "state_salary", "utility_compensation"} <= set(
        OPERATION_SUBTYPES[OperationKind.OTHER_INCOME]
    )


# --- 13.8c: buxgalter jurnali ---


def _journal(tenant: Any, year: int = TODAY.year, month: int = TODAY.month) -> dict[str, Any]:
    from apps.reports import journal

    with _ctx(tenant):
        return journal.build(organization_id=tenant.organization.id, year=year, month=month)


def _turnover(data: dict[str, Any], account: str) -> Decimal:
    debit = sum(
        (Decimal(row["amount"]) for row in data["lines"] if row["debit"] == account), Decimal(0)
    )
    credit = sum(
        (Decimal(row["amount"]) for row in data["lines"] if row["credit"] == account), Decimal(0)
    )
    return debit - credit


def test_the_journal_uses_the_default_account_codes(tenant_a: Any):
    child = _child(tenant_a)
    with _ctx(tenant_a):
        finance.issue_invoice(child=child, period_year=TODAY.year, period_month=TODAY.month)
    _pay(tenant_a, child, "cash", Decimal("2000000"))

    lines = _journal(tenant_a)["lines"]
    assert any(
        row["debit"] == "4010" and row["credit"] == "9030" and Decimal(row["amount"]) == FEE
        for row in lines
    )
    assert any(
        row["debit"] == "5010"
        and row["credit"] == "4010"
        and Decimal(row["amount"]) == Decimal("2000000")
        for row in lines
    )


def test_an_advance_goes_to_6310(tenant_a: Any):
    _pay(tenant_a, _child(tenant_a), "cash", Decimal("1500000"))
    lines = _journal(tenant_a)["lines"]
    assert any(row["debit"] == "5010" and row["credit"] == "6310" for row in lines)


def test_the_pot_accounts_match_the_money_that_moved(tenant_a: Any):
    from apps.cash import services as cash
    from apps.cash.models import CashAccount, CashMovement
    from apps.expenses.models import Expense, ExpenseCategory
    from apps.expenses.services import approve_expense

    tenant_a.fund("50000000", kind="all")
    child = _child(tenant_a)
    with _ctx(tenant_a):
        finance.issue_invoice(child=child, period_year=TODAY.year, period_month=TODAY.month)
    _pay(tenant_a, child, "cash", Decimal("5000000"))
    _pay(tenant_a, child, "terminal", Decimal("700000"))
    with _ctx(tenant_a):
        till = CashAccount.objects.get(branch=tenant_a.branch, kind="cash", is_active=True)
        bank = CashAccount.objects.get(branch=tenant_a.branch, kind="bank", is_active=True)
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Kommunal",
            account_code="9420",
        )
        expense = Expense.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            amount=Decimal("800000"),
            expense_date=TODAY,
            cash_account=bank,
            receipt="r.png",
        )
        approve_expense(expense=expense, approved_by=tenant_a.owner)
        cash.transfer(source=till, target=bank, amount=Decimal("3000000"))

    data = _journal(tenant_a)
    with _ctx(tenant_a):
        start = timezone.make_aware(datetime.combine(TODAY.replace(day=1), time.min))
        moves = list(
            CashMovement.objects.filter(occurred_at__gte=start).select_related("cash_account")
        )

    def net(kind: str) -> Decimal:
        rows = [m for m in moves if m.cash_account.kind == kind]
        inn = sum((m.amount for m in rows if m.direction == "in"), Decimal(0))
        out = sum((m.amount for m in rows if m.direction == "out"), Decimal(0))
        return inn - out

    assert net("cash") != 0
    assert _turnover(data, "5010") == net("cash")
    assert _turnover(data, "5110") == net("bank")
    assert any(row["debit"] == "9420" and row["credit"] == "5110" for row in data["lines"])
    assert any(row["debit"] == "5110" and row["credit"] == "5010" for row in data["lines"])


def test_payroll_is_accrued_with_its_taxes(tenant_a: Any):
    tenant_a.client().post("/api/v1/settings/tax-presets/apply", {"preset": "pq403"}, format="json")
    _employee_run(tenant_a, "4000000", TODAY.year, TODAY.month)
    lines = _journal(tenant_a)["lines"]
    gross = next(row for row in lines if row["credit"] == "6710" and row["debit"] != "6410")
    assert Decimal(gross["amount"]) == Decimal("4000000")
    withheld = next(row for row in lines if row["debit"] == "6710" and row["credit"] == "6410")
    assert Decimal(withheld["amount"]) == Decimal("484000")


def test_the_mapping_is_a_setting(tenant_a: Any):
    _setting(tenant_a, "accounts.cash", "5011")
    _pay(tenant_a, _child(tenant_a), "cash", Decimal("100000"))
    lines = _journal(tenant_a)["lines"]
    assert any(row["debit"] == "5011" for row in lines)
    assert not any(row["debit"] == "5010" for row in lines)


def test_the_journal_downloads_as_excel_and_csv(tenant_a: Any):
    _pay(tenant_a, _child(tenant_a), "cash", Decimal("100000"))
    client = tenant_a.client()
    period = {"year": TODAY.year, "month": TODAY.month}
    data = client.get("/api/v1/reports/journal", period)
    assert data.status_code == 200
    assert data.json()["data"]["lines"]
    xlsx = client.get("/api/v1/reports/journal", {**period, "file": "xlsx"})
    assert xlsx.status_code == 200
    assert "spreadsheetml" in xlsx["Content-Type"]
    csv = client.get("/api/v1/reports/journal", {**period, "file": "csv"})
    assert csv.status_code == 200
    assert b"5010" in b"".join(csv.streaming_content)


@pytest.mark.tenancy
def test_another_tenants_journal_is_empty(tenant_a: Any, tenant_b: Any):
    _pay(tenant_a, _child(tenant_a), "cash", Decimal("100000"))
    data = (
        tenant_b.client()
        .get("/api/v1/reports/journal", {"year": TODAY.year, "month": TODAY.month})
        .json()["data"]
    )
    assert data["lines"] == []


def test_the_cash_desk_batch_takes_an_employer_payer(tenant_a: Any):
    child = _child(tenant_a)
    response = tenant_a.client().post(
        "/api/v1/payments/batch",
        {
            "child_id": str(child.id),
            "lines": [{"method": "bank_transfer", "amount": "500000"}],
            "payer_kind": "employer",
            "payer_org": "Artel MChJ",
            "payer_tin": "301234567",
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    assert response.json()["data"][0]["payer_kind"] == "employer"
    assert response.json()["data"][0]["payer_tin"] == "301234567"
