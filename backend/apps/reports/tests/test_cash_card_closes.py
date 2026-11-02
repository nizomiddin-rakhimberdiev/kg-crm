"""
Boshqaruv panelidagi kassa kartasi tenglamasi YOPILADI (audit, 2026-10-30).

Auditda kartada shunday turardi:

    666 107 120 − 104 520 752 − 309 240 166 = 252 346 202

qoldiq esa 84 971 202 edi. Farq 167 375 000 — egasi olgan
263 000 000 va qoʻshgan 95 625 000: ikkala qator ham kartada yoʻq
edi. Raqamlar notoʻgʻri emas, kartaning oʻzi toʻliq emas edi, va
shuning uchun uni tekshirib boʻlmasdi.

Endi karta har bir harakatni manbasi boʻyicha sanaydi. "Boshqa" —
qoldiq emas, oʻz yigʻindisi: oʻtkazma, boshlangʻich qoldiq, sanoq
farqi va qolgan operatsiyalar.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash import services as cash
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan
from apps.reports import selectors

pytestmark = pytest.mark.django_db


def _money(value: Any) -> Decimal:
    return Decimal(str(value))


@pytest.fixture
def busy_month(tenant_a) -> Any:
    """Bir oyning har xil pul harakatlari — hammasi birga."""
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        cash.ensure_branch_accounts(branch=tenant_a.branch)
        till = cash.account_for_method(branch=tenant_a.branch, method="cash")

        cash.record_operation(
            kind="owner_contribution",
            account=till,
            amount=Decimal("20000000"),
            occurred_on=today,
            reason="Ishga tushirish uchun",
        )
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Aziza",
            last_name="Safarova",
            date_of_birth=date(2021, 5, 4),
            gender="female",
            tariff=tariff,
            enrolled_on=today.replace(day=1),
        )
        finance.record_payment(
            child=child, amount=Decimal("1500000"), method="cash", received_by=tenant_a.owner
        )
        cash.record_operation(
            kind="owner_draw",
            account=till,
            amount=Decimal("3000000"),
            occurred_on=today,
            reason="Egasiga",
            subtype="draw",
        )
        cash.adjust_balance(
            account=till,
            amount=Decimal("500000"),
            reason="Seyfdagi pul kiritildi",
        )
    return tenant_a


def test_the_card_equation_closes(busy_month, tenant_a):
    with organization_context(tenant_a.organization.id):
        card = selectors.cash_position(organization_id=tenant_a.organization.id)

    left = (
        _money(card["income"])
        - _money(card["expenses"])
        - _money(card["payroll"])
        - _money(card["owner_draws"])
        + _money(card["owner_contributions"])
        + _money(card["other"])
    )
    assert left == _money(card["balance"])


def test_the_card_names_the_owner_lines(busy_month, tenant_a):
    with organization_context(tenant_a.organization.id):
        card = selectors.cash_position(organization_id=tenant_a.organization.id)
    assert _money(card["owner_draws"]) == Decimal("3000000.00")
    assert _money(card["owner_contributions"]) == Decimal("20000000.00")


def test_money_in_transit_is_its_own_line(busy_month, tenant_a):
    with organization_context(tenant_a.organization.id):
        card = selectors.cash_position(organization_id=tenant_a.organization.id)
    assert "in_transit" in card
