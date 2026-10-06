"""
Birinchi oy — egasining aniq misoli (PLAN 7.1, 2026-10-06).

"Oyning 25-sanasida kelgan bo'lsa va seshanba kuni bo'lsa va oy
30-sanada tugasa, undan 4 kunlik uchun pul hisoblanishi kerak."

2026-sentabr aynan shunday: 25-kun — juma... shuning uchun test
sanalarni O'ZI tekshiradi, taxmin qilmaydi.

Eng muhimi: `enrolled_on` BO'SH bo'lsa proporsional hisob umuman
ishlamaydi va to'liq oy yoziladi. Aynan shu productionda sodir bo'lgan
(Paddingtonda 21 boladan 21 tasi), chunki formada bu maydon yo'q edi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance.models import TariffPlan
from apps.finance.services import first_month_share, issue_invoice

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

PRICE = Decimal("3050000")


def _child(tenant, enrolled_on: date | None) -> Child:
    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name=f"Tarif {enrolled_on}",
            amount=PRICE,
        )
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 1, 1),
            gender="male",
            tariff=tariff,
            enrolled_on=enrolled_on,
        )


def test_a_child_arriving_late_pays_only_for_the_days_left(tenant_a):
    """Oyning oxirida kelgan bola — qolgan ish kunlari uchun, to'liq oy emas."""
    child = _child(tenant_a, date(2026, 9, 25))
    with organization_context(tenant_a.organization.id):
        share = first_month_share(child=child, period_year=2026, period_month=9)
        invoice = issue_invoice(child=child, period_year=2026, period_month=9)

    assert share is not None
    attended, total = share
    # Sentabr 25-30: 25, 28, 29, 30 ish kuni (26-27 — shanba/yakshanba).
    assert attended == 4, f"kutilgani 4 ish kuni, chiqqani {attended}"
    assert total == 22, f"2026-sentabrda 22 ish kuni, chiqqani {total}"

    # Egasining formulasi: 3 050 000 / 22 * 4 = 554 545,45 — va hisob
    # BUTUN so'mga yaxlitlanadi: bog'cha to'lovida tiyin ishlatilmaydi.
    expected = (PRICE / total * attended).quantize(Decimal("1"))
    assert invoice.amount_due == expected
    assert invoice.amount_due < PRICE
    assert str(invoice.amount_due) == "554545.00"


def test_a_child_arriving_on_the_first_pays_the_full_month(tenant_a):
    child = _child(tenant_a, date(2026, 9, 1))
    with organization_context(tenant_a.organization.id):
        invoice = issue_invoice(child=child, period_year=2026, period_month=9)
    assert invoice.amount_due == PRICE


def test_without_an_enrolment_date_the_full_month_is_charged(tenant_a):
    """
    Productiondagi xatoning o'zi: sana bo'sh — proporsional hisob yo'q.

    Bu test kodning xatosi emas, formaning xatosi edi. U shu yerda
    turadi, chunki keyinchalik kimdir `enrolled_on` ni ixtiyoriy
    qilib qo'ysa, narx jimgina to'liq oyga qaytardi.
    """
    child = _child(tenant_a, None)
    with organization_context(tenant_a.organization.id):
        assert first_month_share(child=child, period_year=2026, period_month=9) is None
        invoice = issue_invoice(child=child, period_year=2026, period_month=9)
    assert invoice.amount_due == PRICE
