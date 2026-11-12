"""
Chiqim tahririning ikki chegarasi (audit 2026-11-12, A3).

* Summa, sana yoki qop o'zgarsa pul qayta yoziladi — buning sababi
  yo'q edi, va jurnalda "chiqim tahrirlandi" degan qator nima uchun
  ekanini aytmasdi.
* To'lov komissiyasi (avtomatik chiqim) qo'lda tahrirlanardi: to'lov
  bir summa desa, komissiya boshqa summani aytardi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.expenses.models import Expense, ExpenseCategory
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _expense_id(tenant_a: Any) -> str:
    tenant_a.fund("1000000", kind="cash")
    with organization_context(tenant_a.organization.id):
        category = ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Bozorlik"
        )
    response = tenant_a.client().post(
        reverse("v1:expense-list"),
        {
            "category_id": str(category.id),
            "expense_date": "2026-10-14",
            "amount": "50000",
            "description": "Non",
            "cash_account_id": str(_cash_id(tenant_a)),
        },
        format="json",
    )
    assert response.status_code == 201, response.json()
    return str(response.json()["data"]["id"])


def _cash_id(tenant_a: Any) -> Any:
    from apps.cash.models import CashAccount

    with organization_context(tenant_a.organization.id):
        return CashAccount.objects.get(branch=tenant_a.branch, kind="cash", is_active=True).id


def test_changing_the_amount_needs_a_reason(tenant_a):
    expense_id = _expense_id(tenant_a)
    url = reverse("v1:expense-detail", args=[expense_id])

    refused = tenant_a.client().patch(url, {"amount": "60000"}, format="json")
    assert refused.status_code == 422, refused.json()

    done = tenant_a.client().patch(
        url, {"amount": "60000", "reason": "Chekda 60 ming ekan"}, format="json"
    )
    assert done.status_code == 200, done.json()
    with organization_context(tenant_a.organization.id):
        log = AuditLog.objects.filter(entity_type="expense", action="update").latest("created_at")
    assert log.changes["reason"] == "Chekda 60 ming ekan"
    assert log.changes["before"]["amount"] == "50000.00"
    assert log.changes["after"]["amount"] == "60000.00"


def test_a_description_change_needs_no_reason(tenant_a):
    expense_id = _expense_id(tenant_a)
    response = tenant_a.client().patch(
        reverse("v1:expense-detail", args=[expense_id]),
        {"description": "Non va sut"},
        format="json",
    )
    assert response.status_code == 200, response.json()


def test_a_payment_commission_cannot_be_edited(tenant_a):
    with organization_context(tenant_a.organization.id):
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
        )
        payment = finance.record_payment(
            child=child, amount=Decimal("1500000"), method="terminal", received_by=tenant_a.owner
        )
        commission = Expense.objects.get(payment=payment)

    response = tenant_a.client().patch(
        reverse("v1:expense-detail", args=[commission.id]),
        {"description": "boshqa", "reason": "Qoʻlda tuzatish"},
        format="json",
    )
    assert response.status_code == 422, response.json()
    with organization_context(tenant_a.organization.id):
        commission.refresh_from_db()
    assert commission.amount == Decimal("3000.00")
