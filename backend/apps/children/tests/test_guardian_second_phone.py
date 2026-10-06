"""
Vasiyning ikkinchi telefoni va uni tahrirlash (PLAN 7.4).

Oilada ko'pincha ikkita raqam bo'ladi. Ikkinchisi faqat kartada turgani
yetmaydi: ota-ona botga o'sha raqamdan yozsa ham ulana olishi kerak,
aks holda maydon bor-u, foydasi yo'q (ADR-27).
"""

from __future__ import annotations

from datetime import date

import pytest

from apps.children.models import Guardian
from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

URL = "/api/v1/guardians"


def _create(client, **extra):
    return client.post(
        URL,
        {"first_name": "Nodira", "last_name": "Karimova", "phone": "+998901112233", **extra},
        format="json",
    )


class TestSecondPhone:
    def test_it_is_optional(self, tenant_a):
        response = _create(tenant_a.client())
        assert response.status_code == 201, response.json()
        assert response.json()["data"]["phone_alt"] == ""

    def test_it_is_saved_and_normalised(self, tenant_a):
        body = _create(tenant_a.client(), phone_alt="90 555 44 33").json()["data"]
        assert body["phone_alt"] == "+998905554433"

    def test_the_same_number_twice_is_refused(self, tenant_a):
        response = _create(tenant_a.client(), phone_alt="+998901112233")
        assert response.status_code == 400
        assert "phone_alt" in response.json()["error"]["details"]

    def test_a_broken_second_number_is_refused(self, tenant_a):
        assert _create(tenant_a.client(), phone_alt="12345").status_code == 400


class TestEditing:
    def test_the_name_and_phone_can_be_changed(self, tenant_a):
        client = tenant_a.client()
        guardian_id = _create(client).json()["data"]["id"]
        response = client.patch(
            f"{URL}/{guardian_id}",
            {"last_name": "Valiyeva", "phone": "+998933334455", "phone_alt": "+998901112233"},
            format="json",
        )
        assert response.status_code == 200, response.json()
        body = response.json()["data"]
        assert body["full_name"] == "Valiyeva Nodira"
        assert body["phone"] == "+998933334455"
        assert body["phone_alt"] == "+998901112233"

    def test_editing_cannot_make_both_numbers_the_same(self, tenant_a):
        client = tenant_a.client()
        guardian_id = _create(client, phone_alt="+998905554433").json()["data"]["id"]
        response = client.patch(
            f"{URL}/{guardian_id}", {"phone_alt": "+998901112233"}, format="json"
        )
        assert response.status_code == 400

    def test_another_kindergartens_guardian_is_404(self, tenant_a, tenant_b):
        other = _create(tenant_b.client()).json()["data"]["id"]
        response = tenant_a.client().patch(f"{URL}/{other}", {"last_name": "X"}, format="json")
        assert response.status_code == 404


class TestBotLinking:
    def _guardian(self, tenant, **extra) -> Guardian:
        from apps.children.models import Child
        from apps.children.services import attach_guardian

        with organization_context(tenant.organization.id):
            guardian = Guardian.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Nodira",
                last_name="Karimova",
                phone="+998901112233",
                **extra,
            )
            child = Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Ali",
                last_name="Valiyev",
                date_of_birth=date(2021, 1, 1),
                gender="male",
            )
            attach_guardian(child=child, guardian=guardian, relation="mother", is_primary=True)
        return guardian

    def test_the_second_number_also_connects_the_bot(self, tenant_a):
        from apps.children import telegram as links
        from apps.parent_bot.index import organizations_for, phone_digest
        from apps.parent_bot.models import ContactKind

        guardian = self._guardian(tenant_a, phone_alt="+998905554433")
        # Indeks ikkala raqamni ham biladi.
        assert organizations_for(ContactKind.PHONE, phone_digest("+998905554433"))

        with organization_context(tenant_a.organization.id):
            linked = links.link_by_phone(phone="+998905554433", chat_id="777")
        assert linked is not None and linked.pk == guardian.pk

    def test_the_first_number_still_connects(self, tenant_a):
        from apps.children import telegram as links

        guardian = self._guardian(tenant_a, phone_alt="+998905554433")
        with organization_context(tenant_a.organization.id):
            linked = links.link_by_phone(phone="+998901112233", chat_id="778")
        assert linked is not None and linked.pk == guardian.pk
