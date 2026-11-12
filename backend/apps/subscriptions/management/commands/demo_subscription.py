"""
Demo tashkilotga bepul faol obuna beradi (audit 2026-11-12).

`analiz` stendining sinovi tugab bekor bo'lgan, va "Obuna va to'lov"
sahifasi bo'sh ochilardi. Faqat demo uchun — mijozning tashkilotiga
ishlatilmaydi: u holda bepul obuna hisob-kitobni yashirardi.

Sukut bo'yicha dry-run.

    python manage.py demo_subscription --slug analiz
    python manage.py demo_subscription --slug analiz --apply
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.core.tenancy import organization_context, platform_context


class Command(BaseCommand):
    help = "Demo tashkilotga 100 % chegirmali faol obuna (dry-run sukut)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", required=True, help="Demo tashkilot slugʻi")
        parser.add_argument("--apply", action="store_true", help="Haqiqatan yozish")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.organizations.models import Organization
        from apps.subscriptions import services
        from apps.subscriptions.models import Subscription, SubscriptionStatus

        slug, apply_it = options["slug"], options["apply"]
        with platform_context():
            organization = Organization.objects.filter(slug=slug).first()
        if organization is None:
            raise CommandError(f"Tashkilot topilmadi: {slug}")

        with organization_context(organization.id):
            live = (
                Subscription.objects.filter(organization=organization)
                .exclude(status=SubscriptionStatus.CANCELLED)
                .first()
            )
            now = f"{live.status}, {live.discount_percent} %" if live else "obuna yoʻq"
            self.stdout.write(f"{organization.name} ({slug}): hozir — {now}")
            if not apply_it:
                self.stdout.write(self.style.WARNING("dry-run: faol, 100 % boʻladi (--apply)"))
                return
            services.ensure_demo_subscription(organization=organization)
        self.stdout.write(self.style.SUCCESS("Yozildi: faol, 100 %"))
