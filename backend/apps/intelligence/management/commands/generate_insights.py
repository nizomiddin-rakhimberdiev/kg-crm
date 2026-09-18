"""
Insight'larni qo'lda hisoblash — demo va qabul testi uchun (docs/07 §11).

    python manage.py generate_insights                  # barcha tashkilotlar
    python manage.py generate_insights --slug bahor-bogchasi
    python manage.py generate_insights --slug ... --as-of 2026-09-17

Kechki vazifa bilan AYNAN bir xil kod yo'li (`services.generate_for_branch`)
— buyruq alohida mantiq emas, o'sha vazifaning qo'lda ishga tushirilishi.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.core.tenancy import organization_context, platform_context
from apps.intelligence import selectors, services
from apps.intelligence.content import uz as content


class Command(BaseCommand):
    help = "Radix Intelligence: insight'larni hisoblaydi va saqlaydi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", help="Faqat shu tashkilot")
        parser.add_argument("--as-of", help="Hisob sanasi (YYYY-MM-DD), sukut — bugun")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.organizations.models import Organization

        as_of = date.fromisoformat(options["as_of"]) if options.get("as_of") else None

        with platform_context():
            queryset = Organization.objects.filter(is_active=True)
            if options.get("slug"):
                queryset = queryset.filter(slug=options["slug"])
            organizations = list(queryset)
        if not organizations:
            raise CommandError("Tashkilot topilmadi.")

        for organization in organizations:
            with organization_context(organization.id):
                self.stdout.write(f"{organization.name} ({organization.slug})")
                for branch_id in selectors.branch_ids_for(organization.id):
                    result = services.generate_for_branch(
                        organization=organization, branch_id=branch_id, as_of=as_of
                    )
                    self.stdout.write(f"  filial {branch_id}: {result.as_dict()}")
                    self._print_open(branch_id)

    def _print_open(self, branch_id: Any) -> None:
        from apps.intelligence.models import OPEN_STATUSES, Insight

        for row in Insight.objects.filter(branch_id=branch_id, status__in=OPEN_STATUSES):
            self.stdout.write(
                f"    [{row.severity}] {content.title(row.type, row.evidence)}"
                f"  →  {content.recommendation(row.recommendation_key)}  ({row.deep_link})"
            )
