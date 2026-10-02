"""
Jurnalda UUID o'rniga NOM (PLAN 4.4).

Auditda yozuv shunday ko'rinardi::

    Yangilandi  child  child: "4f3c9e21-…", group: "9a1b7c04-…"

Formal jihatdan to'g'ri va amalda foydasiz: jurnal aynan "kim nima
qildi?" degan savol uchun bor.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse

from apps.audit import services as audit
from apps.children.models import Child, Group
from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.fixture
def child(tenant_a) -> Child:
    with organization_context(tenant_a.organization.id):
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Karimov",
            date_of_birth=date(2021, 5, 5),
        )


class TestLabels:
    def test_the_entity_is_named_not_numbered(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            audit.record(
                action="update",
                organization=tenant_a.organization,
                actor=tenant_a.owner,
                entity_type="child",
                entity_id=child.id,
                changes={"status": "active"},
            )
        response = tenant_a.client().get(reverse("v1:audit-log-list"))
        row = response.json()["data"][0]
        assert row["entity_label"] == child.full_name

    def test_uuids_inside_changes_are_named_too(self, tenant_a, child):
        with organization_context(tenant_a.organization.id):
            group = Group.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Quyosh",
                capacity=20,
            )
            audit.record(
                action="update",
                organization=tenant_a.organization,
                actor=tenant_a.owner,
                entity_type="enrollment",
                entity_id=group.id,
                changes={"child": str(child.id), "group": str(group.id)},
            )
        response = tenant_a.client().get(reverse("v1:audit-log-list"))
        row = response.json()["data"][0]
        assert row["changes_labels"]["child"] == child.full_name
        assert row["changes_labels"]["group"] == "Quyosh"

    def test_a_deleted_row_leaves_the_entry_in_place(self, tenant_a, child):
        """Nom topilmasa yozuv YO'QOLMAYDI — u faqat nomsiz qoladi."""
        with organization_context(tenant_a.organization.id):
            audit.record(
                action="delete",
                organization=tenant_a.organization,
                actor=tenant_a.owner,
                entity_type="child",
                entity_id=child.id,
                changes={},
            )
            child.delete()
        response = tenant_a.client().get(reverse("v1:audit-log-list"))
        row = response.json()["data"][0]
        assert row["entity_label"] == ""
        assert row["entity_id"] is not None

    @pytest.mark.tenancy
    def test_a_name_from_another_organization_is_never_resolved(self, tenant_a, tenant_b):
        """Jurnal tenant chegarasini buzmaydi — nom ham chegara ichida."""
        with organization_context(tenant_b.organization.id):
            foreign = Child.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                first_name="Begona",
                last_name="Bola",
                date_of_birth=date(2021, 5, 5),
            )
        with organization_context(tenant_a.organization.id):
            # Begona UUID bilan yozuv (amalda bo'lmaydi, lekin
            # nomni hal qilish chegarasi sinovdan o'tishi kerak).
            audit.record(
                action="update",
                organization=tenant_a.organization,
                actor=tenant_a.owner,
                entity_type="child",
                entity_id=foreign.id,
                changes={"child": str(foreign.id)},
            )
        response = tenant_a.client().get(reverse("v1:audit-log-list"))
        row = response.json()["data"][0]
        assert row["entity_label"] == ""
        assert row["changes_labels"] == {}

    def test_one_query_per_entity_type(self, tenant_a, child, django_assert_max_num_queries):
        with organization_context(tenant_a.organization.id):
            for _ in range(10):
                audit.record(
                    action="update",
                    organization=tenant_a.organization,
                    actor=tenant_a.owner,
                    entity_type="child",
                    entity_id=child.id,
                    changes={"child": str(child.id)},
                )
        client = tenant_a.client()
        # Qator-qator so'rash 10 qator uchun 10 ta so'rov bo'lardi.
        with django_assert_max_num_queries(12):
            client.get(reverse("v1:audit-log-list"))
