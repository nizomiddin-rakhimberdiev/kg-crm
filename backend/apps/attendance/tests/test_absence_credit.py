"""
Kelmagan kunlar uchun qaytarish (ADR-19).

Eng muhim tekshiruv birinchi turadi: **oddiy kelmaslik pul
qaytarmaydi.** Agar hisob-kitob davomat jadvalidan o'qiganida, uxlab
qolgan bola ham chegirma olib ketardi va bog'chaning daromadi
o'z-o'zidan kamayardi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.attendance import services_absence as absence
from apps.attendance.models import AttendanceRecord, AttendanceStatus
from apps.attendance.models_absence import AbsenceClaim, ClaimKind, ClaimStatus, Holiday
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _child(tenant: Any, amount: str = "2200000") -> Child:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name="Toʻliq kun",
            amount=Decimal(amount),
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Laylo",
            last_name="Sharipova",
            date_of_birth=date(2021, 3, 14),
            gender="female",
            tariff=tariff,
        )


def _claim(tenant: Any, child: Child, start: date, end: date, kind: str = ClaimKind.MEDICAL):
    return absence.create_claim(
        child=child, kind=kind, date_from=start, date_to=end, document_no="№ 12/3"
    )


# --- Eng muhimi ---


def test_an_ordinary_absence_earns_nothing(tenant_a: Any):
    """
    Davomat jadvali va pul BIR-BIRIDAN O'QIMAYDI.

    Bola kelmadi deb belgilansa ham, hujjat bo'lmasa da'vo yo'q va
    hech qanday chegirma yaralmaydi.
    """
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        AttendanceRecord.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            child=child,
            attendance_date=date(2026, 9, 7),
            status=AttendanceStatus.ABSENT,
            reason="Uxlab qoldi",
        )
        assert AbsenceClaim.objects.filter(child=child).count() == 0

        invoice = finance.issue_invoice(child=child, period_year=2026, period_month=10)

    assert invoice.amount_due == Decimal("2200000.00")


# --- Ish kunlari ---


def test_weekends_and_holidays_do_not_count(tenant_a: Any):
    """
    Bog'cha yopiq bo'lgan kun — ota-ona sog'ingan kun emas.

    2026-yil 7–13 sentabr: dushanbadan yakshanbagacha. Ish kunlari
    beshta, ulardan 9-sentabr bayram deb belgilanadi → to'rtta qoladi.
    """
    with organization_context(tenant_a.organization.id):
        Holiday.objects.create(
            organization=tenant_a.organization,
            holiday_date=date(2026, 9, 9),
            name="Sinov bayrami",
        )
        days = absence.billable_days(
            organization_id=tenant_a.organization.id,
            date_from=date(2026, 9, 7),
            date_to=date(2026, 9, 13),
            branch=tenant_a.branch,
        )
    assert days == 4


def test_the_day_rate_divides_by_working_days_not_thirty(tenant_a: Any):
    """
    `tarif ÷ 30` ota-onaga u to'lamagan pulni qaytarib berardi.

    2026-yil sentabr: 22 ish kuni. 2 200 000 ÷ 22 = 100 000.
    """
    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        rate, days = absence.daily_rate_for(child=child, on_date=date(2026, 9, 10))

    assert days == 22
    assert rate == Decimal("100000.00")


def test_the_rate_follows_the_charged_amount_not_the_raw_tariff(tenant_a: Any):
    """
    Chegirmasi bor bolaga to'laganidan ko'p qaytmasligi kerak.

    Hisob-faktura chiqarilgan bo'lsa, manba — uning `amount_due` i.
    """
    from apps.finance.models import Discount, DiscountType

    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        Discount.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            child=child,
            discount_type=DiscountType.PERCENT,
            value=Decimal("50"),
            valid_from=date(2026, 1, 1),
        )
        invoice = finance.issue_invoice(child=child, period_year=2026, period_month=9)
        rate, _ = absence.daily_rate_for(child=child, on_date=date(2026, 9, 10))

    assert invoice.amount_due == Decimal("1100000.00")
    assert rate == Decimal("50000.00")


# --- Qaytarish yo'li ---


def test_an_approved_claim_becomes_a_minus_line_on_the_next_invoice(tenant_a: Any):
    """
    Ota-ona qo'lidagi qog'oz bilan balans bir xil raqamni ko'rsatadi,
    va o'tgan hujjat tahrirlanmaydi (D3).
    """
    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        finance.issue_invoice(child=child, period_year=2026, period_month=9)
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        absence.approve_claim(claim=claim)
        claim.refresh_from_db()

        assert claim.billable_days == 5
        assert claim.credit_amount == Decimal("500000.00")

        october = finance.issue_invoice(child=child, period_year=2026, period_month=10)
        claim.refresh_from_db()
        lines = list(october.lines.order_by("created_at"))
        # Ledger ham kamaygan summani oladi — balans qog'oz bilan mos.
        charge = child.ledger_entries.filter(source_id=october.id).first()

        assert october.amount_due == Decimal("1700000.00")
        assert claim.status == ClaimStatus.APPLIED
        assert claim.applied_invoice_id == october.id
        assert any("Kelmagan kunlar" in line.description for line in lines)
        assert charge.amount == Decimal("1700000.00")


def test_a_credit_is_applied_only_once(tenant_a: Any):
    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 8))
        absence.approve_claim(claim=claim)

        october = finance.issue_invoice(child=child, period_year=2026, period_month=10)
        november = finance.issue_invoice(child=child, period_year=2026, period_month=11)

    assert october.amount_due == Decimal("2000000.00")
    assert november.amount_due == Decimal("2200000.00")


def test_the_credit_never_makes_an_invoice_negative(tenant_a: Any):
    """Bogʻcha qarzdor boʻlib qolsa, u BALANSDA koʻrinadi, hujjatda emas."""
    child = _child(tenant_a, "500000")
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child, date(2026, 9, 1), date(2026, 9, 30))
        absence.approve_claim(claim=claim)
        october = finance.issue_invoice(child=child, period_year=2026, period_month=10)

    assert october.amount_due >= Decimal("0")


# --- Bazadagi kafolat ---


@pytest.mark.django_db(transaction=True)
def test_two_claims_cannot_cover_the_same_day(tenant_a: Any):
    """
    Kafolat servisda emas, BAZADA (`EXCLUDE USING gist`).

    Servis darajasidagi tekshiruv poygani yutqazadi; cheklov esa
    yutqazmaydi. Shuning uchun bu yerda servis chetlab o'tiladi.
    """
    from django.db import IntegrityError

    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        with pytest.raises(IntegrityError):
            AbsenceClaim.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                child=child,
                kind=ClaimKind.PARENTAL,
                date_from=date(2026, 9, 10),
                date_to=date(2026, 9, 14),
            )


def test_the_service_explains_an_overlap_before_the_database_refuses_it(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        with pytest.raises(BusinessRuleViolation):
            _claim(tenant_a, child, date(2026, 9, 10), date(2026, 9, 14))


def test_a_rejected_claim_frees_the_days(tenant_a: Any):
    """Rad etilgan daʼvo kunlarni band qilmaydi — cheklov uni chiqarib tashlaydi."""
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        first = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        absence.reject_claim(claim=first, note="Hujjat yaroqsiz")
        second = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))

    assert second.status == ClaimStatus.PENDING


def test_there_is_no_minimum_length(tenant_a: Any):
    """Egasining qarori: uch kun ham, oʻn besh kun ham qaytariladi."""
    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        short = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 7))
        absence.approve_claim(claim=short)
        short.refresh_from_db()

    assert short.billable_days == 1
    assert short.credit_amount == Decimal("100000.00")
