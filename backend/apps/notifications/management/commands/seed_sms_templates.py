"""
Mavjud bog'chalarga ruscha SMS shablonlarini qo'shadi (PLAN 3.4).

**Nega migratsiya emas.** Shablon matni — MIJOZNING matni, bizniki
emas: bog'cha uni tahrirlaydi va o'z nomi bilan yuboradi. Migratsiya
uni jimgina, egasidan so'ramasdan qo'shardi. Yangi bog'chalar buni
ro'yxatdan o'tishda oladi (`seed_default_templates`); bu buyruq esa
AVVALDAN mavjud bog'chalar uchun.

Mavjud shablonlarga TEGMAYDI: faqat yetishmaydigan tilni qo'shadi.
Ya'ni bog'cha o'z o'zbekcha matnini tahrirlagan bo'lsa, u o'z joyida
qoladi.

Ishlatish::

    # Avval KO'RISH — hech narsa yozilmaydi
    python manage.py seed_sms_templates --tenant oriental-kinderland --dry-run

    # Ro'yxat to'g'ri bo'lsa, qo'llash
    python manage.py seed_sms_templates --tenant oriental-kinderland

    # Hamma bog'cha uchun (ataylab ALOHIDA bayroq)
    python manage.py seed_sms_templates --all --dry-run
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context
from apps.notifications.models import Channel, NotificationTemplate, TemplateLanguage
from apps.notifications.services import DEFAULT_TEMPLATES_RU
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Mavjud tashkilotlarga ruscha SMS shablonlarini qo'shadi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--tenant", help="Tashkilot slug'i")
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all_tenants",
            help="Barcha faol tashkilotlar uchun",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Faqat ko'rsatadi, hech narsa yozmaydi",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        tenant = options.get("tenant")
        all_tenants = options.get("all_tenants")
        dry_run = options.get("dry_run")

        if not tenant and not all_tenants:
            raise CommandError("`--tenant <slug>` yoki `--all` ko'rsating.")

        with platform_context():
            queryset = Organization.objects.filter(is_active=True)
            if tenant:
                queryset = queryset.filter(slug=tenant)
            organizations = list(queryset)

        if not organizations:
            raise CommandError("Tashkilot topilmadi.")

        total = 0
        for organization in organizations:
            created = self._seed(organization, dry_run=bool(dry_run))
            total += created
            self.stdout.write(f"{organization.slug}: {created} ta shablon")

        verb = "qo'shiladi" if dry_run else "qo'shildi"
        self.stdout.write(self.style.SUCCESS(f"Jami {total} ta ruscha shablon {verb}."))
        if dry_run:
            self.stdout.write("DRY-RUN — hech narsa yozilmadi.")

    def _seed(self, organization: Organization, *, dry_run: bool) -> int:
        created = 0
        with organization_context(organization.id), transaction.atomic():
            for code, body in DEFAULT_TEMPLATES_RU.items():
                exists = NotificationTemplate.objects.filter(
                    code=code,
                    channel=Channel.SMS,
                    language=TemplateLanguage.RU,
                    branch__isnull=True,
                ).exists()
                if exists:
                    continue
                created += 1
                if not dry_run:
                    NotificationTemplate.objects.create(
                        organization=organization,
                        branch=None,
                        code=code,
                        channel=Channel.SMS,
                        language=TemplateLanguage.RU,
                        body=body,
                    )
            if dry_run:
                transaction.set_rollback(True)
        return created
