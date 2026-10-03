"""
Self-signup with a 14-day trial (PLAN 6.7, ADR-28).

The reason open signup was removed — a random visit leaving a tenant in
the database forever — must stay closed: no tenant before the e-mail link
is opened, one trial per e-mail, and the clean-up command never touches a
vendor-opened or paying organization.
"""

from __future__ import annotations

import re
import uuid
from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from apps.core.tenancy import organization_context, platform_context
from apps.organizations.models import Organization
from apps.platform.models import Lead, SignupRequest
from apps.subscriptions.models import Subscription, SubscriptionStatus

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

URL = "/api/v1/public/signup"
CONFIRM = "/api/v1/public/signup/confirm"
PASSWORD = "Bogcha-Parol-2026!"


@pytest.fixture(autouse=True)
def _commit_now(monkeypatch):
    monkeypatch.setattr("django.db.transaction.on_commit", lambda fn, *a, **k: fn())


def _payload(email: str = "egasi@quyosh.uz", **extra) -> dict:
    return {
        "name": "Dilnoza Karimova",
        "email": email,
        "phone": "+998901112233",
        "kindergarten_name": "Quyoshcha",
        "children_count": 40,
        "city": "Toshkent",
        "language": "uz",
        "consent": True,
        "privacy_policy_version": "2026-10-03",
        "submission_id": str(uuid.uuid4()),
        **extra,
    }


def _token() -> str:
    match = re.search(r"token=([\w-]+)", mail.outbox[-1].body)
    assert match, mail.outbox[-1].body
    return match.group(1)


def _organizations() -> int:
    with platform_context():
        return Organization.objects.count()


def _signup(api_client, email: str = "egasi@quyosh.uz") -> str:
    assert api_client.post(URL, _payload(email), format="json").status_code == 202
    return _token()


class TestRequest:
    def test_no_tenant_before_the_link_is_opened(self, api_client):
        before = _organizations()
        _signup(api_client)
        assert _organizations() == before
        assert SignupRequest.objects.get().confirmed_at is None
        assert Lead.objects.get().source == "self_signup"
        assert "/signup/confirm?token=" in mail.outbox[0].body

    def test_the_token_is_not_stored(self, api_client):
        token = _signup(api_client)
        assert SignupRequest.objects.get().token_hash != token

    def test_a_filled_honeypot_is_refused(self, api_client):
        response = api_client.post(URL, _payload(website="spam"), format="json")
        assert response.status_code == 400
        assert not SignupRequest.objects.exists()

    def test_consent_is_required(self, api_client):
        response = api_client.post(URL, _payload(consent=False), format="json")
        assert response.status_code == 400

    def test_asking_again_replaces_the_link(self, api_client):
        old = _signup(api_client)
        new = _signup(api_client)
        assert old != new
        assert (
            api_client.post(
                CONFIRM, {"token": old, "password": PASSWORD}, format="json"
            ).status_code
            == 422
        )
        assert SignupRequest.objects.count() == 1


class TestConfirm:
    def test_the_link_opens_a_14_day_trial(self, api_client):
        token = _signup(api_client)
        response = api_client.post(CONFIRM, {"token": token, "password": PASSWORD}, format="json")
        assert response.status_code == 201, response.json()
        slug = response.json()["data"]["slug"]
        with platform_context():
            organization = Organization.objects.get(slug=slug)
            subscription = Subscription.all_objects.get(organization=organization)
        assert subscription.status == SubscriptionStatus.TRIALING
        days = (subscription.trial_ends_at - subscription.trial_started_at).days
        assert days == 14
        login = api_client.post(
            "/api/v1/auth/login", {"email": "egasi@quyosh.uz", "password": PASSWORD}, format="json"
        )
        assert login.status_code == 200

    def test_a_link_works_once(self, api_client):
        token = _signup(api_client)
        api_client.post(CONFIRM, {"token": token, "password": PASSWORD}, format="json")
        again = api_client.post(CONFIRM, {"token": token, "password": PASSWORD}, format="json")
        assert again.status_code == 422

    def test_an_expired_link_is_refused(self, api_client):
        token = _signup(api_client)
        SignupRequest.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        response = api_client.post(CONFIRM, {"token": token, "password": PASSWORD}, format="json")
        assert response.status_code == 422

    def test_a_weak_password_creates_nothing(self, api_client):
        token = _signup(api_client)
        before = _organizations()
        response = api_client.post(CONFIRM, {"token": token, "password": "123"}, format="json")
        assert response.status_code == 400
        assert _organizations() == before

    def test_one_trial_per_email(self, api_client):
        first = _signup(api_client)
        api_client.post(CONFIRM, {"token": first, "password": PASSWORD}, format="json")
        second = _signup(api_client)
        response = api_client.post(CONFIRM, {"token": second, "password": PASSWORD}, format="json")
        assert response.status_code == 422

    def test_a_vendor_opened_trial_stays_15_days(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            subscription = Subscription.objects.get(organization=tenant_a.organization)
        assert (subscription.trial_ends_at - subscription.trial_started_at).days == 15


def _confirmed(api_client, email: str) -> Organization:
    token = _signup(api_client, email)
    slug = api_client.post(CONFIRM, {"token": token, "password": PASSWORD}, format="json").json()[
        "data"
    ]["slug"]
    with platform_context():
        return Organization.objects.get(slug=slug)


def _expire(organization: Organization, days_ago: int) -> None:
    ended = timezone.now() - timedelta(days=days_ago)
    with platform_context():
        Subscription.all_objects.filter(organization=organization).update(
            status=SubscriptionStatus.CANCELLED, trial_ends_at=ended, cancelled_at=ended
        )


def _exists(organization: Organization) -> bool:
    with platform_context():
        return Organization.objects.filter(pk=organization.pk).exists()


class TestPurge:
    def test_dry_run_deletes_nothing(self, api_client):
        organization = _confirmed(api_client, "a@a.uz")
        _expire(organization, 31)
        out = StringIO()
        call_command("purge_unconverted_trials", stdout=out)
        assert organization.slug in out.getvalue() and "Dry run" in out.getvalue()
        assert _exists(organization)

    def test_an_unconverted_self_signup_is_purged(self, api_client):
        organization = _confirmed(api_client, "b@b.uz")
        _expire(organization, 31)
        call_command("purge_unconverted_trials", "--apply", stdout=StringIO())
        assert not _exists(organization)
        assert not SignupRequest.objects.filter(email="b@b.uz").exists()

    def test_inside_the_export_window_it_stays(self, api_client):
        organization = _confirmed(api_client, "c@c.uz")
        _expire(organization, 10)
        call_command("purge_unconverted_trials", "--apply", stdout=StringIO())
        assert _exists(organization)

    def test_a_trial_that_ever_paid_stays(self, api_client):
        from apps.subscriptions.models import SubscriptionInvoice, SubscriptionPayment
        from apps.subscriptions.services import accept_trial

        organization = _confirmed(api_client, "d@d.uz")
        with organization_context(organization.id):
            invoice = accept_trial(subscription=Subscription.objects.get(organization=organization))
            SubscriptionPayment.objects.create(
                organization=organization,
                subscription_invoice=invoice,
                amount=Decimal("1000"),
                received_at=timezone.now(),
            )
            assert SubscriptionInvoice.objects.exists()
        _expire(organization, 60)
        call_command("purge_unconverted_trials", "--apply", stdout=StringIO())
        assert _exists(organization)

    def test_a_vendor_opened_organization_is_never_a_candidate(self, api_client, tenant_a):
        _expire(tenant_a.organization, 90)
        call_command("purge_unconverted_trials", "--apply", stdout=StringIO())
        assert _exists(tenant_a.organization)

    def test_stale_unconfirmed_requests_go(self, api_client):
        _signup(api_client, "e@e.uz")
        SignupRequest.objects.update(created_at=timezone.now() - timedelta(days=8))
        call_command("purge_unconverted_trials", "--apply", stdout=StringIO())
        assert not SignupRequest.objects.exists()
