"""
Rebuilds the bot's contact index from the guardian rows (ADR-27).

    python manage.py rebuild_contact_index            # dry run: counts only
    python manage.py rebuild_contact_index --apply    # writes
    python manage.py rebuild_contact_index --tenant <slug> --apply

Needed once after deploying PLAN 6.2/6.3 (existing guardians have no
index rows yet), and again whenever `CONTACT_INDEX_KEY` or `SECRET_KEY`
changes. It touches ONLY `contact_index` — guardian rows are read, never
written. Each organization is rebuilt inside its own context: missing
rows are added, rows no guardian accounts for any more are removed.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context


class Command(BaseCommand):
    help = "Rebuild the parent bot's contact index (dry run unless --apply)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--apply", action="store_true", help="Write the changes.")
        parser.add_argument("--tenant", help="Organization slug; default: all.")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.children.models import Guardian
        from apps.organizations.models import Organization
        from apps.parent_bot.index import entries_for_guardian
        from apps.parent_bot.models import ContactIndex

        apply = bool(options["apply"])
        with platform_context():
            organizations = Organization.objects.order_by("name")
            if options.get("tenant"):
                organizations = organizations.filter(slug=options["tenant"])
                if not organizations.exists():
                    raise CommandError(f"No organization with slug {options['tenant']!r}.")
            targets = list(organizations.values_list("id", "name"))

        total_add = total_remove = 0
        for organization_id, name in targets:
            with organization_context(organization_id):
                wanted: set[tuple[str, str]] = set()
                for guardian in Guardian.objects.filter(is_active=True).only(
                    "id", "phone", "telegram_chat_id", "is_active", "organization_id"
                ):
                    wanted.update(entries_for_guardian(guardian))
                existing = set(
                    ContactIndex.all_objects.filter(organization_id=organization_id).values_list(
                        "kind", "digest"
                    )
                )
                to_add = wanted - existing
                to_remove = existing - wanted
                if apply and (to_add or to_remove):
                    with transaction.atomic():
                        ContactIndex.all_objects.bulk_create(
                            [
                                ContactIndex(organization_id=organization_id, kind=k, digest=d)
                                for k, d in to_add
                            ],
                            ignore_conflicts=True,
                        )
                        for kind, value_digest in to_remove:
                            ContactIndex.all_objects.filter(
                                organization_id=organization_id, kind=kind, digest=value_digest
                            ).delete()
            total_add += len(to_add)
            total_remove += len(to_remove)
            self.stdout.write(f"{name}: +{len(to_add)} −{len(to_remove)} (wanted {len(wanted)})")

        verb = "Applied" if apply else "Dry run — nothing written"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb}: +{total_add} −{total_remove} across {len(targets)} org(s)."
            )
        )
