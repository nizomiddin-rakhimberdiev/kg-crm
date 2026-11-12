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

    def test_a_transfer_names_both_pots(self, tenant_a):
        """
        Qopdan qopga o'tkazma `from`/`to` kalitlari bilan yoziladi va
        ular UUID bo'lib qolardi: jurnalda "c28a8dc0-… → 617524bc-…"
        turardi (audit, 2026-10-21). Kalit nomi turni aytmaydi, lekin
        YOZUV TURI aytadi — `cash_transfer` ning `from`/`to` si
        doimo kassa hisobi.
        """
        from apps.cash.models import CashAccount

        with organization_context(tenant_a.organization.id):
            source = CashAccount.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Sayyor kassa",
                kind="cash",
            )
            target = CashAccount.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                name="Ikkinchi bank hisobi",
                kind="bank",
            )
            audit.record(
                action="create",
                organization=tenant_a.organization,
                actor=tenant_a.owner,
                entity_type="cash_transfer",
                entity_id=source.id,
                changes={"from": str(source.id), "to": str(target.id), "amount": "500000.00"},
            )
        row = tenant_a.client().get(reverse("v1:audit-log-list")).json()["data"][0]
        assert row["changes_labels"]["from"] == str(source)
        assert row["changes_labels"]["to"] == str(target)

    def test_an_id_suffixed_key_is_named_too(self, tenant_a, child):
        """
        `employee_id`, `product_id` — kalit `_id` bilan tugaydi va
        oldidagi so'z turni aytadi. Ilgari ular ham UUID bo'lib
        qolardi.
        """
        from apps.hr.models import Employee

        with organization_context(tenant_a.organization.id):
            employee = Employee.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Dilnoza",
                last_name="Yoʻldosheva",
                hire_date=date(2026, 1, 10),
            )
            audit.record(
                action="update",
                organization=tenant_a.organization,
                actor=tenant_a.owner,
                entity_type="employee_advance",
                entity_id=employee.id,
                changes={"employee_id": str(employee.id), "amount": "250000.00"},
            )
        row = tenant_a.client().get(reverse("v1:audit-log-list")).json()["data"][0]
        assert row["changes_labels"]["employee_id"] == str(employee)

    def test_a_deleted_row_leaves_the_entry_in_place(self, tenant_a, child):
        """
        Yozuv YO'QOLMAYDI va o'chirilgan bolaning nomini saqlaydi.

        2026-11-12 gacha nom jonli olinardi va o'chirilgandan keyin bo'sh
        qolardi; endi u yozuv paytida saqlanadi (`entity_label`).
        """
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
        assert row["entity_label"] == child.full_name
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
