"""
Import — tizimga o'tayotgan bog'cha uchun (PLAN 7.6 / 7.8).

Import bir martalik ish emas: bog'cha Radix'ga o'tayotganda butun
ro'yxatini shu yo'l bilan kiritadi. Shuning uchun undagi bolalar
sukut bo'yicha MAVJUD mijoz (birinchi oyi proporsional emas) va
ularning eski qarzi ham ko'chib o'tadi — aks holda bog'cha qarzlarni
qo'lda qaytadan kiritishga majbur bo'lardi.
"""

from __future__ import annotations

import io
from decimal import Decimal

import pytest
from openpyxl import Workbook, load_workbook

from apps.children.importer import build_template, import_children
from apps.children.models import Child, Group
from apps.core.tenancy import organization_context
from apps.finance.balance import child_balance
from apps.finance.models import TariffPlan
from apps.finance.selectors import debtor_queryset

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

HEADERS = [
    "Familiya",
    "Ism",
    "Tug'ilgan sana",
    "Jinsi",
    "Otasining ismi",
    "Guruh",
    "Tarif",
    "Mijoz",
    "Qarzdorlik",
    "Ota-ona",
    "Telefon",
]


def _sheet(rows: list[list[str]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _run(tenant, rows: list[list[str]]):
    with organization_context(tenant.organization.id):
        return import_children(
            organization=tenant.organization,
            branch=tenant.branch,
            file_bytes=_sheet(rows),
            dry_run=False,
        )


def _row(last: str, *, kind: str = "", debt: str = "", tariff: str = "", group: str = ""):
    return [last, "Ali", "14.03.2021", "o'g'il", "", group, tariff, kind, debt, "", ""]


class TestTemplate:
    def test_it_offers_the_kindergartens_own_groups_and_tariffs(self):
        content = build_template(groups=["Quyoshcha", "Kamalak"], tariffs=["Full", "Yarim kun"])
        sheet = load_workbook(io.BytesIO(content)).active
        formulas = [v.formula1 for v in sheet.data_validations.dataValidation]
        assert '"Quyoshcha,Kamalak"' in formulas
        assert '"Full,Yarim kun"' in formulas
        assert '"mavjud,yangi"' in formulas

    def test_a_very_long_list_falls_back_to_plain_text(self):
        """Excel ro'yxati 255 belgi bilan cheklangan — yarim ishlagandan ko'ra yo'q."""
        many = [f"Guruh raqami {n:02d}" for n in range(40)]
        sheet = load_workbook(io.BytesIO(build_template(groups=many))).active
        formulas = [v.formula1 for v in sheet.data_validations.dataValidation]
        assert not any("Guruh raqami" in f for f in formulas)

    def test_the_debt_column_starts_at_zero_in_the_example(self):
        sheet = load_workbook(io.BytesIO(build_template())).active
        assert sheet.cell(row=1, column=9).value == "Qarzdorlik"
        assert str(sheet.cell(row=2, column=9).value) == "0"

    def test_the_example_rows_say_existing(self):
        sheet = load_workbook(io.BytesIO(build_template())).active
        assert sheet.cell(row=1, column=8).value == "Mijoz"
        assert sheet.cell(row=2, column=8).value == "mavjud"


class TestImport:
    def test_an_imported_child_defaults_to_an_existing_client(self, tenant_a):
        _run(tenant_a, [_row("Valiyev")])
        with organization_context(tenant_a.organization.id):
            assert Child.objects.get().is_existing_client is True

    def test_the_sheet_can_still_say_new(self, tenant_a):
        _run(tenant_a, [_row("Valiyev", kind="yangi")])
        with organization_context(tenant_a.organization.id):
            assert Child.objects.get().is_existing_client is False

    def test_the_old_debt_lands_in_the_debtors_list(self, tenant_a):
        _run(tenant_a, [_row("Valiyev", debt="1200000"), _row("Karimov", debt="0")])
        with organization_context(tenant_a.organization.id):
            debtors = {c.last_name: child_balance(c).balance for c in debtor_queryset()}
        assert debtors == {"Valiyev": Decimal("1200000.00")}

    def test_the_tariff_is_matched_by_name_whatever_the_case(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            TariffPlan.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Full",
                amount=Decimal("3050000"),
            )
        _run(tenant_a, [_row("Valiyev", tariff="full")])
        with organization_context(tenant_a.organization.id):
            assert Child.objects.get().tariff.name == "Full"

    def test_an_unknown_tariff_is_simply_left_empty(self, tenant_a):
        _run(tenant_a, [_row("Valiyev", tariff="Yoʻq tarif")])
        with organization_context(tenant_a.organization.id):
            assert Child.objects.get().tariff_id is None

    def test_a_bad_debt_value_is_reported_not_guessed(self, tenant_a):
        report = _run(tenant_a, [_row("Valiyev", debt="ikki million")])
        assert report.created == 0
        assert any("Qarzdorlik" in error.message for error in report.errors)

    def test_a_negative_debt_is_refused(self, tenant_a):
        report = _run(tenant_a, [_row("Valiyev", debt="-500000")])
        assert report.created == 0
        assert report.errors

    def test_the_group_still_works(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            Group.objects.create(
                organization=tenant_a.organization, branch=tenant_a.branch, name="Quyoshcha"
            )
        _run(tenant_a, [_row("Valiyev", group="Quyoshcha")])
        with organization_context(tenant_a.organization.id):
            child = Child.objects.get()
            assert child.enrollments.filter(group__name="Quyoshcha").exists()
