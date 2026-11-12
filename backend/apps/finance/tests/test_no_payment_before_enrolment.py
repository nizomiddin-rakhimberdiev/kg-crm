"""
Qabul sanasidan oldingi to'lov yozilmaydi (audit 2026-11-12, A6).

Bola 20.06 da kelgan bo'lsa, 05.06 sanali to'lov — kiritishdagi xato:
u bolaning kartasida "kelmasdan oldin to'lagan" degan yolg'on tarix va
o'sha oyning kassasida mavjud bo'lmagan tushum qoldiradi.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import Payment

pytestmark = pytest.mark.django_db


def _child(tenant_a, enrolled_on):
    with organization_context(tenant_a.organization.id):
        return Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Kamola",
            last_name="Rahimova",
            date_of_birth=date(2021, 2, 1),
            gender="female",
            enrolled_on=enrolled_on,
        )


def _at(day: date):
    return timezone.make_aware(datetime.combine(day, time(10, 0)))


def test_a_payment_dated_before_enrolment_is_refused(tenant_a):
    child = _child(tenant_a, date(2026, 6, 20))
    with organization_context(tenant_a.organization.id):
        with pytest.raises(BusinessRuleViolation, match="20.06.2026"):
            finance.record_payment(
                child=child,
                amount=Decimal("500000"),
                method="cash",
                received_by=tenant_a.owner,
                paid_at=_at(date(2026, 6, 5)),
                backdate_reason="Qogʻozdagi kvitansiya",
            )
        assert not Payment.objects.filter(child=child).exists()


def test_a_payment_on_the_enrolment_day_is_fine(tenant_a):
    child = _child(tenant_a, date(2026, 6, 20))
    with organization_context(tenant_a.organization.id):
        finance.record_payment(
            child=child,
            amount=Decimal("500000"),
            method="cash",
            received_by=tenant_a.owner,
            paid_at=_at(date(2026, 6, 20)),
            backdate_reason="Qogʻozdagi kvitansiya",
        )
        assert Payment.objects.filter(child=child).count() == 1
