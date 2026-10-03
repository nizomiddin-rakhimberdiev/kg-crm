"""
Removes self-signup trials that never became customers (PLAN 6.7, ADR-28).

    python manage.py purge_unconverted_trials            # dry run: lists only
    python manage.py purge_unconverted_trials --apply    # deletes

Two kinds of rows:

* **Unconfirmed signup requests** older than 7 days — no tenant was ever
  made; only the request row (name, e-mail, phone) goes.
* **Unconverted self-signup tenants**: created by a confirmed signup
  request, subscription cancelled at trial end, never a single
  subscription payment, and the trial ended more than the export window
  (30 days) ago — the customer had that whole time to export.

Vendor-opened organizations are NEVER candidates (no signup request points
at them) — including every tenant that existed before this command, such
as Oriental Kinderland. Paying, active and trialing tenants are never
candidates. Each purge goes through `purge_organization` (the same
ordered, audited path as the console) inside its own transaction.

The policy itself — deleting a never-paid trial — is ADR-28, which the
owner approves; that is why the default does nothing.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.tenancy import platform_context


class Command(BaseCommand):
    help = "Remove unconfirmed signups and unconverted self-signup trials (dry run by default)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--apply", action="store_true", help="Actually delete.")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.platform.models import SignupRequest
        from apps.platform.purge import EXPORT_WINDOW_DAYS, purge_organization
        from apps.platform.services_signup import PENDING_TTL
        from apps.subscriptions.models import (
            Subscription,
            SubscriptionPayment,
            SubscriptionStatus,
        )

        apply = bool(options["apply"])
        now = timezone.now()

        stale = SignupRequest.objects.filter(
            confirmed_at__isnull=True, created_at__lt=now - PENDING_TTL
        )
        self.stdout.write(f"Unconfirmed signup requests older than 7 days: {stale.count()}")
        if apply:
            stale.delete()

        cutoff = now - timedelta(days=EXPORT_WINDOW_DAYS)
        candidates: list[Any] = []
        with platform_context():
            signed_up = SignupRequest.objects.filter(organization__isnull=False).select_related(
                "organization"
            )
            for request in signed_up:
                organization = request.organization
                if organization is None:  # filtered out above; keeps the type checker honest
                    continue
                subscriptions = Subscription.all_objects.filter(organization=organization)
                if not subscriptions.exists():
                    continue
                if subscriptions.exclude(status=SubscriptionStatus.CANCELLED).exists():
                    continue  # trialing, pending, active, suspended — not ours to touch
                if SubscriptionPayment.all_objects.filter(organization=organization).exists():
                    continue  # it paid once: a customer, never purged here
                if subscriptions.filter(trial_ends_at__gte=cutoff).exists():
                    continue  # still inside the export window
                candidates.append(organization)

        for organization in candidates:
            self.stdout.write(f"  unconverted trial: {organization.slug} ({organization.name})")
        self.stdout.write(f"Unconverted self-signup trials: {len(candidates)}")

        if not apply:
            self.stdout.write(self.style.WARNING("Dry run — nothing deleted. Add --apply."))
            return
        for organization in candidates:
            # The command checked the window from the trial's END, so the
            # console's "updated_at" window is bypassed deliberately (force).
            deleted = purge_organization(
                organization_id=organization.id, confirm_slug=organization.slug, force=True
            )
            self.stdout.write(f"  purged {organization.slug}: {sum(deleted.values())} rows")
        self.stdout.write(self.style.SUCCESS("Done."))
