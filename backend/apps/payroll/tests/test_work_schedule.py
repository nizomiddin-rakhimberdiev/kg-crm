"""
Ish grafigi oylikka qanday ta'sir qiladi (PLAN 9.1).

Grafik bezak emas: u xodimning pulidagi MAXRAJ. Haftada uch kun
keladigan tarbiyachi oy o'rtasida ishga kirsa, uning proporsiyasi
filialning 22 ish kunidan emas, o'zining 13 kunidan chiqishi kerak —
aks holda u ishlagan kunlari uchun kam oladi va buni payslipdan
tushuntirib bo'lmaydi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.attendance.models_staff import StaffAttendance, StaffAttendanceStatus
from apps.core.tenancy import organization_context
from apps.hr.models import Employee, WorkMode
from apps.payroll import services
from apps.payroll.models import PayrollItem

pytestmark = pytest.mark.django_db


def _employee(tenant, **kwargs) -> Employee:
    defaults = {
        "organization": tenant.organization,
        "branch": tenant.branch,
        "first_name": "Dilnoza",
        "last_name": "Rahimova",
        "hire_date": date(2024, 1, 1),
        "base_salary": Decimal("4400000.00"),
    }
    defaults.update(kwargs)
    return Employee.objects.create(**defaults)


def _run(tenant, year=2026, month=10):
    return services.create_run(
        organization=tenant.organization, branch=tenant.branch, period_year=year, period_month=month
    )


def test_a_three_day_week_is_prorated_by_its_own_days(tenant_a):
    """
    2026-oktabr: dushanba–juma 22 ish kuni; dushanba/chorshanba/juma esa
    13 kun (5 juma, 4 dushanba, 4 chorshanba).

    14-oktabr (chorshanba) ishga kirgan xodim shu kundan oy oxirigacha
    o'zining 8 kunini ishlaydi → 8/13. Filial kalendari bilan esa 13/22
    chiqardi — ya'ni ishlagan kunining ulushidan kamroq pul.
    """
    with organization_context(tenant_a.organization.id):
        employee = _employee(
            tenant_a,
            hire_date=date(2026, 10, 14),
            work_days="1,3,5",
            base_salary=Decimal("2600000"),
        )
        run = _run(tenant_a)
        item = PayrollItem.objects.get(payroll_run=run, employee=employee)
        assert item.base_amount == Decimal("1600000.00")  # 2 600 000 × 8/13


def test_a_full_month_is_not_prorated_at_all(tenant_a):
    with organization_context(tenant_a.organization.id):
        employee = _employee(tenant_a, work_days="1,3,5", base_salary=Decimal("2800000"))
        run = _run(tenant_a)
        item = PayrollItem.objects.get(payroll_run=run, employee=employee)
        assert item.base_amount == Decimal("2800000.00")


def test_an_hourly_employee_is_paid_for_the_days_in_the_timesheet(tenant_a):
    """Soatbay: kelgan kunlar × kunlik soat × soat narxi."""
    with organization_context(tenant_a.organization.id):
        employee = _employee(
            tenant_a,
            work_mode=WorkMode.HOURLY,
            base_salary=Decimal("0"),
            hours_per_day=Decimal("4"),
            hourly_rate=Decimal("35000"),
        )
        for day in (1, 2, 5, 6, 7):
            StaffAttendance.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                employee=employee,
                attendance_date=date(2026, 10, day),
                status=StaffAttendanceStatus.PRESENT,
            )
        # Kasal kun pul keltirmaydi.
        StaffAttendance.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            employee=employee,
            attendance_date=date(2026, 10, 8),
            status=StaffAttendanceStatus.SICK,
        )
        run = _run(tenant_a)
        item = PayrollItem.objects.get(payroll_run=run, employee=employee)
        assert item.base_amount == Decimal("700000.00")  # 5 × 4 × 35 000


def test_an_hourly_employee_without_a_timesheet_falls_back_to_the_schedule(tenant_a):
    """
    Tabel to'ldirilmagan bo'lsa — grafik bo'yicha.

    Nolga tushirish "texnik jihatdan to'g'ri" bo'lardi, lekin buxgalter
    uchun bu sabab ko'rsatilmagan nol: tabelni hech kim yuritmagan
    bog'chada har bir soatbay xodim oylikni ololmay qolardi.
    """
    with organization_context(tenant_a.organization.id):
        employee = _employee(
            tenant_a,
            work_mode=WorkMode.HOURLY,
            base_salary=Decimal("0"),
            work_days="2,4",
            hours_per_day=Decimal("3"),
            hourly_rate=Decimal("40000"),
        )
        run = _run(tenant_a)
        item = PayrollItem.objects.get(payroll_run=run, employee=employee)
        # 2026-oktabrda seshanba va payshanba — 9 kun.
        assert item.base_amount == Decimal("1080000.00")  # 9 × 3 × 40 000
