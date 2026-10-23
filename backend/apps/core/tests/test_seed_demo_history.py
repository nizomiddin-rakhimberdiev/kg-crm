"""
Demo tarixi haqiqiy bogʻchaga oʻxshashi kerak (mijoz soʻrovi, 2026-10-23).

Mijoz "taxminiy narsalar yozma, aniq va toza boʻlsin" dedi, va buning
oʻlchovi bitta: **ma'lumot oʻz ichida ziddiyatsiz boʻlsin**. Bu test
aynan ziddiyatlarni qidiradi — bogʻcha ochilishidan oldin yozilgan
bola, toʻldirilmagan majburiy maydon, yopilmagan oy, boʻsh tabel.

Buyruqning oʻzi ham tekshiruv: oy faqat tenglik "yashil" boʻlsa
yopiladi, ya'ni yopilgan oylar soni — seed raqamlari bir-biriga mos
kelganining DALILI.
"""

from __future__ import annotations

from datetime import date
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

MONTHS = 3
CHILDREN = 12


def _month_start(value: date, back: int = 0) -> date:
    total = value.year * 12 + (value.month - 1) - back
    return date(total // 12, total % 12 + 1, 1)


@pytest.fixture
def seeded(tenant_a: Any) -> Any:
    out = StringIO()
    call_command(
        "seed_demo",
        "--slug",
        tenant_a.organization.slug,
        "--children",
        str(CHILDREN),
        "--months",
        str(MONTHS),
        stdout=out,
    )
    return tenant_a


def test_nobody_arrives_before_the_kindergarten_opens(seeded: Any):
    from apps.children.models import Child
    from apps.hr.models import Employee

    opening = _month_start(timezone.localdate(), MONTHS - 1)
    with organization_context(seeded.organization.id):
        early = [
            child.full_name
            for child in Child.objects.all()
            if child.enrolled_on and child.enrolled_on < opening
        ]
        hired_early = [
            employee.full_name
            for employee in Employee.objects.all()
            if employee.hire_date and employee.hire_date < opening
        ]
    assert early == []
    assert hired_early == []


def test_every_child_carries_what_a_real_one_would(seeded: Any):
    """Qayerdan eshitgan va shartnoma raqami — ikkalasi ham toʻla."""
    from apps.children.models import Child

    with organization_context(seeded.organization.id):
        rows = list(Child.objects.all())
        assert len(rows) == CHILDREN
        assert all(child.heard_from for child in rows)
        assert all(child.contract_number for child in rows)
        # Manba bitta qiymatga yopishib qolmagan.
        assert len({child.heard_from for child in rows}) >= 3


def test_the_finished_months_are_closed(seeded: Any):
    """
    Oy faqat tenglik toʻgʻri boʻlsa yopiladi — ya'ni yopilgan oylar
    soni seed raqamlarining mosligini isbotlaydi.
    """
    from apps.finance.models import MonthClose

    with organization_context(seeded.organization.id):
        assert MonthClose.objects.count() == MONTHS - 1


def test_the_staff_timesheet_is_not_empty(seeded: Any):
    from apps.attendance.models_staff import StaffAttendance

    with organization_context(seeded.organization.id):
        assert StaffAttendance.objects.count() > 0
        # Bolalar davomati bilan bir xil oynada.
        oldest = StaffAttendance.objects.order_by("attendance_date").first()
        assert oldest is not None
        assert oldest.attendance_date >= _month_start(timezone.localdate(), MONTHS - 1)


def test_recalculation_and_benefits_exist(seeded: Any):
    """Ikkalasi ham hujjatdan keladi — ekranda boʻsh tab qolmasin."""
    from apps.attendance.models_absence import AbsenceClaim
    from apps.finance.models import Discount

    with organization_context(seeded.organization.id):
        assert AbsenceClaim.objects.filter(status="approved").exists()
        assert Discount.objects.exists()


def test_the_money_adds_up_in_every_month(seeded: Any):
    """
    Hisoblangan = yigʻilgan + qarz — har bir oyda.

    Bu demo "chiroyli, lekin mumkin boʻlmagan" holatga tushmaganining
    oʻlchovi: raqamlar bir-biridan kelib chiqadi.
    """
    from apps.finance.selectors import monthly_summary

    today = timezone.localdate()
    with organization_context(seeded.organization.id):
        for back in range(MONTHS):
            period = _month_start(today, back)
            summary = monthly_summary(
                organization_id=seeded.organization.id,
                year=period.year,
                month=period.month,
            )
            assert summary["check"]["ok"], f"{period}: {summary['check']['equation']}"


def test_the_cash_balance_is_never_negative(seeded: Any):
    """
    Manfiy qop bogʻcha haqida fakt aytmaydi — u yozuv yetishmayotganini
    aytadi (ADR-29). Demoda bunday holat boʻlmasligi kerak.
    """
    from apps.cash.selectors import account_balances

    with organization_context(seeded.organization.id):
        rows = account_balances(organization_id=seeded.organization.id)
        negative = [row for row in rows if float(row["balance"]) < 0]
    assert negative == []


def test_reset_clears_a_full_history_and_keeps_the_tenant(seeded: Any):
    """
    `--reset` toʻliq tarixni ham tozalashi kerak — ADR-20 taqsimoti,
    qaytarish, oy yopilishi, kassa sanogʻi bilan birga.

    Avval `_reset` oʻzining qisqa roʻyxatini yuritardi va u asta-sekin
    orqada qoldi: `payment_allocation` roʻyxatda yoʻq edi, va jonli
    bazada bitta taqsimot butun tozalashni `RestrictedError` bilan
    yiqitdi. Endi tartib `purge.py` dagi YAGONA roʻyxatdan olinadi,
    shuning uchun yangi jadval oʻz-oʻzidan qamrab olinadi.
    """
    from apps.accounts.models import User
    from apps.branches.models import Branch
    from apps.children.models import Child
    from apps.finance.models import PaymentAllocation

    organization = seeded.organization
    with organization_context(organization.id):
        assert PaymentAllocation.objects.exists(), "demo taqsimotsiz — test maʼnosiz"

    call_command(
        "seed_demo",
        "--slug",
        organization.slug,
        "--children",
        "1",
        "--months",
        "1",
        "--reset",
        stdout=StringIO(),
    )

    with organization_context(organization.id):
        # Tashkilot, egasi va filial QOLADI — tozalash faqat operatsion.
        assert Branch.objects.filter(organization_id=organization.id).exists()
        assert User.objects.filter(organization_id=organization.id).exists()
        assert Child.objects.count() == 1
