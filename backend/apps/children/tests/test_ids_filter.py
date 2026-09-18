"""
`GET /children?ids=a,b,c` — yorliqlarni id bo'yicha bitta so'rovda olish
(docs/07 §6: "Nega?" paneli nomlarni snapshot'dan emas, jonli oladi).
"""

from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse

from apps.children.models import Child
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


def _child(tenant, name: str, is_active: bool = True) -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Test",
            date_of_birth=date(2021, 1, 1),
            gender="male",
            is_active=is_active,
        )


def _ids(response) -> set[str]:
    return {row["id"] for row in response.json()["data"]}


class TestIdsFilter:
    def test_returns_only_requested_including_inactive(self, tenant_a):
        a = _child(tenant_a, "A")
        b = _child(tenant_a, "B", is_active=False)
        _child(tenant_a, "C")
        response = tenant_a.client().get(reverse("v1:child-list"), {"ids": f"{a.id},{b.id}"})
        assert response.status_code == 200
        assert _ids(response) == {str(a.id), str(b.id)}

    @pytest.mark.tenancy
    def test_other_tenant_ids_are_simply_absent(self, tenant_a, tenant_b):
        mine = _child(tenant_a, "Meniki")
        theirs = _child(tenant_b, "Begona")
        response = tenant_a.client().get(
            reverse("v1:child-list"), {"ids": f"{mine.id},{theirs.id}"}
        )
        assert _ids(response) == {str(mine.id)}

    def test_garbage_ids_do_not_crash(self, tenant_a):
        a = _child(tenant_a, "A")
        response = tenant_a.client().get(reverse("v1:child-list"), {"ids": f"not-a-uuid,,{a.id}"})
        assert response.status_code == 200
        assert _ids(response) == {str(a.id)}

    def test_empty_ids_means_no_filter(self, tenant_a):
        _child(tenant_a, "A")
        _child(tenant_a, "B")
        response = tenant_a.client().get(reverse("v1:child-list"), {"ids": ""})
        assert len(_ids(response)) == 2
