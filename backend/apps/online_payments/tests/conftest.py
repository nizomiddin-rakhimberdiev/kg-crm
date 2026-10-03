"""Shared fixtures: a kindergarten with an open invoice and provider keys."""

from __future__ import annotations

import base64
import uuid
from datetime import date
from decimal import Decimal

import pytest

from apps.core.tenancy import organization_context

PAYME_KEY = "payme-secret-key-123"
CLICK_KEY = "click-secret-key-456"


def make_invoice(tenant, amount: str = "1500000"):
    from apps.children.models import Child
    from apps.finance.models import TariffPlan
    from apps.finance.services import issue_invoice

    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name=f"T-{uuid.uuid4().hex[:8]}",
            amount=Decimal(amount),
        )
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2022, 1, 1),
            gender="male",
            tariff=tariff,
            enrolled_on=date(2026, 8, 1),
        )
        return issue_invoice(child=child, period_year=2026, period_month=9)


def connect(tenant, provider: str):
    from apps.online_payments.services import save_credential

    with organization_context(tenant.organization.id):
        return save_credential(
            organization=tenant.organization,
            provider=provider,
            merchant_id="m-1",
            service_id="777" if provider == "click" else "",
            secret=PAYME_KEY if provider == "payme" else CLICK_KEY,
        )


def payme_auth(key: str = PAYME_KEY) -> str:
    return "Basic " + base64.b64encode(f"Paycom:{key}".encode()).decode()


@pytest.fixture
def invoice(tenant_a):
    return make_invoice(tenant_a)


@pytest.fixture
def payme(tenant_a):
    return connect(tenant_a, "payme")


@pytest.fixture
def click(tenant_a):
    return connect(tenant_a, "click")
