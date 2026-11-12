"""
Tarif va imtiyoz — o'z modullari (audit 2026-11-12, C1).

Ikkalasi `payments` modulida edi, ya'ni to'lov qabul qiladigan kassir
yangi tarif ham, 100 % imtiyoz ham yarata olardi — bolaning oylik
to'lovini o'zi nolga tushirardi. Fakturani bekor qilish esa oddiy
`update` edi. Endi `tariffs` va `discounts` alohida, kassirda faqat
o'qish; faktura bekor qilish — `payments.approve`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.apps import apps as global_apps
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import Permission, Role, RolePermission, User
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _as(tenant: Any, role: str) -> APIClient:
    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=f"{role}@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=role,
            organization=tenant.organization,
            role=tenant.role(role),
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _child(tenant: Any) -> Child:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Aziza",
            last_name="Safarova",
            date_of_birth=date(2021, 5, 4),
            gender="female",
            tariff=tariff,
            enrolled_on=date(2026, 1, 10),
        )


def test_a_cashier_reads_tariffs_but_does_not_create_them(tenant_a):
    cashier = _as(tenant_a, "cashier")
    assert cashier.get("/api/v1/tariffs").status_code == 200
    created = cashier.post("/api/v1/tariffs", {"name": "Bepul", "amount": "0"}, format="json")
    assert created.status_code == 403, created.json()


def test_a_cashier_does_not_grant_discounts(tenant_a):
    child = _child(tenant_a)
    cashier = _as(tenant_a, "cashier")
    assert cashier.get("/api/v1/discounts").status_code == 200
    created = cashier.post(
        "/api/v1/discounts",
        {
            "child_id": str(child.id),
            "kind": "custom",
            "discount_type": "percent",
            "value": "100",
            "reason": "Tanish",
            "valid_from": "2026-11-01",
        },
        format="json",
    )
    assert created.status_code == 403, created.json()


def test_a_director_still_manages_both(tenant_a):
    director = _as(tenant_a, "director")
    created = director.post(
        "/api/v1/tariffs", {"name": "Yarim kun", "amount": "900000"}, format="json"
    )
    assert created.status_code == 201, created.json()


def test_a_cashier_does_not_cancel_an_invoice(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        invoice = finance.issue_invoice(child=child, period_year=2026, period_month=10)
    cashier = _as(tenant_a, "cashier")
    response = cashier.post(
        f"/api/v1/invoices/{invoice.id}/cancel", {"reason": "Xato yozilgan"}, format="json"
    )
    assert response.status_code == 403, response.json()


def test_existing_roles_keep_working_after_the_split(tenant_a):
    """Migratsiya: egasi va direktor to'liq, qolgan to'lov rollari o'qiydi."""
    import importlib

    migration = importlib.import_module(
        "apps.accounts.migrations.0011_tariffs_and_discounts_modules"
    )
    with organization_context(tenant_a.organization.id):
        RolePermission.objects.filter(permission__module__in=("tariffs", "discounts")).delete()
        migration.grant(global_apps, tenant_a.organization.id)

        def codes(role_code: str) -> set[str]:
            role = Role.objects.get(code=role_code)
            return set(
                Permission.objects.filter(
                    role_permissions__role=role, module__in=("tariffs", "discounts")
                ).values_list("code", flat=True)
            )

        assert "tariffs.create" in codes("org_owner")
        assert "discounts.create" in codes("director")
        assert codes("cashier") == {"tariffs.read", "discounts.read"}
        assert codes("attendance_manager") == set()
