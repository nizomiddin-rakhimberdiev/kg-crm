"""
Subscription invoices paid through Radix's own Payme / Click (PLAN 6.4).

The same protocol code as tuition (6.1), a different ledger: the tenant
comes from the invoice NUMBER, the payment is a subscription payment, a
suspended organization can always pay, and a refund is never automatic.
"""

from __future__ import annotations

import base64
import hashlib

import pytest

from apps.core.tenancy import organization_context
from apps.subscriptions import services
from apps.subscriptions.models import (
    Subscription,
    SubscriptionInvoice,
    SubscriptionPayment,
    SubscriptionStatus,
)

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

PAYME_KEY = "radix-payme-key"
CLICK_KEY = "radix-click-key"
PAYME_URL = "/api/v1/public/pay/subscription/payme"
CLICK_URL = "/api/v1/public/pay/subscription/click"


@pytest.fixture
def radix(settings):
    settings.RADIX_PAYME_MERCHANT_ID = "radix-m"
    settings.RADIX_PAYME_KEY = PAYME_KEY
    settings.RADIX_CLICK_MERCHANT_ID = "77"
    settings.RADIX_CLICK_SERVICE_ID = "555"
    settings.RADIX_CLICK_SECRET = CLICK_KEY
    settings.FRONTEND_URL = "https://radix-crm.uz"
    return settings


def _invoice(tenant) -> SubscriptionInvoice:
    with organization_context(tenant.organization.id):
        subscription = Subscription.objects.get(organization=tenant.organization)
        return services.accept_trial(subscription=subscription)


def _suspend(tenant) -> None:
    with organization_context(tenant.organization.id):
        Subscription.objects.filter(organization=tenant.organization).update(
            status=SubscriptionStatus.SUSPENDED
        )


def _payme(api_client, method: str, params: dict, key: str = PAYME_KEY) -> dict:
    auth = "Basic " + base64.b64encode(f"Paycom:{key}".encode()).decode()
    response = api_client.post(
        PAYME_URL,
        {"method": method, "params": params, "id": 1},
        format="json",
        HTTP_AUTHORIZATION=auth,
    )
    assert response.status_code == 200
    return response.json()


def _tiyin(invoice: SubscriptionInvoice) -> int:
    return int(invoice.total_amount * 100)


def _state(tenant):
    with organization_context(tenant.organization.id):
        subscription = Subscription.objects.get(organization=tenant.organization)
        payments = list(SubscriptionPayment.objects.all())
    return subscription, payments


class TestPayme:
    def test_payment_closes_the_invoice_and_lifts_a_suspension(self, api_client, radix, tenant_a):
        invoice = _invoice(tenant_a)
        _suspend(tenant_a)
        account = {"invoice": invoice.number}
        created = _payme(
            api_client,
            "CreateTransaction",
            {"id": "s-1", "time": 1, "amount": _tiyin(invoice), "account": account},
        )
        assert created["result"]["state"] == 1
        assert _payme(api_client, "PerformTransaction", {"id": "s-1"})["result"]["state"] == 2

        subscription, payments = _state(tenant_a)
        assert subscription.status == SubscriptionStatus.ACTIVE
        (payment,) = payments
        assert payment.method == "online" and payment.amount == invoice.total_amount
        with organization_context(tenant_a.organization.id):
            invoice.refresh_from_db()
        assert invoice.status == "paid"

    def test_a_retried_perform_records_once(self, api_client, radix, tenant_a):
        invoice = _invoice(tenant_a)
        params = {"id": "s-2", "time": 1, "amount": _tiyin(invoice)}
        _payme(api_client, "CreateTransaction", {**params, "account": {"invoice": invoice.number}})
        _payme(api_client, "PerformTransaction", {"id": "s-2"})
        _payme(api_client, "PerformTransaction", {"id": "s-2"})
        assert len(_state(tenant_a)[1]) == 1

    def test_a_wrong_key_is_refused(self, api_client, radix, tenant_a):
        invoice = _invoice(tenant_a)
        body = _payme(
            api_client,
            "CheckPerformTransaction",
            {"amount": _tiyin(invoice), "account": {"invoice": invoice.number}},
            key="tuition-key-of-some-kindergarten",
        )
        assert body["error"]["code"] == -32504

    def test_without_radix_keys_nothing_works(self, api_client, tenant_a):
        invoice = _invoice(tenant_a)
        body = _payme(
            api_client,
            "CheckPerformTransaction",
            {"amount": _tiyin(invoice), "account": {"invoice": invoice.number}},
        )
        assert body["error"]["code"] == -32504

    def test_an_unknown_number_is_not_found(self, api_client, radix, tenant_a):
        body = _payme(
            api_client, "CheckPerformTransaction", {"amount": 100, "account": {"invoice": "NOPE"}}
        )
        assert body["error"]["code"] == -31050

    def test_a_tuition_invoice_id_is_not_a_subscription_invoice(self, api_client, radix, tenant_a):
        """The two ledgers never mix: a kindergarten's invoice id finds nothing here."""
        from apps.online_payments.tests.conftest import make_invoice

        tuition = make_invoice(tenant_a)
        body = _payme(
            api_client,
            "CheckPerformTransaction",
            {"amount": 100, "account": {"invoice": str(tuition.id)}},
        )
        assert body["error"]["code"] == -31050

    def test_a_refund_after_payment_is_refused(self, api_client, radix, tenant_a):
        invoice = _invoice(tenant_a)
        params = {"id": "s-3", "time": 1, "amount": _tiyin(invoice)}
        _payme(api_client, "CreateTransaction", {**params, "account": {"invoice": invoice.number}})
        _payme(api_client, "PerformTransaction", {"id": "s-3"})
        body = _payme(api_client, "CancelTransaction", {"id": "s-3", "reason": 5})
        assert body["error"]["code"] == -31007
        assert len(_state(tenant_a)[1]) == 1

    def test_cancelling_before_payment_is_fine(self, api_client, radix, tenant_a):
        invoice = _invoice(tenant_a)
        params = {"id": "s-4", "time": 1, "amount": _tiyin(invoice)}
        _payme(api_client, "CreateTransaction", {**params, "account": {"invoice": invoice.number}})
        body = _payme(api_client, "CancelTransaction", {"id": "s-4", "reason": 3})
        assert body["result"]["state"] == -1
        assert _state(tenant_a)[1] == []


def _click(api_client, fields: dict) -> dict:
    parts = [fields["click_trans_id"], fields["service_id"], CLICK_KEY, fields["merchant_trans_id"]]
    if fields["action"] == "1":
        parts.append(fields["merchant_prepare_id"])
    parts += [fields["amount"], fields["action"], fields["sign_time"]]
    sign = hashlib.md5("".join(parts).encode(), usedforsecurity=False).hexdigest()
    response = api_client.post(CLICK_URL, {**fields, "sign_string": sign})
    assert response.status_code == 200
    return response.json()


class TestClick:
    def test_prepare_and_complete_pay_the_invoice(self, api_client, radix, tenant_a):
        invoice = _invoice(tenant_a)
        base = {
            "click_trans_id": "8001",
            "service_id": "555",
            "merchant_trans_id": invoice.number,
            "amount": f"{invoice.total_amount:.2f}",
            "error": "0",
            "sign_time": "2026-10-03 12:00:00",
        }
        assert _click(api_client, {**base, "action": "0"})["error"] == 0
        done = _click(api_client, {**base, "action": "1", "merchant_prepare_id": "8001"})
        assert done["error"] == 0
        assert _state(tenant_a)[0].status == SubscriptionStatus.ACTIVE


class TestPayLinksEndpoint:
    def _url(self, invoice) -> str:
        return f"/api/v1/billing/invoices/{invoice.id}/pay"

    def test_links_for_an_open_invoice(self, radix, tenant_a):
        invoice = _invoice(tenant_a)
        data = tenant_a.client().get(self._url(invoice)).json()["data"]["providers"]
        assert set(data) == {"payme", "click"}
        payload = base64.b64decode(data["payme"].rsplit("/", 1)[1]).decode()
        assert f"ac.invoice={invoice.number}" in payload
        assert f"/t/{tenant_a.organization.slug}/billing?paid=1" in payload

    def test_a_suspended_organization_can_still_pay(self, radix, tenant_a):
        invoice = _invoice(tenant_a)
        _suspend(tenant_a)
        response = tenant_a.client().get(self._url(invoice))
        assert response.status_code == 200

    def test_without_radix_keys_there_are_no_links(self, tenant_a):
        invoice = _invoice(tenant_a)
        assert tenant_a.client().get(self._url(invoice)).json()["data"]["providers"] == {}

    def test_another_organizations_invoice_is_404(self, radix, tenant_a, tenant_b):
        foreign = _invoice(tenant_b)
        assert tenant_a.client().get(self._url(foreign)).status_code == 404
