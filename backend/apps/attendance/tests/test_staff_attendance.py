"""
Xodimlar davomati va oylik tabel (docs/04 §8.3, 2026-10).

Mijoz so'rovi: xodimlarni ham davomat qilish — oy oxirida oylik
hisobotini chiqarish oson bo'lsin. Testlar tabel raqamlari to'g'riligini
va kim nimani ko'ra/belgilay olishini qotiradi.
"""

from __future__ import annotations

import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.authentication import issue_token_pair
from apps.accounts.models import User
from apps.attendance.models import Holiday, StaffAttendance
from apps.branches.models import Branch
from apps.core.tenancy import organization_context
from apps.hr.models import Employee
from apps.reports.models import ExportStatus, ReportExport
from apps.reports.tasks import generate_export
from apps.subscriptions.models import Subscription, SubscriptionStatus

pytestmark = pytest.mark.django_db

PASSWORD = "Juda-Kuchli-Parol-2026"  # noqa: S105
DAILY = "/api/v1/staff-attendance/daily"
BULK = "/api/v1/staff-attendance/bulk"
TIMESHEET = "/api/v1/staff-attendance/timesheet"


def _employee(
    tenant, last: str, *, hired: date = date(2025, 1, 6), branch=None, **extra
) -> Employee:
    with organization_context(tenant.organization.id):
        return Employee.objects.create(
            organization=tenant.organization,
            branch=branch or tenant.branch,
            first_name="Xodim",
            last_name=last,
            hire_date=hired,
            base_salary=Decimal("3000000"),
            **extra,
        )


def _member(tenant, role_code: str, email: str, branch=None) -> APIClient:
    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=email,
            password=PASSWORD,
            full_name=role_code,
            organization=tenant.organization,
            role=tenant.role(role_code),
            branch=branch or tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def _mark(client, day: date, *rows, branch=None):
    body = {
        "attendance_date": day.isoformat(),
        "records": [
            {"employee_id": str(emp.id), "status": status, "note": ""} for emp, status in rows
        ],
    }
    if branch is not None:
        body["branch_id"] = str(branch.id)
    return client.post(BULK, body, format="json")


class TestDailyMarking:
    def test_register_lists_everyone_employed_that_day(self, tenant_a):
        today = timezone.localdate()
        working = _employee(tenant_a, "Ishlayotgan")
        _employee(tenant_a, "Ertaga", hired=today + timedelta(days=1))
        _employee(
            tenant_a,
            "Ketgan",
            hired=date(2024, 1, 8),
            termination_date=date(2025, 1, 1),
            employment_status="terminated",
            is_active=False,
        )

        rows = tenant_a.client().get(DAILY, {"date": today.isoformat()}).json()["data"]["rows"]
        assert [row["employee_id"] for row in rows] == [str(working.id)]
        assert rows[0]["status"] is None

    def test_bulk_marks_and_a_second_call_corrects(self, tenant_a):
        today = timezone.localdate()
        ali = _employee(tenant_a, "Aliyev")
        vali = _employee(tenant_a, "Valiyev")
        client = tenant_a.client()

        assert _mark(client, today, (ali, "absent"), (vali, "present")).status_code == 200
        # Ertalab "kelmadi", soat 10 da keldi — tuzatish yangi qator emas.
        assert _mark(client, today, (ali, "present")).status_code == 200

        with organization_context(tenant_a.organization.id):
            assert StaffAttendance.objects.filter(employee=ali).count() == 1
            assert StaffAttendance.objects.get(employee=ali).status == "present"
            assert StaffAttendance.objects.get(employee=vali).recorded_by == tenant_a.owner

    def test_future_day_is_refused(self, tenant_a):
        ali = _employee(tenant_a, "Aliyev")
        tomorrow = timezone.localdate() + timedelta(days=1)
        assert _mark(tenant_a.client(), tomorrow, (ali, "present")).status_code == 422

    def test_day_before_hiring_is_refused(self, tenant_a):
        new = _employee(tenant_a, "Yangi", hired=timezone.localdate())
        yesterday = timezone.localdate() - timedelta(days=1)
        assert _mark(tenant_a.client(), yesterday, (new, "present")).status_code == 422


class TestTimesheet:
    def test_counts_working_days_holidays_and_late_hire(self, tenant_a):
        """
        2026-03: 22 ta ish kuni (du–ju). 9-mart bayram → 21.
        16-martda ishga kirgan xodim uchun — 12 (16–31, bayramsiz).
        """
        with organization_context(tenant_a.organization.id):
            Holiday.objects.create(
                organization=tenant_a.organization, holiday_date=date(2026, 3, 9), name="Bayram"
            )
        full = _employee(tenant_a, "Butun")
        late = _employee(tenant_a, "Kech", hired=date(2026, 3, 16))
        client = tenant_a.client()
        _mark(client, date(2026, 3, 2), (full, "present"), (late, "present"))  # late: hali yo'q
        _mark(client, date(2026, 3, 2), (full, "present"))
        _mark(client, date(2026, 3, 3), (full, "sick"))
        _mark(client, date(2026, 3, 4), (full, "leave"))
        _mark(client, date(2026, 3, 5), (full, "absent"))
        _mark(client, date(2026, 3, 16), (late, "present"))

        data = client.get(TIMESHEET, {"month": "2026-03"}).json()["data"]
        rows = {row["full_name"].split()[0]: row for row in data["employees"]}

        assert data["days_in_month"] == 31
        assert len(data["working_dates"]) == 21
        assert rows["Butun"]["working_days"] == 21
        assert rows["Kech"]["working_days"] == 12
        assert (rows["Butun"]["present"], rows["Butun"]["sick"]) == (1, 1)
        assert (rows["Butun"]["leave"], rows["Butun"]["absent"]) == (1, 1)
        assert rows["Butun"]["days"] == {"2": "present", "3": "sick", "4": "leave", "5": "absent"}
        # O'tgan oy — barcha ish kunlari "bugungacha": 21 − 4 belgilangan.
        assert rows["Butun"]["unmarked"] == 17
        assert data["totals"]["present"] == 2

    def test_employee_who_left_mid_month_keeps_the_month(self, tenant_a):
        left = _employee(
            tenant_a,
            "Ketgan",
            termination_date=date(2026, 3, 13),
            employment_status="terminated",
            is_active=False,
        )
        rows = tenant_a.client().get(TIMESHEET, {"month": "2026-03"}).json()["data"]["employees"]
        row = next(r for r in rows if r["employee_id"] == str(left.id))
        assert row["working_days"] == 10  # 2–13 mart


class TestAccess:
    def test_cashier_without_attendance_permission_is_403(self, tenant_a):
        client = _member(tenant_a, "cashier", "kassir@alfa.uz")
        assert client.get(DAILY, {"date": timezone.localdate().isoformat()}).status_code == 403

    def test_childrens_attendance_rights_do_not_open_staff_attendance(self, tenant_a):
        """
        Mijoz (2026-10-21): xodimlar davomati bolalar davomatiga emas, xodimlar
        bo'limiga tegishli. Bolalar davomatini yurituvchi rol (davomat
        menejeri, menejer) xodimlarnikini ko'rmaydi ham, belgilamaydi ham.
        """
        ali = _employee(tenant_a, "Aliyev")
        today = timezone.localdate()
        for role in ("attendance_manager", "manager"):
            client = _member(tenant_a, role, f"{role}@alfa.uz")
            assert client.get(DAILY, {"date": today.isoformat()}).status_code == 403
            assert client.get(TIMESHEET, {"month": today.strftime("%Y-%m")}).status_code == 403
            assert _mark(client, today, (ali, "present")).status_code == 403

    def test_a_payroll_holder_marks_staff(self, tenant_a):
        ali = _employee(tenant_a, "Aliyev")
        client = _member(tenant_a, "director", "direktor@alfa.uz")
        assert _mark(client, timezone.localdate(), (ali, "present")).status_code == 200

    def test_branch_bound_user_sees_and_marks_only_her_branch(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            gorkiy = Branch.objects.create(
                organization=tenant_a.organization, name="Gorkiy", code="SECOND"
            )
        mine = _employee(tenant_a, "Meniki")
        other = _employee(tenant_a, "Begona", branch=gorkiy)
        client = _member(tenant_a, "director", "direktor@alfa.uz")
        today = timezone.localdate()

        rows = client.get(DAILY, {"date": today.isoformat(), "branch": str(gorkiy.id)}).json()
        assert [r["employee_id"] for r in rows["data"]["rows"]] == [str(mine.id)]
        assert _mark(client, today, (other, "present"), branch=gorkiy).status_code == 404

        # Ega esa ikkala filialni ko'radi.
        owner_rows = tenant_a.client().get(DAILY, {"date": today.isoformat()}).json()
        assert len(owner_rows["data"]["rows"]) == 2

    def test_cross_tenant_employee_is_404_and_nothing_is_written(self, tenant_a, tenant_b):
        foreign = _employee(tenant_b, "Begona")
        response = _mark(tenant_a.client(), timezone.localdate(), (foreign, "present"))
        assert response.status_code == 404
        with organization_context(tenant_b.organization.id):
            assert not StaffAttendance.objects.filter(employee=foreign).exists()

    def test_suspended_subscription_blocks_writes_not_reads(self, tenant_a):
        ali = _employee(tenant_a, "Aliyev")
        with organization_context(tenant_a.organization.id):
            Subscription.objects.filter(organization=tenant_a.organization).update(
                status=SubscriptionStatus.SUSPENDED
            )
        client = tenant_a.client()
        assert _mark(client, timezone.localdate(), (ali, "present")).status_code == 402
        assert client.get(TIMESHEET).status_code == 200


class TestExport:
    def test_timesheet_exports_to_excel_with_day_codes(self, tenant_a):
        from openpyxl import load_workbook

        ali = _employee(tenant_a, "Aliyev")
        client = tenant_a.client()
        _mark(client, date(2026, 3, 2), (ali, "present"))
        _mark(client, date(2026, 3, 3), (ali, "sick"))

        job = client.post(
            "/api/v1/reports/staff-attendance/export",
            {"params": {"year": 2026, "month": 3}},
            format="json",
        )
        assert job.status_code == 202, job.json()
        generate_export(job.json()["data"]["id"], str(tenant_a.organization.id))

        with organization_context(tenant_a.organization.id):
            export = ReportExport.objects.get(pk=job.json()["data"]["id"])
            assert export.status == ExportStatus.READY
            sheet = load_workbook(io.BytesIO(export.file.read())).active
        headers = [cell.value for cell in sheet[1]]
        assert headers[:4] == ["Xodim", "Lavozim", "Filial", "1"]
        row = {headers[i]: cell.value for i, cell in enumerate(sheet[2])}
        assert row["2"] == "K" and row["3"] == "B"
        assert row["Keldi"] == 1 and row["Kasal"] == 1

    def test_branch_bound_export_is_forced_to_own_branch(self, tenant_a):
        client = _member(tenant_a, "manager", "menejer@alfa.uz")
        from apps.accounts.models import Permission, RolePermission

        with organization_context(tenant_a.organization.id):
            role = tenant_a.role("manager")
            for code in ("reports.export", "payroll.read"):
                RolePermission.objects.get_or_create(
                    role=role, permission=Permission.objects.get(code=code)
                )
            other = Branch.objects.create(
                organization=tenant_a.organization, name="Gorkiy", code="SECOND"
            )
        job = client.post(
            "/api/v1/reports/staff-attendance/export",
            {"params": {"branch_id": str(other.id)}},
            format="json",
        )
        assert job.status_code == 202, job.json()
        with organization_context(tenant_a.organization.id):
            params = ReportExport.objects.get(pk=job.json()["data"]["id"]).params
        assert params["branch_id"] == str(tenant_a.branch.id)
