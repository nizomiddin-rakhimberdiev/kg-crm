"""
To'lov qabul qilish ekrani (docs/04 §9.7).

Bu ekran ilgari hisob-fakturalar ro'yxatiga tayanardi va ikki sababdan
noto'g'ri ishlardi:

1. Hisob-faktura chiqarilmagan bola UMUMAN ko'rinmasdi — ya'ni undan
   pul qabul qilib bo'lmasdi.
2. Ro'yxat `page_size` siz so'ralar va sahifalash tugmasi yo'q edi:
   serverdan 25 qator kelardi, 41 bolali bog'chada 16 bola ekranga
   chiqmasdi. Yuqoridagi "jami" ham shuning uchun kam ko'rsatardi.

Birinchi ikkita test aynan shu ikki holatni qotirib qo'yadi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import selectors, services
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _tariff(tenant: Any, amount: str = "1500000") -> TariffPlan:
    return TariffPlan.objects.create(
        organization=tenant.organization,
        branch=tenant.branch,
        name="Toʻliq kun",
        amount=Decimal(amount),
    )


def _child(tenant: Any, first: str, last: str = "Karimov", tariff: Any = None) -> Child:
    return Child.objects.create(
        organization=tenant.organization,
        branch=tenant.branch,
        first_name=first,
        last_name=last,
        date_of_birth=date(2021, 3, 14),
        gender="male",
        tariff=tariff,
    )


def _board(tenant: Any, **kwargs: Any) -> list[dict[str, Any]]:
    queryset = selectors.month_board_queryset(
        organization_id=tenant.organization.id, period_year=2026, period_month=9, **kwargs
    )
    return [selectors.board_row(child) for child in queryset]


def test_a_child_without_an_invoice_is_still_on_the_board(tenant_a: Any):
    """
    Eng muhimi: fakturasiz bola ham ko'rinadi.

    Aks holda undan pul qabul qilishning yo'li yo'q edi — kassir uni
    ekranda topa olmasdi.
    """
    with organization_context(tenant_a.organization.id):
        _child(tenant_a, "Javohir")
        rows = _board(tenant_a)

    assert [row["child_name"] for row in rows] == ["Karimov Javohir"]
    assert rows[0]["state"] == "no_invoice"
    assert rows[0]["charged"] == "0.00"
    assert rows[0]["invoice_id"] is None


def test_every_child_is_reachable_regardless_of_how_many_there_are(tenant_a: Any):
    """
    Sahifalash serverda, va u bolalar ro'yxatiga qo'llanadi.

    Ilgari ekran 25 qator bilan cheklanardi va qolganlariga yo'l yo'q
    edi; bu test o'sha chegara qaytib kelmasligini tekshiradi.
    """
    with organization_context(tenant_a.organization.id):
        tariff = _tariff(tenant_a)
        for index in range(30):
            _child(tenant_a, f"Bola{index:02d}", last=f"Familiya{index:02d}", tariff=tariff)
        rows = _board(tenant_a)

    assert len(rows) == 30


def test_the_board_shows_what_is_still_owed_this_month(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        tariff = _tariff(tenant_a, "1500000")
        child = _child(tenant_a, "Javohir", tariff=tariff)
        invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
        services.record_payment_batch(
            child=child,
            invoice=invoice,
            lines=[{"method": "cash", "amount": Decimal("1400000")}],
        )
        rows = _board(tenant_a)

    assert rows[0]["charged"] == "1500000.00"
    assert rows[0]["paid"] == "1400000.00"
    assert rows[0]["outstanding"] == "100000.00"
    assert rows[0]["state"] == "partial"


def test_an_advance_shows_as_a_negative_balance(tenant_a: Any):
    """Kassir avansni toʻlov qabul qilishdan OLDIN koʻrishi kerak."""
    with organization_context(tenant_a.organization.id):
        child = _child(tenant_a, "Javohir")
        services.record_payment(child=child, amount=Decimal("500000"), method="cash")
        rows = _board(tenant_a)

    assert rows[0]["balance"] == "-500000.00"


def test_search_finds_a_child_by_name(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        _child(tenant_a, "Javohir", last="Karimov")
        _child(tenant_a, "Zarina", last="Abdullayeva")

        assert [r["child_name"] for r in _board(tenant_a, search="javo")] == ["Karimov Javohir"]
        assert [r["child_name"] for r in _board(tenant_a, search="abdulla")] == [
            "Abdullayeva Zarina"
        ]


def test_status_filters_split_the_board(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        tariff = _tariff(tenant_a, "1000000")
        paid_child = _child(tenant_a, "Toliq", last="Aaa", tariff=tariff)
        debtor = _child(tenant_a, "Qarzdor", last="Bbb", tariff=tariff)
        _child(tenant_a, "Fakturasiz", last="Ccc")

        invoice = services.issue_invoice(child=paid_child, period_year=2026, period_month=9)
        services.record_payment(
            child=paid_child, invoice=invoice, amount=Decimal("1000000"), method="cash"
        )
        services.issue_invoice(child=debtor, period_year=2026, period_month=9)

        assert [r["child_name"] for r in _board(tenant_a, status="paid")] == ["Aaa Toliq"]
        assert [r["child_name"] for r in _board(tenant_a, status="debtor")] == ["Bbb Qarzdor"]
        assert [r["child_name"] for r in _board(tenant_a, status="no_invoice")] == [
            "Ccc Fakturasiz"
        ]


def test_the_summary_counts_every_child_not_just_one_page(tenant_a: Any):
    """
    Yuqoridagi "jami" SAHIFADAN qat'i nazar to'g'ri bo'lishi kerak.

    Ilgari u yuklangan 25 qatordan hisoblanardi va bog'chaning oylik
    tushumini kam ko'rsatardi.
    """
    with organization_context(tenant_a.organization.id):
        tariff = _tariff(tenant_a, "1000000")
        for index in range(30):
            child = _child(tenant_a, f"Bola{index:02d}", last=f"F{index:02d}", tariff=tariff)
            services.issue_invoice(child=child, period_year=2026, period_month=9)

        summary = selectors.month_board_summary(
            organization_id=tenant_a.organization.id, period_year=2026, period_month=9
        )

    assert summary["children"] == 30
    assert summary["with_invoice"] == 30
    assert summary["charged"] == "30000000.00"
    assert summary["debtors"] == 30


def test_the_summary_reports_children_without_an_invoice(tenant_a: Any):
    """Tarifsiz bola jimgina yoʻqolib qolmasin — ular sanаb turiladi."""
    with organization_context(tenant_a.organization.id):
        tariff = _tariff(tenant_a)
        with_tariff = _child(tenant_a, "Bor", last="Aaa", tariff=tariff)
        _child(tenant_a, "Yoq", last="Bbb")
        services.issue_invoice(child=with_tariff, period_year=2026, period_month=9)

        summary = selectors.month_board_summary(
            organization_id=tenant_a.organization.id, period_year=2026, period_month=9
        )

    assert summary["children"] == 2
    assert summary["without_invoice"] == 1


def test_a_cancelled_invoice_leaves_the_child_without_one(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        tariff = _tariff(tenant_a)
        child = _child(tenant_a, "Javohir", tariff=tariff)
        invoice = services.issue_invoice(child=child, period_year=2026, period_month=9)
        services.cancel_invoice(invoice=invoice, reason="Xato chiqarilgan")
        rows = _board(tenant_a)

    assert rows[0]["state"] == "no_invoice"


@pytest.mark.tenancy
def test_the_board_never_shows_another_organization(tenant_a: Any, tenant_b: Any):
    with organization_context(tenant_b.organization.id):
        _child(tenant_b, "Begona", last="Bola")
    with organization_context(tenant_a.organization.id):
        _child(tenant_a, "Oz", last="Bolasi")
        rows = _board(tenant_a)

    assert [row["child_name"] for row in rows] == ["Bolasi Oz"]
