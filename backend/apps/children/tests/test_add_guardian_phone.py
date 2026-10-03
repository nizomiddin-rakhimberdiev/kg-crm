"""
Bola kartasidan vasiy qo'shish ham telefonni tekshiradi (Q7).

Yakuniy qabul ssenariysi (brief §6, 1-qadam) shuni topdi: alohida
`/guardians` endpointi `PhoneField` dan o'tardi, bola kartasidagi
`POST /children/{id}/guardians` esa xom satrni yozib qo'yardi —
"12345" qabul qilinar, "+998 90 123 45 67" esa normalizatsiyasiz
saqlanardi (ya'ni xuddi shu ota-ona telefoni bo'yicha topilmay,
ikkinchi vasiy yaratilardi).
"""

from __future__ import annotations

from datetime import date

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.fixture
def child(tenant_a) -> Child:
    with organization_context(tenant_a.organization.id):
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2022, 1, 1),
            gender="male",
        )


def _add(tenant, child, phone: str):
    return tenant.client().post(
        f"/api/v1/children/{child.id}/guardians",
        {"first_name": "Nodira", "last_name": "Valiyeva", "phone": phone, "relation": "mother"},
        format="json",
    )


def test_a_broken_phone_is_refused(tenant_a, child):
    response = _add(tenant_a, child, "12345")
    assert response.status_code == 400
    assert "phone" in response.json()["error"]["details"]


def test_a_valid_phone_is_stored_normalised(tenant_a, child):
    response = _add(tenant_a, child, "+998 90 123 45 67")
    assert response.status_code == 201
    assert response.json()["data"]["guardian"]["phone"] == "+998901234567"


def test_the_same_parent_typed_differently_is_one_guardian(tenant_a, child):
    from apps.children.models import Guardian

    _add(tenant_a, child, "+998 90 123 45 67")
    _add(tenant_a, child, "90 123 45 67")
    with organization_context(tenant_a.organization.id):
        assert Guardian.objects.count() == 1
