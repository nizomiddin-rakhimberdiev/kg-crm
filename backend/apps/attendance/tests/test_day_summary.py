"""
Kun boʻyicha umumiy davomat (mijoz soʻrovi, 2026-10-23).

Davomat ekranida "Keldi / Sababli / Kelmagan" faqat TANLANGAN guruh
boʻyicha koʻrinardi, va u ham pastda, kichkina yozuvda. Mudira esa
avval butun bogʻcha boʻyicha bilishni xohlaydi: bugun nechta bola
keldi, nechtasi belgilanmagan.

Umumiy ko'rsatkich foydalanuvchining OʻZ koʻlamida hisoblanadi
(ADR-21): guruhga biriktirilgan tarbiyachi faqat oʻz guruhlarini
koʻradi, ya'ni uning "hammasi" — oʻsha guruhlar.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.attendance.services import mark_bulk
from apps.children.models import Child, Group
from apps.children.services import enroll_child
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


def _group(tenant: Any, name: str, count: int) -> tuple[Group, list[Child]]:
    group = Group.objects.create(
        organization=tenant.organization, branch=tenant.branch, name=name, capacity=10
    )
    children = []
    for index in range(count):
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=f"{name}{index}",
            last_name="Testov",
            date_of_birth=date(2021, 1, 1),
            gender="male",
        )
        enroll_child(child=child, group=group)
        children.append(child)
    return group, children


def _summary(client: Any, day: Any) -> dict[str, Any]:
    response = client.get(reverse("v1:attendance-day-summary"), {"date": day.isoformat()})
    assert response.status_code == 200, response.content
    return response.json()["data"]


def test_the_day_is_counted_across_every_group(tenant_a: Any):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        first, kids_a = _group(tenant_a, "Quyosh", 3)
        second, kids_b = _group(tenant_a, "Oy", 2)
        mark_bulk(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            group=first,
            attendance_date=today,
            records=[
                {"child_id": kids_a[0].id, "status": "present"},
                {"child_id": kids_a[1].id, "status": "excused", "reason": "shifokorda"},
            ],
            recorded_by=tenant_a.owner,
        )
        mark_bulk(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            group=second,
            attendance_date=today,
            records=[{"child_id": kids_b[0].id, "status": "absent"}],
            recorded_by=tenant_a.owner,
        )

    data = _summary(tenant_a.client(), today)

    assert data["total"] == 5
    assert data["present"] == 1
    assert data["excused"] == 1
    assert data["absent"] == 1
    # Belgilanmagan — "kelmagan" EMAS: ikkisi boshqa narsa (ADR-19).
    assert data["unmarked"] == 2
    assert data["marked"] == 3


def test_every_group_is_listed_even_when_nothing_is_marked(tenant_a: Any):
    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        _group(tenant_a, "Quyosh", 2)
        _group(tenant_a, "Oy", 1)

    data = _summary(tenant_a.client(), today)

    assert data["total"] == 3
    assert data["marked"] == 0
    assert {row["name"] for row in data["groups"]} == {"Quyosh", "Oy"}
    assert all(row["marked"] == 0 for row in data["groups"])


def test_a_group_teacher_only_counts_their_own_children(tenant_a: Any):
    """ADR-21: tarbiyachining "hammasi" — uning guruhlari."""
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import Permission, Role, RolePermission, User
    from apps.hr.models import Employee

    today = timezone.localdate()
    with organization_context(tenant_a.organization.id):
        mine, _ = _group(tenant_a, "Meniki", 2)
        _group(tenant_a, "Begona", 4)
        # Modul ruxsati bor, `children.read_all` esa yoʻq — bogʻcha
        # qoʻlda yasaydigan "Tarbiyachi" roli aynan shunday (ADR-21).
        role = Role.objects.create(
            organization=tenant_a.organization, name="Tarbiyachi", code="teacher_day"
        )
        for code in ("attendance.read", "attendance.create", "attendance.update"):
            RolePermission.objects.create(role=role, permission=Permission.objects.get(code=code))
        teacher = User.objects.create_user(
            email="tarbiyachi@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Tarbiyachi",
            organization=tenant_a.organization,
            role=role,
            branch=tenant_a.branch,
        )
        employee = Employee.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Tarbiyachi",
            last_name="Xodim",
            hire_date=date(2026, 1, 10),
            user=teacher,
        )
        mine.teacher = employee
        mine.save(update_fields=["teacher"])
        tokens = issue_token_pair(teacher)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    data = _summary(client, today)

    assert data["total"] == 2
    assert [row["name"] for row in data["groups"]] == ["Meniki"]


@pytest.mark.tenancy
def test_another_organization_is_never_counted(tenant_a: Any, tenant_b: Any):
    today = timezone.localdate()
    with organization_context(tenant_b.organization.id):
        _group(tenant_b, "Begona", 5)
    with organization_context(tenant_a.organization.id):
        _group(tenant_a, "Meniki", 1)

    data = _summary(tenant_a.client(), today)

    assert data["total"] == 1
