"""
Qidiruv: ism, shartnoma raqami yoki ID (mijoz soʻrovi, 2026-10-28).

Mijoz "asosiyda ham, bolalarda ham, toʻlovlar va qarzdorliklarda ham"
dedi, va buning sababi amaliy: kassir qoʻlida qogʻoz shartnoma turadi,
ekranda esa faqat ism boʻyicha qidirish bor edi — bir xil familiyali
uchta bola orasidan toʻgʻrisini topish uchun har birini ochib koʻrish
kerak boʻlardi.

Qidiruv BIR XIL ishlashi kerak: uch ekran uchta boshqa javob bersa,
xodim qaysi biriga ishonishni bilmaydi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


@pytest.fixture
def children(tenant_a) -> list[Child]:
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        rows = []
        for index, (last, first, contract) in enumerate(
            [
                ("Safarova", "Aziza", "SH-2026-0041"),
                ("Safarov", "Doston", "SH-2026-0042"),
                ("Qodirova", "Malika", "SH-2026-0100"),
            ]
        ):
            rows.append(
                Child.objects.create(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    first_name=first,
                    last_name=last,
                    date_of_birth=date(2021, 3, 1 + index),
                    gender="female" if index != 1 else "male",
                    tariff=tariff,
                    contract_number=contract,
                    enrolled_on=timezone.localdate().replace(day=1),
                )
            )
        return rows


def test_children_are_found_by_contract_number(tenant_a, children):
    response = tenant_a.client().get(reverse("v1:child-list"), {"q": "SH-2026-0042"})
    assert response.status_code == 200
    names = [row["full_name"] for row in response.json()["data"]]
    assert names == ["Safarov Doston"]


def test_children_are_found_by_id(tenant_a, children):
    target = children[2]
    response = tenant_a.client().get(reverse("v1:child-list"), {"q": str(target.id)})
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["data"]] == [str(target.id)]


def test_the_name_search_still_works(tenant_a, children):
    response = tenant_a.client().get(reverse("v1:child-list"), {"q": "safarov"})
    assert {row["full_name"] for row in response.json()["data"]} == {
        "Safarova Aziza",
        "Safarov Doston",
    }


def test_the_payment_board_finds_a_contract_number(tenant_a, children):
    today = timezone.localdate()
    response = tenant_a.client().get(
        reverse("v1:payment-board"),
        {"period_year": today.year, "period_month": today.month, "search": "SH-2026-0100"},
    )
    assert response.status_code == 200, response.data
    assert [row["child_name"] for row in response.json()["data"]] == ["Qodirova Malika"]


def test_debtors_are_found_by_contract_number(tenant_a, children):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        for child in children[:2]:
            finance.issue_invoice(
                child=child,
                period_year=today.year,
                period_month=today.month,
                issued_date=today,
                due_date=today,
            )

    response = tenant_a.client().get(reverse("v1:debtor-list"), {"q": "SH-2026-0042"})
    assert response.status_code == 200, response.data
    rows = response.json()["data"]["results"]
    assert [row["child"]["full_name"] for row in rows] == ["Safarov Doston"]
