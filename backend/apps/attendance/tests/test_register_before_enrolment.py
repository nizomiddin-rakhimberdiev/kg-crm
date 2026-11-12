"""
Bola kelmagan kun — jurnalda ham, xabarda ham to'g'ri (audit 2026-11-12, G2).

* Xato xabari qabul sanasini "bola shu kuni bog'chada bo'lmagan" deb
  aytardi — ya'ni teskarisini.
* 20-noyabrda keladigan bola 10-noyabr jurnalida turardi: tarbiyachi
  uni "kelmadi" deb belgilardi va keyin saqlash rad etilardi.
"""

from __future__ import annotations

from datetime import date

import pytest

from apps.attendance.services import daily_register, mark_bulk
from apps.children.models import Child, Group
from apps.children.services import enroll_child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(tenant_a):
    with organization_context(tenant_a.organization.id):
        group = Group.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Quyoshlar",
            capacity=10,
        )
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Kamola",
            last_name="Rahimova",
            date_of_birth=date(2021, 1, 1),
            gender="female",
            enrolled_on=date(2026, 6, 20),
        )
        enroll_child(child=child, group=group)
    return group, child


def test_the_message_names_the_day_and_the_arrival(tenant_a, setup):
    group, child = setup
    with (
        organization_context(tenant_a.organization.id),
        pytest.raises(BusinessRuleViolation) as error,
    ):
        mark_bulk(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            group=group,
            attendance_date=date(2026, 6, 10),
            records=[{"child_id": child.id, "status": "absent"}],
        )
    message = str(error.value.detail)
    assert "10.06.2026" in message
    assert "20.06.2026" in message


def test_a_child_not_yet_arrived_is_not_on_the_register(tenant_a, setup):
    group, child = setup
    with organization_context(tenant_a.organization.id):
        before = daily_register(group=group, attendance_date=date(2026, 6, 10))
        after = daily_register(group=group, attendance_date=date(2026, 6, 22))
    assert [row["child_id"] for row in before] == []
    assert [row["child_id"] for row in after] == [str(child.id)]
