"""
Topshiriqdagi pul ikkinchi marta ishlatilmaydi (audit 2026-11-12, A5).

Topshirish yaratilganda kassirning qo'lidagi pul tekshiriladi, lekin
TASDIQLASH paytida emas. Orada kassir o'sha naqddan chiqim qilsa yoki
to'lov storno qilinsa, qabul qiluvchi qo'lida yo'q pulni "oldim"
derdi va javobgarlik jadvali haqiqiy kassadan katta bo'lib qolardi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.cash import services as cash
from apps.cash.models import CashAccount, CashHandover, MovementDirection, MovementSource
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Payment

pytestmark = pytest.mark.django_db


def _user(tenant: Any, role: str, email: str) -> tuple[User, APIClient]:
    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=email,
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=email.split("@")[0].title(),
            organization=tenant.organization,
            role=tenant.role(role),
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return user, client


def _pay(tenant: Any, received_by: Any) -> Payment:
    with organization_context(tenant.organization.id):
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )
        return finance.record_payment(
            child=child, amount=Decimal("500000"), method="cash", received_by=received_by
        )


def _till(tenant: Any) -> CashAccount:
    with organization_context(tenant.organization.id):
        return cash.account_for_method(branch=tenant.branch, method="cash")


def _hand(tenant: Any, cashier: User, director: User) -> CashHandover:
    with organization_context(tenant.organization.id):
        return cash.hand_over(
            from_user=cashier, to_user=director, amount=Decimal("500000"), branch=tenant.branch
        )


def test_confirming_checks_the_money_is_still_in_hand(tenant_a: Any):
    cashier, _ = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, _ = _user(tenant_a, "director", "direktor@alfa.uz")
    _pay(tenant_a, cashier)
    handover = _hand(tenant_a, cashier, director)

    # Orada kassir o'sha naqddan 300 000 sarfladi.
    with organization_context(tenant_a.organization.id):
        cash.post_movement(
            account=_till(tenant_a),
            direction=MovementDirection.OUT,
            amount=Decimal("300000"),
            source_type=MovementSource.MANUAL,
            source_id=None,
            description="Bozorlik",
            created_by=cashier,
        )
        with pytest.raises(BusinessRuleViolation, match="qoʻlida"):
            cash.confirm_handover(handover=handover, user=director)
        handover.refresh_from_db()
    assert handover.status == "pending"


def test_a_cash_payment_waiting_in_a_handover_is_not_reversed(tenant_a: Any):
    cashier, _ = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, _ = _user(tenant_a, "director", "direktor@alfa.uz")
    payment = _pay(tenant_a, cashier)
    handover = _hand(tenant_a, cashier, director)

    with organization_context(tenant_a.organization.id):
        with pytest.raises(BusinessRuleViolation, match="topshiriq"):
            finance.reverse_payment(
                payment=payment, reason="Xato kiritilgan", created_by=tenant_a.owner
            )

        # Qabul qiluvchi rad etdi — pul yana kassirda, storno mumkin.
        cash.reject_handover(handover=handover, user=director, reason="Sanoqda kam chiqdi")
        finance.reverse_payment(
            payment=payment, reason="Xato kiritilgan", created_by=tenant_a.owner
        )
        payment.refresh_from_db()
    assert payment.is_reversed


def test_the_custody_table_shows_what_is_promised_away(tenant_a: Any):
    """Jadvalda "qo'lda" bilan "topshirishga va'da qilingan" alohida ko'rinadi."""
    cashier, _ = _user(tenant_a, "cashier", "kassir@alfa.uz")
    director, director_client = _user(tenant_a, "director", "direktor@alfa.uz")
    _pay(tenant_a, cashier)
    _hand(tenant_a, cashier, director)

    rows = director_client.get("/api/v1/cash-accounts/custody").json()["data"]
    row = next(r for r in rows if r["user_id"] == str(cashier.id))
    assert Decimal(row["cash"]) == Decimal("500000")
    assert Decimal(row["pending_out"]) == Decimal("500000")
    assert Decimal(row["available"]) == Decimal("0")
