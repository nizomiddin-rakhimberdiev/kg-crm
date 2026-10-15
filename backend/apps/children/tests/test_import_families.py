"""
Import va maʼlumot sifati (Bosqich 12.7, brif §7).

Excel'dan koʻchishda: toifa — rang emas, ustun; bir bola ikki xil
yozilgan (Oʻ/O', X/H, Boxodirova/Bohodirova/Bahodirova,
Doniyorov/Donyorov) — tizim buni oʻzi sezadi va TASDIQ soʻraydi;
oilalar vasiy telefoni orqali bogʻlanadi, telefon qanday yozilganidan
qatʼi nazar; bir oilada har xil narx — ogohlantirish.
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from openpyxl import Workbook

from apps.children.importer import import_children
from apps.children.models import Child, Guardian
from apps.core.tenancy import organization_context
from apps.finance.models import Discount, TariffPlan

pytestmark = pytest.mark.django_db

HEADERS = [
    "Familiya",
    "Ism",
    "Tug'ilgan sana",
    "Guruh",
    "Tarif",
    "Imtiyoz",
    "Imtiyoz sababi",
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


def _row(
    last: str,
    first: str = "Ali",
    *,
    born: str = "14.03.2021",
    group: str = "Quyoshcha",
    tariff: str = "Asosiy",
    benefit: str = "",
    reason: str = "",
    parent: str = "",
    phone: str = "",
) -> list[str]:
    return [last, first, born, group, tariff, benefit, reason, parent, phone]


@pytest.fixture
def tenant(tenant_a: Any) -> Any:
    with organization_context(tenant_a.organization.id):
        TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Asosiy",
            amount=Decimal("3050000"),
        )
        TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Aka-uka",
            amount=Decimal("2950000"),
        )
    return tenant_a


def _run(tenant: Any, rows: list[list[str]], *, dry_run: bool = False, decision: str = "") -> Any:
    with organization_context(tenant.organization.id):
        return import_children(
            organization=tenant.organization,
            branch=tenant.branch,
            file_bytes=_sheet(rows),
            dry_run=dry_run,
            duplicate_decision=decision,
        )


# --- Toifa ustuni ---


def test_the_benefit_column_becomes_a_typed_benefit_with_a_reason(tenant: Any):
    report = _run(
        tenant,
        [_row("Karimov", benefit="Xodim farzandi", reason="Oshpaz Karimova farzandi")],
    )
    assert report.is_valid, report.as_dict()
    with organization_context(tenant.organization.id):
        benefit = Discount.objects.get(child__last_name="Karimov")
    assert benefit.kind == "staff_child"
    assert benefit.reason == "Oshpaz Karimova farzandi"


def test_a_benefit_without_a_reason_says_where_it_came_from(tenant: Any):
    _run(tenant, [_row("Karimov", benefit="kam ta'minlangan")])
    with organization_context(tenant.organization.id):
        benefit = Discount.objects.get(child__last_name="Karimov")
    assert benefit.kind == "low_income"
    assert "import" in benefit.reason.lower()


def test_an_unknown_benefit_word_is_a_row_error(tenant: Any):
    report = _run(tenant, [_row("Karimov", benefit="sariq")], dry_run=True)
    assert [error.field for error in report.errors] == ["benefit"]


# --- Oilalar telefon orqali ---


def test_one_phone_written_two_ways_is_one_family(tenant: Any):
    report = _run(
        tenant,
        [
            _row("Valiyev", "Ali", parent="Valiyev Vali", phone="90 111 11 11"),
            _row(
                "Valiyev", "Soli", born="01.02.2022", parent="Valiyev Vali", phone="+998901111111"
            ),
        ],
    )
    assert report.is_valid, report.as_dict()
    with organization_context(tenant.organization.id):
        assert Guardian.objects.count() == 1
        assert Guardian.objects.get().phone == "+998901111111"


def test_an_unreadable_phone_is_a_row_error(tenant: Any):
    report = _run(tenant, [_row("Valiyev", parent="Vali", phone="12345")], dry_run=True)
    assert [error.field for error in report.errors] == ["guardian_phone"]


def test_siblings_at_different_prices_are_flagged(tenant: Any):
    report = _run(
        tenant,
        [
            _row("Valiyev", "Ali", tariff="Aka-uka", phone="901111111", parent="Vali"),
            _row(
                "Valiyev",
                "Soli",
                born="01.02.2022",
                tariff="Asosiy",
                phone="901111111",
                parent="Vali",
            ),
        ],
        dry_run=True,
    )
    assert report.is_valid
    assert any(warning.field == "family" for warning in report.warnings), report.as_dict()


# --- Dublikatlar: transliteratsiya ---


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Boxodirova", "Bohodirova"),
        ("Bohodirova", "Bahodirova"),
        ("Doniyorov", "Donyorov"),
        ("Oʻrinboyev", "O'rinboyev"),
    ],
)
def test_transliteration_twins_are_caught_inside_the_file(tenant: Any, first: str, second: str):
    report = _run(
        tenant,
        [_row(first, "Malika", group="Quyoshcha"), _row(second, "Malika", group="Kamalak")],
        dry_run=True,
    )
    assert len(report.possible_duplicates) == 1, report.as_dict()


def test_a_twin_of_a_child_already_in_the_system_is_caught(tenant: Any):
    _run(tenant, [_row("Boxodirova", "Malika")])
    report = _run(tenant, [_row("Bahodirova", "Malika", born="15.03.2021")], dry_run=True)
    assert len(report.possible_duplicates) == 1
    assert report.possible_duplicates[0]["matches"][0]["source"] == "system"


def test_different_children_are_not_duplicates(tenant: Any):
    report = _run(tenant, [_row("Valiyev", "Ali"), _row("Karimov", "Ali")], dry_run=True)
    assert report.possible_duplicates == []


def test_possible_duplicates_wait_for_a_decision(tenant: Any):
    rows = [_row("Boxodirova", "Malika"), _row("Bohodirova", "Malika", group="Kamalak")]

    undecided = _run(tenant, rows)
    assert not undecided.is_valid
    with organization_context(tenant.organization.id):
        assert not Child.objects.exists()

    skipped = _run(tenant, rows, decision="skip")
    assert skipped.is_valid and skipped.created == 1
    with organization_context(tenant.organization.id):
        assert Child.objects.count() == 1


def test_keeping_both_is_also_a_decision(tenant: Any):
    rows = [_row("Boxodirova", "Malika"), _row("Bohodirova", "Malika", group="Kamalak")]
    report = _run(tenant, rows, decision="keep")
    assert report.created == 2


def test_the_api_passes_the_decision_through(tenant: Any):
    from django.core.files.uploadedfile import SimpleUploadedFile

    rows = [_row("Boxodirova", "Malika"), _row("Bohodirova", "Malika", group="Kamalak")]
    upload = SimpleUploadedFile(
        "bolalar.xlsx",
        _sheet(rows),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response = tenant.client().post(
        "/api/v1/children/import",
        {"file": upload, "dry_run": "false", "duplicate_decision": "skip"},
        format="multipart",
    )
    assert response.status_code == 200, response.json()
    data = response.json()["data"]
    assert data["created"] == 1
    assert len(data["possible_duplicates"]) == 1
    assert date(2021, 3, 14).isoformat() in str(data["possible_duplicates"])
