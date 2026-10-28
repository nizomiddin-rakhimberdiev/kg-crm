"""
Jurnal hammaga ochiq, amal esa egasiga (mijoz soʻrovi, 2026-10-28).

Mijoz: "Hamma toʻlovlar hammaga koʻrinishi kerak, kim qachon qancha
toʻlov qabul qilib olgani, hamma rolda". Bu ADR-30 ning bir qismini
almashtiradi — oʻsha qoida bir hafta amalda ishlatilgandan keyin
bogʻchaning oʻzi fikrini oʻzgartirdi: smena almashganda "kecha kim
qancha oldi?" degan savol har kuni beriladi, va u har safar egadan
oʻtishi kerak edi.

Ochilgani — KOʻRISH. Boshqa kassirning pulini qaytarish hamon oʻsha
odamning ishi: begona qoʻl tekkan toʻlov keyin hech kimnikiga
oʻxshamaydi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import Role, User
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _client(tenant: Any, user: User) -> APIClient:
    with organization_context(tenant.organization.id):
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _child(tenant_a: Any) -> Child:
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Aziza",
            last_name="Safarova",
            date_of_birth=date(2021, 5, 4),
            gender="female",
            tariff=tariff,
        )


@pytest.fixture
def cashier(tenant_a) -> User:
    """Toʻlov qabul qila oladigan, cheklangan rol."""
    with organization_context(tenant_a.organization.id):
        role = Role.objects.get(organization=tenant_a.organization, code="cashier")
        role.payments_own_only = True
        role.save(update_fields=["payments_own_only"])
        return User.objects.create_user(
            email="kassir@bogcha.uz",
            password="Kassir2026!",
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            role=role,
            full_name="Kassirova Laziza",
        )


def test_a_cashier_sees_a_payment_someone_else_took(tenant_a, cashier):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )

    response = _client(tenant_a, cashier).get(reverse("v1:payment-list"))
    assert response.status_code == 200, response.data
    rows = response.json()["data"]
    assert len(rows) == 1
    assert rows[0]["received_by_name"]


def test_a_cashier_cannot_reverse_someone_elses_payment(tenant_a, cashier):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )

    response = _client(tenant_a, cashier).post(
        reverse("v1:payment-reverse", args=[payment.id]),
        {"reason": "Xato"},
        format="json",
    )
    assert response.status_code == 403


def test_a_cashier_can_reverse_their_own_payment(tenant_a, cashier):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=cashier
        )

    response = _client(tenant_a, cashier).post(
        reverse("v1:payment-reverse", args=[payment.id]),
        {"reason": "Xato summa"},
        format="json",
    )
    assert response.status_code == 200, response.data


def test_another_tenant_still_sees_nothing(tenant_a, tenant_b, cashier):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        payment = finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=tenant_a.owner
        )

    response = tenant_b.client().get(reverse("v1:payment-detail", args=[payment.id]))
    assert response.status_code == 404
