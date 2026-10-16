"""
Bank ko'chirmasi importi va avtomatik moslashtirish (Bosqich 13.3d,
brif §4, testlar 8, 9, 14).

Bank-klient eksporti bankdan bankka farq qiladi, shuning uchun ustunlar
MOSLASHTIRILADI (sana, summa yoki debet/kredit, maqsad, kontragent).
Keyin har bir qator o'z hujjatini topadi:

* Click/Payme/terminal tushumi → yo'ldagi to'lovlar (kunlik reestr);
* ota-ona o'tkazmasi → mavjud to'lov, yo'q bo'lsa shartnoma raqami yoki
  bola ismi bo'yicha YANGI to'lov;
* chiqim qatori → xarajat, egaga to'lov, soliq, o'tkazma;
* qolgani — "moslashtirilmagan" navbatda.
"""

from __future__ import annotations

import io
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from openpyxl import Workbook

from apps.cash.models import BankStatementLine, CashAccount
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory
from apps.finance import services as finance
from apps.finance.models import Payment

pytestmark = pytest.mark.django_db

URL = "/api/v1/bank-statements"
TODAY = timezone.localdate()
D1 = TODAY - timedelta(days=3)
D2 = TODAY - timedelta(days=2)

HEADERS = ["Sana", "Debet", "Kredit", "Toʻlov maqsadi", "Kontragent", "Hujjat №"]
MAPPING = {
    "date": "Sana",
    "debit": "Debet",
    "credit": "Kredit",
    "purpose": "Toʻlov maqsadi",
    "counterparty": "Kontragent",
    "reference": "Hujjat №",
}


def _xlsx(rows: list[list[Any]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["AT Kapitalbank — koʻchirma"])
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _bank(tenant: Any) -> CashAccount:
    with organization_context(tenant.organization.id):
        from apps.cash import services as cash

        cash.ensure_branch_accounts(branch=tenant.branch)
        return CashAccount.objects.get(branch=tenant.branch, kind="bank", is_active=True)


def _upload(tenant: Any, rows: list[list[Any]], **extra: Any) -> Any:
    import json

    return tenant.client().post(
        URL,
        {
            "file": SimpleUploadedFile("vypiska.xlsx", _xlsx(rows)),
            "cash_account_id": str(_bank(tenant).id),
            "mapping": json.dumps(MAPPING),
            **extra,
        },
        format="multipart",
    )


def _child(tenant: Any, first: str = "Ali", last: str = "Valiyev") -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=first,
            last_name=last,
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


def _pay(tenant: Any, method: str, amount: str, day: date, child: Child | None = None) -> Payment:
    with organization_context(tenant.organization.id):
        return finance.record_payment(
            child=child or _child(tenant, "Soli"),
            amount=Decimal(amount),
            method=method,
            paid_at=timezone.make_aware(datetime.combine(day, time(10))),
        )


def _lines(tenant: Any, status: str | None = None) -> list[BankStatementLine]:
    with organization_context(tenant.organization.id):
        lines = BankStatementLine.objects.order_by("line_no")
        if status:
            lines = lines.filter(status=status)
        return list(lines)


# --- Ustunlarni moslashtirish ---


def test_the_preview_shows_the_columns_to_map(tenant_a: Any):
    response = tenant_a.client().post(
        f"{URL}/preview",
        {"file": SimpleUploadedFile("vypiska.xlsx", _xlsx([[D1, 0, 500000, "x", "y", "1"]]))},
        format="multipart",
    )
    assert response.status_code == 200, response.json()
    data = response.json()["data"]
    assert data["headers"] == HEADERS
    assert len(data["sample"]) == 1


def test_lines_are_imported_with_their_direction(tenant_a: Any):
    response = _upload(
        tenant_a,
        [
            [D1, 0, "1 200 000,00", "Nimadir", "Kimdir", "11"],
            [D1, "350000", 0, "Komissiya", "Bank", "12"],
        ],
    )
    assert response.status_code == 201, response.json()
    lines = _lines(tenant_a)
    assert [(line.direction, line.amount) for line in lines] == [
        ("in", Decimal("1200000")),
        ("out", Decimal("350000")),
    ]


def test_the_same_statement_twice_adds_nothing(tenant_a: Any):
    rows = [[D1, 0, 700000, "Nimadir", "Kimdir", "11"]]
    _upload(tenant_a, rows)
    second = _upload(tenant_a, rows)
    assert second.json()["data"]["skipped"] == 1
    assert len(_lines(tenant_a)) == 1


# --- 8: Click reestri yo'ldagi to'lovlarni yopadi ---


def test_8_a_click_registry_settles_that_days_payments(tenant_a: Any):
    for amount in ("1000000", "2000000"):
        _pay(tenant_a, "click", amount, D1)

    response = _upload(tenant_a, [[D2, 0, 2970000, "CLICK reestr", "CLICK LLC", "51"]])

    assert response.json()["data"]["matched"] == 1
    with organization_context(tenant_a.organization.id):
        assert not Payment.objects.filter(method="click", settlement__isnull=True).exists()
    assert _lines(tenant_a)[0].match_kind == "settlement"


# --- Ota-ona o'tkazmalari ---


def test_a_bank_transfer_already_entered_is_confirmed(tenant_a: Any):
    payment = _pay(tenant_a, "bank_transfer", "3050000", D1, _child(tenant_a))
    _upload(tenant_a, [[D1, 0, 3050000, "Bogʻcha toʻlovi", "Valiyev Vali", "7"]])
    line = _lines(tenant_a)[0]
    assert line.status == "matched"
    assert line.match_kind == "payment"
    assert line.matched_ids == [str(payment.id)]
    with organization_context(tenant_a.organization.id):
        assert Payment.objects.count() == 1


def test_14_an_employer_transfer_with_a_contract_number_finds_its_child(tenant_a: Any):
    from apps.contracts.models import Contract, ContractTemplate

    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        template = ContractTemplate.objects.create(
            organization=tenant_a.organization, name="Asosiy", body="x"
        )
        Contract.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            child=child,
            template=template,
            number="SH-0042",
            template_version=1,
            rendered_text="x",
        )

    _upload(
        tenant_a,
        [[D1, 0, 3050000, "Shartnoma SH-0042 boʻyicha bogʻcha toʻlovi", "UZTELECOM AJ", "9"]],
    )

    line = _lines(tenant_a)[0]
    assert line.status == "matched", line.note
    assert line.match_kind == "payment_created"
    with organization_context(tenant_a.organization.id):
        payment = Payment.objects.get(child=child)
    assert payment.method == "bank_transfer"
    assert payment.amount == Decimal("3050000")
    assert timezone.localtime(payment.paid_at).date() == D1


def test_a_unique_child_name_in_the_purpose_is_enough(tenant_a: Any):
    child = _child(tenant_a, "Malika", "Karimova")
    _upload(tenant_a, [[D1, 0, 1525000, "Karimova Malika uchun oktabr", "Karimov B", "3"]])
    with organization_context(tenant_a.organization.id):
        assert Payment.objects.filter(child=child).exists()


def test_two_children_with_that_name_wait_for_a_person(tenant_a: Any):
    _child(tenant_a, "Malika", "Karimova")
    _child(tenant_a, "Malika", "Karimova")
    _upload(tenant_a, [[D1, 0, 1525000, "Karimova Malika uchun", "Karimov B", "3"]])
    assert _lines(tenant_a)[0].status == "unmatched"


# --- Chiqim qatorlari ---


def test_a_debit_line_finds_its_expense(tenant_a: Any):
    tenant_a.fund(kind="all")
    bank = _bank(tenant_a)
    with organization_context(tenant_a.organization.id):
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Ijara"
        )
    tenant_a.client().post(
        "/api/v1/expenses",
        {
            "category_id": str(category.id),
            "amount": "8000000",
            "expense_date": D1.isoformat(),
            "cash_account_id": str(bank.id),
        },
        format="json",
    )
    _upload(tenant_a, [[D2, 8000000, 0, "Ijara oktabr", "Ijarachi MChJ", "4"]])
    line = _lines(tenant_a)[0]
    assert line.match_kind == "expense"


# --- Navbat ---


def test_unmatched_lines_can_be_ignored_or_turned_into_an_expense(tenant_a: Any):
    tenant_a.fund(kind="all")
    _upload(
        tenant_a,
        [
            [D1, 120000, 0, "Hisob xizmati", "Bank", "1"],
            [D1, 45000, 0, "SMS xabarnoma", "Bank", "2"],
        ],
    )
    first, second = _lines(tenant_a, "unmatched")
    with organization_context(tenant_a.organization.id):
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Bank xizmati"
        )

    created = tenant_a.client().post(
        f"{URL}/lines/{first.id}/expense", {"category_id": str(category.id)}, format="json"
    )
    ignored = tenant_a.client().post(
        f"{URL}/lines/{second.id}/ignore", {"note": "Keyingi oyda tekshiriladi"}, format="json"
    )

    assert created.status_code == 200, created.json()
    assert ignored.status_code == 200
    with organization_context(tenant_a.organization.id):
        expense = Expense.objects.get()
    assert expense.amount == Decimal("120000")
    assert expense.paid_on == D1
    assert _lines(tenant_a, "unmatched") == []


# --- 9: qoldiq ko'chirma bilan solishtiriladi ---


def test_9_a_statement_balance_that_differs_is_reported(tenant_a: Any):
    _pay(tenant_a, "bank_transfer", "1000000", D1)
    response = _upload(tenant_a, [[D1, 0, 1000000, "Toʻlov", "X", "1"]], closing_balance="1500000")
    data = response.json()["data"]
    assert Decimal(data["system_balance"]) == Decimal("1000000")
    assert Decimal(data["balance_difference"]) == Decimal("500000")


@pytest.mark.tenancy
def test_another_tenants_statement_is_404(tenant_a: Any, tenant_b: Any):
    statement_id = _upload(tenant_a, [[D1, 0, 700000, "X", "Y", "1"]]).json()["data"]["id"]
    assert tenant_b.client().get(f"{URL}/{statement_id}").status_code == 404
    line = _lines(tenant_a)[0]
    assert (
        tenant_b.client()
        .post(f"{URL}/lines/{line.id}/ignore", {"note": "x"}, format="json")
        .status_code
        == 404
    )
