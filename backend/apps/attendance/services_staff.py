"""
Xodimlar davomati va oylik tabel (docs/04 §8.3, 2026-10).

Uch amal: kunlik jurnal, bir kunni bitta chaqiruvda belgilash va oylik
tabel. Tabel — buxgalter oy oxirida ochadigan narsa: har bir xodimning
har bir kuni, jami va o'sha xodim uchun shu oydagi ish kunlari.

Filial doirasi ROLGA bog'liq (docs/02 §11.3): ega barcha filiallarni
(yoki tanlaganini), qolganlar faqat o'z filialini ko'radi va belgilaydi.

Maosh bu yerda o'zgartirilmaydi. Tabel — fakt; kasallik yoki
sababsiz kelmaslik oylikka qanday ta'sir qilishi buxgalterning qarori.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext
from rest_framework.exceptions import NotFound

from apps.attendance.models_staff import StaffAttendance, StaffAttendanceStatus
from apps.attendance.services_absence import _holidays, working_weekdays
from apps.core.exceptions import BusinessRuleViolation
from apps.hr.models import Employee, EmploymentStatus

__all__ = [
    "scope_branch_id",
    "daily_register",
    "mark_bulk",
    "monthly_timesheet",
    "timesheet_rows",
]


def scope_branch_id(user: Any, requested: Any = None) -> Any:
    """
    Qaysi filial ko'rinadi: ega — so'raganini (yoki hammasini, `None`),
    filialga bog'langan xodim — faqat o'zinikini (so'rov e'tiborsiz).
    """
    if getattr(user, "is_org_owner", False):
        return requested or None
    return user.branch_id


def _employees(branch_id: Any) -> QuerySet[Employee]:
    queryset = Employee.objects.select_related("position", "branch")
    if branch_id:
        queryset = queryset.filter(branch_id=branch_id)
    return queryset.order_by("last_name", "first_name")


def _employed_between(queryset: QuerySet[Employee], start: date, end: date) -> QuerySet[Employee]:
    """
    `[start, end]` oralig'ida kamida bir kun ishlagan xodimlar.

    Bo'shagan xodim ham kiradi — agar bo'shash sanasi oraliqqa tushsa:
    oy o'rtasida ketgan odamning tabeli o'sha oy uchun to'liq bo'lishi
    kerak. O'chirilgan (bo'shash sanasi yo'q, faol emas) xodim kirmaydi.
    """
    return queryset.filter(hire_date__lte=end).filter(
        Q(termination_date__isnull=True, is_active=True) | Q(termination_date__gte=start)
    )


def _working_dates(
    *, organization_id: Any, start: date, end: date, branch: Any = None
) -> list[date]:
    """Oraliqdagi ish kunlari — bog'cha hafta kunlari sozlamasi va bayramlar."""
    if start > end:
        return []
    weekdays = working_weekdays(branch)
    closed = _holidays(organization_id, start, end)
    days: list[date] = []
    cursor = start
    while cursor <= end:
        if cursor.isoweekday() in weekdays and cursor not in closed:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def daily_register(*, branch_id: Any, attendance_date: date) -> list[dict[str, Any]]:
    """
    Bir kunlik jurnal — o'sha kuni ishlagan HAR BIR xodim.

    Belgilanmagan xodim `status: None` bilan keladi: "kim qoldi?" degan
    savol javobsiz qolmasin (bolalar jurnali bilan bir xil qoida).
    """
    employees = list(_employed_between(_employees(branch_id), attendance_date, attendance_date))
    records = {
        record.employee_id: record
        for record in StaffAttendance.objects.filter(
            employee_id__in=[e.id for e in employees], attendance_date=attendance_date
        )
    }
    rows = []
    for employee in employees:
        record = records.get(employee.id)
        rows.append(
            {
                "employee_id": str(employee.id),
                "full_name": employee.full_name,
                "position": employee.position.title if employee.position else None,
                "branch": employee.branch.name,
                # Ta'tildagi xodim uchun UI "Ta'tilda" ni oldindan taklif qiladi.
                "on_leave": employee.employment_status == EmploymentStatus.ON_LEAVE,
                "status": record.status if record else None,
                "note": record.note if record else "",
            }
        )
    return rows


@transaction.atomic
def mark_bulk(
    *,
    organization: Any,
    branch_id: Any,
    attendance_date: date,
    records: list[dict[str, Any]],
    recorded_by: Any = None,
) -> int:
    """
    Bir kunni bitta chaqiruvda belgilaydi (upsert).

    Faqat o'sha kuni ishlagan va foydalanuvchi ko'ra oladigan filialdagi
    xodimni belgilash mumkin. Ko'rinmaydigan xodim — `404` (begona
    tashkilot yoki boshqa filial): uning borligini ham aytmaymiz.
    """
    if attendance_date > timezone.localdate():
        raise BusinessRuleViolation(gettext("Kelajakdagi kunga davomat belgilab bo'lmaydi."))

    visible = {e.id: e for e in _employees(branch_id)}
    employed = {
        e.id for e in _employed_between(_employees(branch_id), attendance_date, attendance_date)
    }
    valid = set(StaffAttendanceStatus.values)

    saved = 0
    for row in records:
        employee = visible.get(row["employee_id"])
        if employee is None:
            raise NotFound(gettext("Xodim topilmadi."))
        if employee.id not in employed:
            raise BusinessRuleViolation(
                gettext(
                    "{full_name} {date} kuni ishlamagan (ishga kirish/bo'shash sanasi)."
                ).format(full_name=employee.full_name, date=attendance_date.isoformat())
            )
        status = row["status"]
        if status not in valid:
            raise BusinessRuleViolation(gettext("Noma'lum holat: {status}").format(status=status))
        StaffAttendance.objects.update_or_create(
            employee=employee,
            attendance_date=attendance_date,
            defaults={
                "organization": organization,
                "branch": employee.branch,
                "status": status,
                "note": (row.get("note") or "")[:255],
                "recorded_by": recorded_by,
            },
        )
        saved += 1
    return saved


# Tabel kataklari uchun qisqa belgilar — qog'oz tabeldagi kabi.
def _codes() -> dict[str, str]:
    return {
        StaffAttendanceStatus.PRESENT: gettext("K"),
        StaffAttendanceStatus.ABSENT: gettext("Y"),
        StaffAttendanceStatus.SICK: gettext("B"),
        StaffAttendanceStatus.LEAVE: gettext("T"),
    }


def monthly_timesheet(
    *, organization_id: Any, branch_id: Any, year: int, month: int
) -> dict[str, Any]:
    """
    Oylik tabel: xodim × kun, jami va xodimning shu oydagi ish kunlari.

    Ish kunlari HAR BIR xodim uchun alohida: oy o'rtasida ishga kirgan
    yoki ketgan xodimning "rejadagi" kunlari kamroq. `unmarked` — bugungi
    kungacha bo'lgan, lekin hali belgilanmagan ish kunlari: oy oxirida
    tabelni yopishdan oldin nima qolganini ko'rsatadi.
    """
    if not 1 <= month <= 12:
        raise BusinessRuleViolation(gettext("Oy 1–12 oralig'ida bo'lishi kerak."))
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    today = timezone.localdate()

    employees = list(_employed_between(_employees(branch_id), first, last))
    records: dict[Any, dict[date, StaffAttendance]] = {}
    for record in StaffAttendance.objects.filter(
        employee_id__in=[e.id for e in employees],
        attendance_date__gte=first,
        attendance_date__lte=last,
    ):
        records.setdefault(record.employee_id, {})[record.attendance_date] = record

    rows = []
    totals = dict.fromkeys(StaffAttendanceStatus.values, 0)
    for employee in employees:
        start = max(first, employee.hire_date)
        end = min(last, employee.termination_date or last)
        working = _working_dates(
            organization_id=organization_id, start=start, end=end, branch=employee.branch
        )
        marks = records.get(employee.id, {})
        counts = dict.fromkeys(StaffAttendanceStatus.values, 0)
        for record in marks.values():
            counts[record.status] += 1
            totals[record.status] += 1
        unmarked = sum(1 for day in working if day <= today and day not in marks)
        rows.append(
            {
                "employee_id": str(employee.id),
                "full_name": employee.full_name,
                "position": employee.position.title if employee.position else None,
                "branch": employee.branch.name,
                "days": {str(day.day): record.status for day, record in sorted(marks.items())},
                "working_days": len(working),
                "unmarked": unmarked,
                **counts,
            }
        )

    calendar_branch = employees[0].branch if branch_id and employees else None
    return {
        "year": year,
        "month": month,
        "days_in_month": last.day,
        # Sarlavhadagi dam olish kunlari uchun: tashkilot (yoki filial) kalendari.
        "working_dates": [
            day.isoformat()
            for day in _working_dates(
                organization_id=organization_id, start=first, end=last, branch=calendar_branch
            )
        ],
        "employees": rows,
        "totals": totals,
    }


def timesheet_rows(
    *, organization_id: Any, branch_id: Any, year: int, month: int, **_: Any
) -> list[dict[str, Any]]:
    """Excel eksport qatorlari: xodim, lavozim, 1…31 kun belgisi, jami."""
    sheet = monthly_timesheet(
        organization_id=organization_id, branch_id=branch_id, year=year, month=month
    )
    codes = _codes()
    rows = []
    for employee in sheet["employees"]:
        row: dict[str, Any] = {
            "employee": employee["full_name"],
            "position": employee["position"] or "",
            "branch": employee["branch"],
        }
        for day in range(1, 32):
            status = employee["days"].get(str(day))
            row[f"d{day}"] = codes.get(status, "") if status else ""
        row.update(
            {
                "present": employee["present"],
                "absent": employee["absent"],
                "sick": employee["sick"],
                "leave": employee["leave"],
                "working_days": employee["working_days"],
            }
        )
        rows.append(row)
    return rows
