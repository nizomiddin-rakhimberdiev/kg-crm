"""
Maʼlumotnoma chegirmasi (audit, 2026-10-30).

Uchta kamchilik, uchalasi ham bitta oqimda:

* **Preview chegirmani koʻrsatmaydi.** Summa `plan_month()` dan
  olinardi, tasdiqlangan daʼvolar esa faqat `issue_invoice` ichida
  qoʻllanardi — yaʼni mudira tasdiqlashdan oldin 1 500 000 koʻrib,
  keyin 1 425 000 olardi. Preview va ish bir xil raqamni aytishi
  kerak, aks holda tasdiqlashning maʼnosi yoʻq.
* **Hujjat talab qiladigan tur hujjatsiz tasdiqlanardi.** Tibbiy
  maʼlumotnoma — pulni qaytarish asosi; uning oʻzi boʻlmasa,
  qaytarishga asos ham yoʻq.
* **Tasdiqlangan daʼvoni bekor qilib boʻlmasdi** — xato tasdiq
  abadiy qolardi.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from apps.attendance import services_absence as absence
from apps.attendance.models_absence import AbsenceClaim, ClaimStatus
from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan

pytestmark = pytest.mark.django_db


def _child(tenant_a: Any) -> Child:
    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            name="Toʻliq kun",
            amount=Decimal("1500000"),
        )
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Nigora",
            last_name="Rahimova",
            date_of_birth=date(2021, 5, 4),
            gender="female",
            tariff=tariff,
            enrolled_on=date(2026, 1, 5),
        )


def _claim(tenant_a: Any, child: Child, *, days: int = 2, kind: str = "parental") -> AbsenceClaim:
    """Oʻtgan oyda yotgan, tasdiqlangan daʼvo."""
    today = timezone.localdate()
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=10)
    while start.weekday() >= 5:
        start += timedelta(days=1)
    claim = absence.create_claim(
        child=child,
        kind=kind,
        date_from=start,
        date_to=start + timedelta(days=days - 1),
        note="Ota-ona arizasi",
        # Ariza ham hujjat — raqami bilan (ADR-51).
        document_no="A-17",
    )
    return absence.approve_claim(claim=claim)


def test_the_preview_shows_the_credit(tenant_a):
    child = _child(tenant_a)
    today = timezone.localdate()
    nxt = (today.replace(day=28) + timedelta(days=7)).replace(day=1)

    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child)
        assert claim.credit_amount > 0

        preview = finance.preview_monthly_invoices(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=nxt.year,
            period_month=nxt.month,
        )

    row = next(r for r in preview.rows if r.full_name == child.full_name)
    assert row.amount == Decimal("1500000") - claim.credit_amount


def test_the_credit_is_not_counted_twice(tenant_a):
    child = _child(tenant_a)
    today = timezone.localdate()
    nxt = (today.replace(day=28) + timedelta(days=7)).replace(day=1)

    with organization_context(tenant_a.organization.id):
        _claim(tenant_a, child)
        finance.issue_invoice(child=child, period_year=nxt.year, period_month=nxt.month)
        # Daʼvo qoʻllandi — ikkinchi preview uni yana ayirmasligi kerak.
        again = finance.preview_monthly_invoices(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            period_year=nxt.year,
            period_month=nxt.month,
        )
    assert all(r.full_name != child.full_name for r in again.rows)


def test_a_medical_claim_without_a_document_is_refused(tenant_a):
    child = _child(tenant_a)
    today = timezone.localdate()
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=10)
    while start.weekday() >= 5:
        start += timedelta(days=1)

    with organization_context(tenant_a.organization.id):
        claim = absence.create_claim(
            child=child,
            kind="medical",
            date_from=start,
            date_to=start + timedelta(days=1),
            note="Shifokor maʼlumotnomasi",
        )
        with pytest.raises(BusinessRuleViolation):
            absence.approve_claim(claim=claim)


def test_a_document_number_is_enough(tenant_a):
    """Qogʻoz maʼlumotnoma raqami ham hujjat — skaner har doim ham yoʻq."""
    child = _child(tenant_a)
    today = timezone.localdate()
    start = (today.replace(day=1) - timedelta(days=1)).replace(day=10)
    while start.weekday() >= 5:
        start += timedelta(days=1)

    with organization_context(tenant_a.organization.id):
        claim = absence.create_claim(
            child=child,
            kind="medical",
            date_from=start,
            date_to=start + timedelta(days=1),
            document_no="M-4821",
            note="Shifokor maʼlumotnomasi",
        )
        approved = absence.approve_claim(claim=claim)
    assert approved.status == ClaimStatus.APPROVED


def test_an_approved_claim_can_be_cancelled_with_a_reason(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child)
        cancelled = absence.cancel_claim(claim=claim, reason="Xato tasdiqlangan")
        assert cancelled.status == ClaimStatus.REJECTED
        assert "Xato tasdiqlangan" in cancelled.decision_note


def test_cancelling_without_a_reason_is_refused(tenant_a):
    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child)
        with pytest.raises(BusinessRuleViolation):
            absence.cancel_claim(claim=claim, reason="")


def test_a_claim_already_on_an_invoice_is_not_cancelled_here(tenant_a):
    """Fakturaga tushgan daʼvo — pul harakati; u tuzatish qatori bilan qaytadi."""
    child = _child(tenant_a)
    today = timezone.localdate()
    nxt = (today.replace(day=28) + timedelta(days=7)).replace(day=1)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child)
        finance.issue_invoice(child=child, period_year=nxt.year, period_month=nxt.month)
        claim.refresh_from_db()
        assert claim.status == ClaimStatus.APPLIED
        with pytest.raises(BusinessRuleViolation):
            absence.cancel_claim(claim=claim, reason="Xato tasdiqlangan")


def test_the_cancel_endpoint_needs_the_approve_permission(tenant_a):
    from django.urls import reverse

    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child)

    response = tenant_a.client().post(
        reverse("v1:absence-claim-cancel", args=[claim.id]),
        {"reason": "Xato tasdiqlangan"},
        format="json",
    )
    assert response.status_code == 200, response.data
    assert response.json()["data"]["status"] == "rejected"


def test_another_tenant_cannot_cancel_the_claim(tenant_a, tenant_b):
    from django.urls import reverse

    child = _child(tenant_a)
    with organization_context(tenant_a.organization.id):
        claim = _claim(tenant_a, child)

    response = tenant_b.client().post(
        reverse("v1:absence-claim-cancel", args=[claim.id]),
        {"reason": "Begona daʼvo"},
        format="json",
    )
    assert response.status_code == 404
