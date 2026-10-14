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
from apps.finance.balance import child_balance
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


def test_an_unpaid_month_is_reduced_straight_away(tenant_a: Any):
    """
    Egasining qoidasi (PLAN 7.7): ota-ona bu oy uchun hali to'lamagan
    bo'lsa, qayta hisob SHU OYNING summasidan ayriladi — keyingi oyni
    kutmaydi.

    Hujjat o'zgaradi (minus qator va yangi summa), chunki ota-ona hali
    to'lamagan qog'ozdagi raqam bilan tizimdagi raqam bir xil bo'lishi
    kerak. Ledger esa qarshi KREDIT yozuvi bilan to'g'rilanadi — debet
    o'chirilmaydi (3-invariant).
    """
    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        september = finance.issue_invoice(child=child, period_year=2026, period_month=9)
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        absence.approve_claim(claim=claim)

        claim.refresh_from_db()
        september.refresh_from_db()

        assert claim.credit_amount == Decimal("500000.00")
        assert claim.status == ClaimStatus.APPLIED
        assert claim.applied_invoice_id == september.id
        assert september.amount_due == Decimal("1700000.00")
        assert any("Kelmagan kunlar" in line.description for line in september.lines.all())
        # Balans ham qog'oz bilan bir xil: 2 200 000 debet − 500 000 kredit.
        assert child_balance(child).balance == Decimal("1700000.00")


def test_a_paid_month_carries_the_credit_to_the_next_invoice(tenant_a: Any):
    """To'langan oydan pul ayirib bo'lmaydi — kredit keyingi oyga o'tadi."""
    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        september = finance.issue_invoice(child=child, period_year=2026, period_month=9)
        finance.record_payment(
            child=child, amount=september.amount_due, method="cash", invoice=september
        )

        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        absence.approve_claim(claim=claim)
        claim.refresh_from_db()
        september.refresh_from_db()

        # Sentabr tegilmaydi.
        assert september.amount_due == Decimal("2200000.00")
        assert claim.status == ClaimStatus.APPROVED

        october = finance.issue_invoice(child=child, period_year=2026, period_month=10)
        claim.refresh_from_db()
        charge = child.ledger_entries.filter(source_id=october.id).first()

        assert october.amount_due == Decimal("1700000.00")
        assert claim.status == ClaimStatus.APPLIED
        assert claim.applied_invoice_id == october.id
        assert charge.amount == Decimal("1700000.00")


def test_a_credit_bigger_than_what_is_left_waits_for_next_month(tenant_a: Any):
    """
    Qoldiqdan katta kredit BO'LINMAYDI.

    Qisman qo'llash da'voni ikkiga bo'lishni talab qilardi; bo'linmagan
    holda esa qoldiqdan ortig'i jimgina yo'qolardi.
    """
    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        september = finance.issue_invoice(child=child, period_year=2026, period_month=9)
        # Qoldiq 200 000 bo'lib qoladi, kredit esa 500 000 bo'ladi.
        finance.record_payment(
            child=child, amount=Decimal("2000000"), method="cash", invoice=september
        )
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        absence.approve_claim(claim=claim)

        claim.refresh_from_db()
        september.refresh_from_db()
        assert september.amount_due == Decimal("2200000.00")
        assert claim.status == ClaimStatus.APPROVED


def test_without_an_invoice_the_credit_simply_waits(tenant_a: Any):
    """Hali faktura chiqarilmagan oy — qo'llaydigan hujjat yo'q."""
    child = _child(tenant_a, "2200000")
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        absence.approve_claim(claim=claim)
        claim.refresh_from_db()
        assert claim.status == ClaimStatus.APPROVED


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


# --- Hujjatning o'zi (PLAN 7.7) ---


def _pdf(name: str = "spravka.pdf") -> Any:
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile(
        name, "%PDF-1.4 maʼlumotnoma".encode(), content_type="application/pdf"
    )


def test_a_claim_can_be_created_with_the_certificate_attached(tenant_a: Any):
    child = _child(tenant_a)
    client = tenant_a.client()
    response = client.post(
        "/api/v1/absence-claims",
        {
            "child_id": str(child.id),
            "kind": ClaimKind.MEDICAL,
            "date_from": "2026-09-07",
            "date_to": "2026-09-11",
            "document_no": "№ 12/3",
            "document_file": _pdf(),
        },
        format="multipart",
    )
    assert response.status_code == 201, response.content
    assert response.json()["data"]["has_document"] is True

    with organization_context(tenant_a.organization.id):
        claim = AbsenceClaim.objects.get(pk=response.json()["data"]["id"])
        # Nom UUID: yuklangan nom saqlansa, hujjat nomini taxmin qilish
        # yo'li ochilardi va bir xil nomlar to'qnashardi.
        assert "spravka" not in claim.document_file.name
        assert claim.document_file.name.startswith(f"{tenant_a.organization.id}/absence/")


def test_the_certificate_can_be_attached_later(tenant_a: Any):
    """Qog'oz ko'pincha keyinroq keladi."""
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))

    client = tenant_a.client()
    response = client.post(
        f"/api/v1/absence-claims/{claim.id}/document", {"file": _pdf()}, format="multipart"
    )
    assert response.status_code == 200, response.content
    assert response.json()["data"]["has_document"] is True

    download = client.get(f"/api/v1/absence-claims/{claim.id}/document/download")
    assert download.status_code == 200
    assert b"".join(download.streaming_content) == "%PDF-1.4 maʼlumotnoma".encode()


def test_a_decided_claim_keeps_the_document_it_was_approved_with(tenant_a: Any):
    """
    Tasdiqlangandan keyin hujjat almashmaydi: aks holda tasdiqlovchi
    bir narsani ko'rib imzolardi, papkada esa boshqasi turardi.
    """
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        absence.attach_document(claim=claim, uploaded=_pdf("birinchi.pdf"))
        absence.approve_claim(claim=claim)

    response = tenant_a.client().post(
        f"/api/v1/absence-claims/{claim.id}/document", {"file": _pdf()}, format="multipart"
    )
    assert response.status_code == 422, response.content


def test_an_executable_is_not_a_certificate(tenant_a: Any):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))

    from django.core.files.uploadedfile import SimpleUploadedFile

    response = tenant_a.client().post(
        f"/api/v1/absence-claims/{claim.id}/document",
        {"file": SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")},
        format="multipart",
    )
    assert response.status_code == 422, response.content


def test_another_organization_cannot_read_the_document(tenant_a: Any, tenant_b: Any):
    """
    Begona bolaning tibbiy maʼlumotnomasi — `404`, `403` emas.

    Fayl `/media/` havolasi orqali berilmaydi aynan shu sababdan:
    statik URL na kirishni, na tashkilot chegarasini biladi.
    """
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child, date(2026, 9, 7), date(2026, 9, 11))
        absence.attach_document(claim=claim, uploaded=_pdf())

    stranger = tenant_b.client()
    assert stranger.get(f"/api/v1/absence-claims/{claim.id}/document/download").status_code == 404
    assert (
        stranger.post(
            f"/api/v1/absence-claims/{claim.id}/document", {"file": _pdf()}, format="multipart"
        ).status_code
        == 404
    )
