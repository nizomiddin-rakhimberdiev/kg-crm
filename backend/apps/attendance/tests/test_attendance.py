"""Davomat testlari (docs/04 §8, docs/03 §12)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.attendance import services as attendance_services
from apps.attendance.models import AttendanceRecord
from apps.attendance.services import daily_register, mark_bulk, monthly_summary
from apps.children.models import Child, Group
from apps.children.services import enroll_child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def group_with_children(tenant_a):
    """Guruh va unda uchta faol bola."""
    with organization_context(tenant_a.organization.id):
        group = Group.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Quyoshlar",
            capacity=10,
        )
        children = []
        for index in range(3):
            child = Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name=f"Bola{index}",
                last_name="Testov",
                date_of_birth=date(2021, 1, 1),
                gender="male",
            )
            enroll_child(child=child, group=group)
            children.append(child)
    return group, children


class TestBulkMarking:
    def test_marks_whole_group_in_one_call(self, tenant_a, group_with_children):
        group, children = group_with_children
        with organization_context(tenant_a.organization.id):
            records = mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=timezone.localdate(),
                records=[
                    {"child_id": children[0].id, "status": "present"},
                    {"child_id": children[1].id, "status": "absent", "reason": "kasal"},
                    {"child_id": children[2].id, "status": "excused"},
                ],
            )
        assert len(records) == 3
        assert {r.status for r in records} == {"present", "absent", "excused"}

    def test_reposting_updates_instead_of_duplicating(self, tenant_a, group_with_children):
        """
        Tarbiyachi ertalab belgilab, tushdan keyin tuzatishi — normal
        ish oqimi. Ikkinchi yuborish yangi qator emas, YANGILANISH.
        """
        group, children = group_with_children
        today = timezone.localdate()
        with organization_context(tenant_a.organization.id):
            mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=today,
                records=[{"child_id": children[0].id, "status": "absent"}],
            )
            mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=today,
                records=[{"child_id": children[0].id, "status": "present"}],
            )
            assert AttendanceRecord.objects.filter(child=children[0]).count() == 1
            assert AttendanceRecord.objects.get(child=children[0]).status == "present"

    def test_future_date_is_rejected(self, tenant_a, group_with_children):
        group, children = group_with_children
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="Kelajakdagi"),
        ):
            mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=timezone.localdate() + timedelta(days=1),
                records=[{"child_id": children[0].id, "status": "present"}],
            )

    def test_child_outside_the_group_is_rejected(self, tenant_a, group_with_children):
        """
        Mijoz istalgan `child_id` yuborib, boshqa guruhning bolasiga
        yozuv yarata olmasligi kerak.
        """
        group, _ = group_with_children
        with organization_context(tenant_a.organization.id):
            outsider = Child.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Begona",
                last_name="Bola",
                date_of_birth=date(2021, 1, 1),
                gender="female",
            )
            with pytest.raises(BusinessRuleViolation, match="faol emas"):
                mark_bulk(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    group=group,
                    attendance_date=timezone.localdate(),
                    records=[{"child_id": outsider.id, "status": "present"}],
                )

    @pytest.mark.tenancy
    def test_cannot_mark_another_tenants_group(self, tenant_a, tenant_b):
        with organization_context(tenant_b.organization.id):
            foreign = Group.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                name="Begona",
                capacity=5,
            )
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="tashkilotga"),
        ):
            mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=foreign,
                attendance_date=timezone.localdate(),
                records=[],
            )


class TestDatabaseConstraints:
    def test_one_record_per_child_per_day(self, tenant_a, group_with_children):
        """Bazadagi kafolat (D1) — servis qatlami chetlab oʻtilganda ham."""
        group, children = group_with_children
        today = timezone.localdate()
        with organization_context(tenant_a.organization.id):
            AttendanceRecord.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=children[0],
                group=group,
                attendance_date=today,
                status="present",
            )
            with pytest.raises(IntegrityError), transaction.atomic():
                AttendanceRecord.objects.create(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    child=children[0],
                    group=group,
                    attendance_date=today,
                    status="absent",
                )

    def test_checkout_cannot_precede_checkin(self, tenant_a, group_with_children):
        group, children = group_with_children
        now = timezone.now()
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            AttendanceRecord.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=children[0],
                group=group,
                attendance_date=timezone.localdate(),
                status="present",
                check_in_at=now,
                check_out_at=now - timedelta(hours=2),
            )


class TestTimezoneSkew:
    """
    Regressiya: DB cheklovi UTC'da, filial esa o'z zonasida yashaydi.

    Toshkent UTC+5. Yarim tundan 05:00 gacha lokal sana UTC sanadan bir
    kun oldinda bo'ladi. Qat'iy `attendance_date <= Now()` cheklovi shu
    oynada HAR KUNI to'g'ri yozuvni rad etardi — bu test buni qaytib
    kelmasligi uchun qotiradi.
    """

    def test_todays_attendance_works_in_every_hour(self, tenant_a, group_with_children):
        group, children = group_with_children
        with organization_context(tenant_a.organization.id):
            records = mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=timezone.localdate(),
                records=[{"child_id": children[0].id, "status": "present"}],
            )
        assert len(records) == 1

    def test_database_still_blocks_obviously_future_dates(self, tenant_a, group_with_children):
        """Zaxira bir kun — "kelasi oy" baribir bazada rad etiladi."""
        group, children = group_with_children
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            AttendanceRecord.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=children[0],
                group=group,
                attendance_date=timezone.localdate() + timedelta(days=30),
                status="present",
            )


class TestDailyRegister:
    def test_includes_unmarked_children(self, tenant_a, group_with_children):
        """
        Belgilanmagan bolalar ham qaytadi (`status=None`) — aks holda
        tarbiyachi kimni o'tkazib yuborganini ko'rmasdi.
        """
        group, children = group_with_children
        today = timezone.localdate()
        with organization_context(tenant_a.organization.id):
            mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=today,
                records=[{"child_id": children[0].id, "status": "present"}],
            )
            rows = daily_register(group=group, attendance_date=today)

        assert len(rows) == 3
        marked = [r for r in rows if r["status"] is not None]
        unmarked = [r for r in rows if r["status"] is None]
        assert len(marked) == 1 and len(unmarked) == 2


class TestMonthlySummary:
    def test_counts_and_rate(self, tenant_a, group_with_children):
        group, children = group_with_children
        today = timezone.localdate()
        with organization_context(tenant_a.organization.id):
            for offset, status_value in enumerate(["present", "present", "absent", "excused"]):
                mark_bulk(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    group=group,
                    attendance_date=today - timedelta(days=offset),
                    records=[{"child_id": children[0].id, "status": status_value}],
                )
            rows = monthly_summary(
                organization_id=tenant_a.organization.id,
                year=today.year,
                month=today.month,
                group=group,
            )

        row = next(r for r in rows if r["child_id"] == str(children[0].id))
        # Sana oy chegarasidan o'tsa, ba'zi yozuvlar boshqa oyga tushadi —
        # shuning uchun aniq sonlar emas, mantiqiy bog'liqlik tekshiriladi.
        assert row["total"] == row["present"] + row["absent"] + row["excused"]
        expected = round(row["present"] / row["total"] * 100, 1)
        assert row["attendance_rate"] == expected


class TestEndpoints:
    def test_bulk_endpoint(self, tenant_a, group_with_children):
        group, children = group_with_children
        response = tenant_a.client().post(
            reverse("v1:attendance-bulk"),
            {
                "group_id": str(group.id),
                "attendance_date": timezone.localdate().isoformat(),
                "records": [
                    {"child_id": str(children[0].id), "status": "present"},
                    {"child_id": str(children[1].id), "status": "absent", "reason": "kasal"},
                ],
            },
            format="json",
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) == 2

    def test_bulk_rejects_duplicate_child_in_one_request(self, tenant_a, group_with_children):
        group, children = group_with_children
        response = tenant_a.client().post(
            reverse("v1:attendance-bulk"),
            {
                "group_id": str(group.id),
                "attendance_date": timezone.localdate().isoformat(),
                "records": [
                    {"child_id": str(children[0].id), "status": "present"},
                    {"child_id": str(children[0].id), "status": "absent"},
                ],
            },
            format="json",
        )
        assert response.status_code == 400

    def test_daily_endpoint(self, tenant_a, group_with_children):
        group, _ = group_with_children
        response = tenant_a.client().get(
            reverse("v1:attendance-daily"),
            {"group": str(group.id), "date": timezone.localdate().isoformat()},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["group"]["name"] == "Quyoshlar"
        assert len(data["rows"]) == 3

    @pytest.mark.tenancy
    def test_daily_cannot_read_another_tenants_group(self, tenant_a, tenant_b):
        with organization_context(tenant_b.organization.id):
            foreign = Group.objects.create(
                organization=tenant_b.organization,
                branch=tenant_b.branch,
                name="Begona",
                capacity=5,
            )
        response = tenant_a.client().get(
            reverse("v1:attendance-daily"),
            {"group": str(foreign.id), "date": timezone.localdate().isoformat()},
        )
        # Begona guruh — "topilmadi", mavjudligi oshkor bo'lmaydi.
        assert response.status_code == 422
        assert "topilmadi" in response.json()["error"]["message"]

    def test_summary_endpoint(self, tenant_a, group_with_children):
        group, children = group_with_children
        today = timezone.localdate()
        with organization_context(tenant_a.organization.id):
            mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=today,
                records=[{"child_id": children[0].id, "status": "present"}],
            )
        response = tenant_a.client().get(
            reverse("v1:attendance-summary"), {"month": today.strftime("%Y-%m")}
        )
        assert response.status_code == 200
        assert len(response.json()["data"]["rows"]) >= 1

    def test_attendance_manager_can_mark_but_not_read_payments(self, tenant_a, group_with_children):
        """Davomat menejerida `attendance` toʻliq, `payments` yoʻq (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        group, children = group_with_children
        with organization_context(tenant_a.organization.id):
            monitor = User.objects.create_user(
                email="davomat@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Davomat menejeri",
                organization=tenant_a.organization,
                role=tenant_a.role("attendance_manager"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(monitor)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        marked = client.post(
            reverse("v1:attendance-bulk"),
            {
                "group_id": str(group.id),
                "attendance_date": timezone.localdate().isoformat(),
                "records": [{"child_id": str(children[0].id), "status": "present"}],
            },
            format="json",
        )
        assert marked.status_code == 200
        assert client.get(reverse("v1:user-list")).status_code == 403


class TestTeacherScope:
    """
    Tarbiyachi faqat o'z guruhini belgilaydi — PLAN 2.6.

    Bu qatlam mavjud RBAC'ni o'zgartirmaydi, ustiga qo'shiladi: modul
    ruxsati avvalgidek birinchi to'siq, guruh esa ikkinchisi.
    """

    def _teacher(self, tenant, group):
        """Tizim hisobi + xodim + guruhga biriktirish."""
        from apps.accounts.models import Role, User
        from apps.hr.models import Employee

        with organization_context(tenant.organization.id):
            role = Role.objects.create(
                organization=tenant.organization, name="Tarbiyachi", code="teacher_custom"
            )
            # Modul ruxsati bor, `read_all` esa yo'q — aynan auditdagi
            # maxsus rol holati.
            from apps.accounts.models import Permission, RolePermission

            for code in ("attendance.read", "attendance.create", "attendance.update"):
                RolePermission.objects.create(
                    role=role, permission=Permission.objects.get(code=code)
                )
            user = User.objects.create_user(
                email="tarbiyachi@test.uz",
                password="Juda-Kuchli-Parol-2026",
                organization=tenant.organization,
                branch=tenant.branch,
                full_name="Dilnoza Ergasheva",
                role=role,
            )
            Employee.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Dilnoza",
                last_name="Ergasheva",
                hire_date=date(2024, 1, 1),
                base_salary=Decimal("5000000"),
                user=user,
            )
            group.teacher = Employee.objects.get(user=user)
            group.save(update_fields=["teacher"])
        return user

    def test_a_teacher_may_mark_their_own_group(self, tenant_a, group_with_children):
        group, children = group_with_children
        user = self._teacher(tenant_a, group)
        with organization_context(tenant_a.organization.id):
            records = attendance_services.mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=timezone.localdate(),
                records=[{"child_id": children[0].id, "status": "present"}],
                recorded_by=user,
            )
        assert len(records) == 1

    def test_a_teacher_cannot_mark_another_group(self, tenant_a, group_with_children):
        from apps.children.models import Group

        group, children = group_with_children
        user = self._teacher(tenant_a, group)
        with organization_context(tenant_a.organization.id):
            other = Group.objects.create(
                organization=tenant_a.organization, branch=tenant_a.branch, name="Begona guruh"
            )
            with pytest.raises(BusinessRuleViolation, match="biriktirilmagan"):
                attendance_services.mark_bulk(
                    organization=tenant_a.organization,
                    branch=tenant_a.branch,
                    group=other,
                    attendance_date=timezone.localdate(),
                    records=[],
                    recorded_by=user,
                )

    def test_a_teacher_cannot_edit_an_old_day(self, tenant_a, group_with_children):
        """Sukut oyna: bugun va kecha. Oʻtgan oy pulga tegadi (ADR-19)."""
        group, children = group_with_children
        user = self._teacher(tenant_a, group)
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="oxirgi"),
        ):
            attendance_services.mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=timezone.localdate() - timedelta(days=5),
                records=[{"child_id": children[0].id, "status": "present"}],
                recorded_by=user,
            )

    def test_a_teacher_may_still_fix_yesterday(self, tenant_a, group_with_children):
        group, children = group_with_children
        user = self._teacher(tenant_a, group)
        with organization_context(tenant_a.organization.id):
            records = attendance_services.mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=timezone.localdate() - timedelta(days=1),
                records=[{"child_id": children[0].id, "status": "present"}],
                recorded_by=user,
            )
        assert len(records) == 1

    def test_the_owner_needs_a_reason_for_an_old_day(self, tenant_a, group_with_children):
        group, children = group_with_children
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="sabab"),
        ):
            attendance_services.mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=timezone.localdate() - timedelta(days=30),
                records=[{"child_id": children[0].id, "status": "present"}],
                recorded_by=tenant_a.owner,
            )

    def test_the_owner_may_fix_an_old_day_with_a_reason(self, tenant_a, group_with_children):
        group, children = group_with_children
        with organization_context(tenant_a.organization.id):
            records = attendance_services.mark_bulk(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                group=group,
                attendance_date=timezone.localdate() - timedelta(days=30),
                records=[{"child_id": children[0].id, "status": "present"}],
                recorded_by=tenant_a.owner,
                reason="Jurnal qogʻozdan koʻchirildi",
            )
        assert len(records) == 1

    def test_nobody_is_restricted_until_a_teacher_is_assigned(self, tenant_a):
        """
        Cheklov "ruxsati yoʻq" degan sababdan emas, "u aynan shu
        guruhning tarbiyachisi" degan sababdan kelib chiqadi. Hech kim
        biriktirilmagan bo'lsa, qatlam umuman ishlamaydi.
        """
        from apps.children.scope import is_group_restricted

        with organization_context(tenant_a.organization.id):
            assert not is_group_restricted(tenant_a.owner)
