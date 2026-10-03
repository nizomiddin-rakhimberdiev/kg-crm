"""
"Your child did not come today" (design §3.3, P6-5).

Off by default; once switched on, it goes once per child per day, only
on a change to absent, only for today — and it never touches money.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.attendance.services import mark_bulk
from apps.children.models import Child, ChildGuardian, Group, Guardian
from apps.children.services import enroll_child
from apps.core.tenancy import organization_context
from apps.notifications.models import Notification

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.fixture(autouse=True)
def _commit_now(monkeypatch):
    """`on_commit` callbacks run immediately — the test DB never commits."""
    monkeypatch.setattr("django.db.transaction.on_commit", lambda fn, *a, **k: fn())


@pytest.fixture
def child(tenant_a):
    with organization_context(tenant_a.organization.id):
        group = Group.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Quyosh", capacity=9
        )
        child = Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 1, 1),
            gender="male",
        )
        enroll_child(child=child, group=group)
        guardian = Guardian.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Nodira",
            last_name="Karimova",
            phone="+998901112233",
            telegram_chat_id="777",
        )
        ChildGuardian.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            child=child,
            guardian=guardian,
            relation="mother",
            is_primary=True,
        )
    return child, group


def _mark(tenant, group, child, status, on=None):
    with organization_context(tenant.organization.id):
        mark_bulk(
            organization=tenant.organization,
            branch=tenant.branch,
            group=group,
            attendance_date=on or timezone.localdate(),
            records=[{"child_id": child.id, "status": status}],
        )


def _switch_on(tenant):
    from apps.settings_app.services import set_setting

    with organization_context(tenant.organization.id):
        set_setting(organization=tenant.organization, key="notifications.absence_alert", value=True)


def _count(tenant) -> int:
    with organization_context(tenant.organization.id):
        return Notification.objects.filter(template_code="absence_notice").count()


def test_off_by_default(tenant_a, child):
    kid, group = child
    _mark(tenant_a, group, kid, "absent")
    assert _count(tenant_a) == 0


def test_switched_on_it_tells_the_parent(tenant_a, child):
    kid, group = child
    _switch_on(tenant_a)
    _mark(tenant_a, group, kid, "absent")
    assert _count(tenant_a) == 1
    with organization_context(tenant_a.organization.id):
        assert "Valiyev Ali" in Notification.objects.get().rendered_body


def test_correcting_the_register_back_and_forth_sends_once(tenant_a, child):
    kid, group = child
    _switch_on(tenant_a)
    _mark(tenant_a, group, kid, "absent")
    _mark(tenant_a, group, kid, "present")
    _mark(tenant_a, group, kid, "absent")
    _mark(tenant_a, group, kid, "absent")
    assert _count(tenant_a) == 1


def test_a_past_day_sends_nothing(tenant_a, child):
    kid, group = child
    _switch_on(tenant_a)
    _mark(tenant_a, group, kid, "absent", on=timezone.localdate() - timedelta(days=1))
    assert _count(tenant_a) == 0


def test_it_moves_no_money(tenant_a, child):
    from apps.finance.balance import child_balance

    kid, group = child
    _switch_on(tenant_a)
    _mark(tenant_a, group, kid, "absent")
    with organization_context(tenant_a.organization.id):
        assert child_balance(kid).balance == 0
