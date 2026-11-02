"""
Javobgarlikdagi pul hisob qoldigʻiga TENG (audit, 2026-10-30).

Auditda: Asadbek nomida naqd 343 301 835 + bank 81 521 834 =
424 823 670 koʻrinardi, hisoblarda esa 27.10 holatiga 85 131 002 bor
edi. Sabab — muallifsiz harakatlar filtrdan tushib qolardi: bank
komissiyasi `created_by=None` bilan yoziladi (uni kassir emas, bank
ushlaydi), yaʼni odamga KIRIM yozilib, unga tegishli CHIQIM
yozilmasdi.

Jadval tekshirib boʻladigan boʻlishi kerak: qatorlar yigʻindisi
hisoblar yigʻindisiga teng.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.cash import selectors
from apps.cash import services as cash
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


@pytest.fixture
def desk(tenant_a) -> Any:
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        cash.ensure_branch_accounts(branch=tenant_a.branch)
        till = cash.account_for_method(branch=tenant_a.branch, method="cash")
        cash.record_operation(
            kind="owner_contribution",
            account=till,
            amount=Decimal("10000000"),
            occurred_on=today,
            reason="Ishga tushirish uchun",
            created_by=tenant_a.owner,
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
        # Terminal toʻlovi — komissiyasi MUALLIFSIZ yoziladi.
        finance.record_payment(
            child=child, amount=Decimal("1500000"), method="terminal", received_by=tenant_a.owner
        )
    return tenant_a


def _sum(rows: list[dict[str, Any]], key: str) -> Decimal:
    return sum((Decimal(row[key]) for row in rows), Decimal("0"))


def test_custody_adds_up_to_the_account_balances(desk, tenant_a):
    with organization_context(tenant_a.organization.id):
        rows = selectors.custody(organization_id=tenant_a.organization.id)
        balances = selectors.account_balances(organization_id=tenant_a.organization.id)
    assert _sum(rows, "amount") == _sum(balances, "balance")


def test_the_unassigned_bucket_is_named(desk, tenant_a):
    """Muallifsiz harakat yoʻqolmaydi — u alohida qatorda koʻrinadi."""
    with organization_context(tenant_a.organization.id):
        rows = selectors.custody(organization_id=tenant_a.organization.id)
    unassigned = [row for row in rows if row["user_id"] is None]
    assert unassigned, rows
    assert unassigned[0]["full_name"]


def test_an_earlier_date_sees_less(desk, tenant_a):
    """`as_of` — tanlangan sanadagi holat."""
    with organization_context(tenant_a.organization.id):
        before = selectors.custody(
            organization_id=tenant_a.organization.id,
            as_of=timezone.localdate() - timedelta(days=1),
        )
    assert _sum(before, "amount") == Decimal("0")
