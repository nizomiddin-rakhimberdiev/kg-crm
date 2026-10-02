"""
Mavjud bog'chalarga yetishmayotgan xabar shablonlarini qo'shadi.

Shablonlar to'plami kanal × tilga ko'payib boradi: dastlab faqat
o'zbekcha SMS bor edi, keyin ruscha (PLAN 3.4), keyin Telegram
(PLAN 3.7). Yangi bog'cha hammasini ro'yxatdan o'tishda oladi
(`seed_default_templates`), bu buyruq esa AVVALDAN mavjud bog'chalar
uchun.

**Nega migratsiya emas.** Shablon matni — MIJOZNING matni, bizniki
emas: bog'cha uni tahrirlaydi va o'z nomi bilan yuboradi. Migratsiya
uni jimgina, egasidan so'ramasdan qo'shardi.

Mavjud shablonlarga TEGMAYDI — faqat yetishmayotganini qo'shadi.
Ya'ni bog'cha o'z matnini tahrirlagan bo'lsa, u o'z joyida qoladi.

Ishlatish::

    # Avval KO'RISH — hech narsa yozilmaydi
    python manage.py seed_templates --tenant oriental-kinderland --dry-run

    # Ro'yxat to'g'ri bo'lsa, qo'llash
    python manage.py seed_templates --tenant oriental-kinderland

    # Hamma bog'cha uchun (ataylab ALOHIDA bayroq)
    python manage.py seed_templates --all --dry-run
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context
from apps.notifications.services import seed_default_templates
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Mavjud tashkilotlarga yetishmayotgan xabar shablonlarini qo'shadi."

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
        dry_run = bool(options.get("dry_run"))

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
            created = self._seed(organization, dry_run=dry_run)
            total += created
            self.stdout.write(f"{organization.slug}: {created} ta shablon")

        verb = "qo'shiladi" if dry_run else "qo'shildi"
        self.stdout.write(self.style.SUCCESS(f"Jami {total} ta shablon {verb}."))
        if dry_run:
            self.stdout.write("DRY-RUN — hech narsa yozilmadi.")

    def _seed(self, organization: Organization, *, dry_run: bool) -> int:
        """
        Yetishmayotganini sanaydi va (dry-run bo'lmasa) yozadi.

        Sanash uchun AYNAN yozish yo'li ishlatiladi va dry-run'da
        tranzaksiya qaytariladi: alohida "nima yetishmayapti" so'rovi
        yozish mantiqidan ajralib ketardi va buyruq boshqa narsani
        ko'rsatib, boshqa narsani yozardi.
        """
        with organization_context(organization.id), transaction.atomic():
            created = seed_default_templates(organization)
            if dry_run:
                transaction.set_rollback(True)
        return created
