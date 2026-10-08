"""
Xodimlar: hisob bogʻlash va ish grafigi (PLAN 9.1).
"""

from __future__ import annotations

import pytest

from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db


class TestAccountLinking:
    """
    Hisob bogʻlash endi foydalanuvchi tomonidan (PLAN 9.1b).

    Ish tartibi shunday: avval odam ishga olinadi, kirish huquqi esa
    keyin — va hamma xodimga ham kerak emas.
    """

    def test_employee_form_no_longer_takes_a_user(self, tenant_a):
        from apps.hr.serializers import EmployeeWriteSerializer

        assert "user_id" not in EmployeeWriteSerializer().fields

    def test_creating_a_user_links_the_chosen_employee(self, tenant_a):
        from datetime import date as _date

        from apps.hr.models import Employee

        client = tenant_a.client()
        with organization_context(tenant_a.organization.id):
            employee = Employee.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Nodira",
                last_name="Ergasheva",
                hire_date=_date(2026, 1, 10),
            )
            role = tenant_a.role("director")

        response = client.post(
            "/api/v1/users",
            {
                "full_name": "Nodira Ergasheva",
                "email": "nodira@alfa.uz",
                "password": "Juda-Kuchli-Parol-2026",
                "role_id": str(role.id),
                "branch_id": str(tenant_a.branch.id),
                "employee_id": str(employee.id),
            },
            format="json",
        )
        assert response.status_code == 201, response.content
        with organization_context(tenant_a.organization.id):
            employee.refresh_from_db()
            assert employee.user is not None
            assert employee.user.email == "nodira@alfa.uz"

    def test_an_employee_cannot_be_linked_to_two_accounts(self, tenant_a):
        from datetime import date as _date

        from apps.accounts.models import User
        from apps.hr.models import Employee

        client = tenant_a.client()
        with organization_context(tenant_a.organization.id):
            taken = User.objects.create_user(
                email="band@alfa.uz",
                password="Juda-Kuchli-Parol-2026",
                full_name="Band",
                organization=tenant_a.organization,
                role=tenant_a.role("director"),
                branch=tenant_a.branch,
            )
            employee = Employee.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Shahzod",
                last_name="Qodirov",
                hire_date=_date(2026, 1, 10),
                user=taken,
            )
            role = tenant_a.role("director")

        response = client.post(
            "/api/v1/users",
            {
                "full_name": "Ikkinchi",
                "email": "ikkinchi@alfa.uz",
                "password": "Juda-Kuchli-Parol-2026",
                "role_id": str(role.id),
                "branch_id": str(tenant_a.branch.id),
                "employee_id": str(employee.id),
            },
            format="json",
        )
        assert response.status_code == 400, response.content


class TestWorkSchedule:
    def test_hourly_employee_needs_a_rate(self, tenant_a):
        from apps.hr.serializers import EmployeeWriteSerializer

        serializer = EmployeeWriteSerializer(
            data={
                "first_name": "Soat",
                "last_name": "Bay",
                "hire_date": "2026-10-01",
                "work_mode": "hourly",
                "base_salary": "0",
            }
        )
        assert not serializer.is_valid()
        assert "hourly_rate" in serializer.errors

    def test_work_days_are_normalised(self, tenant_a):
        from apps.hr.serializers import EmployeeWriteSerializer

        serializer = EmployeeWriteSerializer(
            data={
                "first_name": "Uch",
                "last_name": "Kunlik",
                "hire_date": "2026-10-01",
                "work_days": "5, 1 ,3,3",
                "base_salary": "1000000",
            }
        )
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["work_days"] == "1,3,5"

    def test_a_bad_weekday_is_refused(self, tenant_a):
        from apps.hr.serializers import EmployeeWriteSerializer

        serializer = EmployeeWriteSerializer(
            data={
                "first_name": "Xato",
                "last_name": "Kun",
                "hire_date": "2026-10-01",
                "work_days": "0,9",
                "base_salary": "1000000",
            }
        )
        assert not serializer.is_valid()
        assert "work_days" in serializer.errors
