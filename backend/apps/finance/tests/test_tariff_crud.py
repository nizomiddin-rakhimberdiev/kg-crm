"""
Tariflar: yaratish, tahrirlash, oʻchirish (mijoz soʻrovi, 2026-10-14).

Mijoz: *"yaratilgan tariflar delete ni bosganda oʻchmayapdi, edit qilish
imkoniyati ham boʻlishi kerak"*. Oʻchirish aslida ishlardi — tarif
`is_active=False` boʻlardi — lekin roʻyxat oʻchirilganlarini ham
qaytarardi va karta ekranda joyida qolardi.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

URL = "/api/v1/tariffs"


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.json()["data"]
    return data["results"] if isinstance(data, dict) else data


def _create(client: Any, tenant: Any, name: str = "V.I.P", amount: str = "3050000") -> str:
    response = client.post(
        URL, {"name": name, "amount": amount, "branch_id": str(tenant.branch.id)}, format="json"
    )
    assert response.status_code == 201, response.json()
    return str(response.json()["data"]["id"])


def test_a_deleted_tariff_leaves_the_list(tenant_a: Any):
    client = tenant_a.client()
    tariff_id = _create(client, tenant_a)

    assert client.delete(f"{URL}/{tariff_id}").status_code == 204

    assert tariff_id not in [row["id"] for row in _rows(client.get(URL))]
    assert client.get(f"{URL}/{tariff_id}").status_code == 404


def test_the_same_name_can_be_used_again_after_delete(tenant_a: Any):
    client = tenant_a.client()
    client.delete(f"{URL}/{_create(client, tenant_a)}")
    _create(client, tenant_a)


def test_a_tariff_can_be_renamed_and_repriced(tenant_a: Any):
    client = tenant_a.client()
    tariff_id = _create(client, tenant_a)

    response = client.patch(
        f"{URL}/{tariff_id}", {"name": "VIP", "amount": "3200000"}, format="json"
    )

    assert response.status_code == 200, response.json()
    row = next(r for r in _rows(client.get(URL)) if r["id"] == tariff_id)
    assert (row["name"], row["amount"]) == ("VIP", "3200000.00")


def test_a_tariff_with_children_is_not_deleted(tenant_a: Any):
    client = tenant_a.client()
    tariff_id = _create(client, tenant_a)
    with organization_context(tenant_a.organization.id):
        Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            tariff_id=tariff_id,
        )

    response = client.delete(f"{URL}/{tariff_id}")

    assert response.status_code == 422
    assert tariff_id in [row["id"] for row in _rows(client.get(URL))]


@pytest.mark.tenancy
def test_another_tenants_tariff_is_404(tenant_a: Any, tenant_b: Any):
    tariff_id = _create(tenant_a.client(), tenant_a)
    stranger = tenant_b.client()
    assert stranger.patch(f"{URL}/{tariff_id}", {"name": "x"}, format="json").status_code == 404
    assert stranger.delete(f"{URL}/{tariff_id}").status_code == 404
