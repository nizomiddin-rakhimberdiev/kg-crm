"""
Demo tashkilotning obunasi (audit 2026-11-12, D2).

`analiz` demo stendida obuna yo'q edi (sinovi tugab bekor bo'lgan), va
"Obuna va to'lov" sahifasi to'rtta 422 bilan bo'sh qobiq bo'lib
ochilardi. Demo — bepul, lekin ishlayotgan obuna: 100 % chegirma bilan
faol. Nol so'mlik hisob esa hech qachon "muddati o'tgan" bo'lmaydi —
aks holda demo 15 kundan keyin yozishdan to'xtardi.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.core.tenancy import organization_context
from apps.subscriptions import services
from apps.subscriptions.models import (
    Subscription,
    SubscriptionInvoice,
    SubscriptionStatus,
)

pytestmark = pytest.mark.django_db


def _cancel_trial(tenant) -> None:
    with organization_context(tenant.organization.id):
        Subscription.objects.filter(organization=tenant.organization).update(
            status=SubscriptionStatus.CANCELLED, cancelled_at=timezone.now()
        )


def test_a_demo_gets_a_complimentary_active_subscription(tenant_a):
    _cancel_trial(tenant_a)
    with organization_context(tenant_a.organization.id):
        subscription = services.ensure_demo_subscription(organization=tenant_a.organization)
        again = services.ensure_demo_subscription(organization=tenant_a.organization)

    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.discount_percent == Decimal("100")
    assert again.pk == subscription.pk

    response = tenant_a.client().get("/api/v1/billing/subscription")
    assert response.status_code == 200, response.json()


def test_a_zero_invoice_is_never_overdue(tenant_a):
    with organization_context(tenant_a.organization.id):
        invoice = services.accept_trial(
            subscription=Subscription.objects.get(organization=tenant_a.organization)
        )
        SubscriptionInvoice.objects.filter(pk=invoice.pk).update(
            # 100 % chegirma: chegirma = baza + ortiqcha, jami = 0.
            discount_amount=invoice.base_amount + invoice.overage_amount,
            total_amount=Decimal("0"),
            issued_at=timezone.localdate() - timedelta(days=30),
            due_at=timezone.localdate() - timedelta(days=20),
        )
        assert services.mark_past_due() == 0


def test_the_command_is_a_dry_run_by_default(tenant_a):
    _cancel_trial(tenant_a)
    slug = tenant_a.organization.slug

    call_command("demo_subscription", "--slug", slug, stdout=StringIO())
    with organization_context(tenant_a.organization.id):
        assert not Subscription.objects.exclude(status=SubscriptionStatus.CANCELLED).exists()

    call_command("demo_subscription", "--slug", slug, "--apply", stdout=StringIO())
    with organization_context(tenant_a.organization.id):
        live = Subscription.objects.exclude(status=SubscriptionStatus.CANCELLED).get()
    assert live.status == SubscriptionStatus.ACTIVE
