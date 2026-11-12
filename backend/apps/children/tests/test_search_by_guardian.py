"""
Bolani vasiysi orqali topish (audit 2026-11-12, D1).

Ota-ona qo'ng'iroq qiladi: "Men Kamola Valiyeva, 90 123 45 67". Kassir
ekranida esa faqat bolaning ismi va shartnoma raqami bo'yicha qidiruv
bor edi.
"""

from __future__ import annotations

from datetime import date

import pytest

from apps.children.models import Child, ChildGuardian, Guardian
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def child(tenant_a) -> Child:
    with organization_context(tenant_a.organization.id):
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Doston",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 1),
            gender="male",
        )
        Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Malika",
            last_name="Qodirova",
            date_of_birth=date(2021, 3, 2),
            gender="female",
        )
        guardian = Guardian.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Kamola",
            last_name="Toshmatova",
            phone="+998901234567",
        )
        ChildGuardian.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            child=child,
            guardian=guardian,
            relation="mother",
            is_primary=True,
        )
        return child


@pytest.mark.parametrize("term", ["Toshmatova", "kamola", "90 123 45 67", "1234567"])
def test_a_child_is_found_by_their_guardian(tenant_a, child, term):
    rows = tenant_a.client().get("/api/v1/children", {"q": term}).json()["data"]
    assert [row["id"] for row in rows] == [str(child.id)]
