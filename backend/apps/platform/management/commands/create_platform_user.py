"""
Vendor xodimi hisobini yaratadi (ADR-10).

Buyruq orqali, API orqali EMAS: platforma hisobi yaratish endpointi
bo'lsa, u tabiiy ravishda eng qimmatli nishonga aylanardi. Serverga
kira oladigan odam esa allaqachon shu darajadagi kirishga ega.

2FA sirini ekranga chiqaradi — uni Authenticator ilovasiga qo'shish
kerak. Sir faqat SHU YERDA ko'rinadi; keyin uni qayta ko'rsatib
bo'lmaydi.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core.tenancy import platform_context
from apps.platform.models import PlatformRole, PlatformUser
from apps.platform.totp import generate_secret, provisioning_uri


class Command(BaseCommand):
    help = "Platforma (vendor) xodimi hisobini yaratadi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument(
            "--role",
            default=PlatformRole.ADMIN,
            choices=[PlatformRole.ADMIN, PlatformRole.SUPPORT],
        )

    def handle(self, *args: Any, **options: Any) -> None:
        with platform_context():
            if PlatformUser.objects.filter(email__iexact=options["email"]).exists():
                raise CommandError(f"'{options['email']}' allaqachon mavjud.")

            secret = generate_secret()
            user = PlatformUser(
                email=options["email"],
                full_name=options["name"],
                role=options["role"],
                totp_secret=secret,
                # Darhol tasdiqlangan: buyruqni serverda ishga tushirgan
                # odam allaqachon eng yuqori darajadagi kirishga ega.
                totp_confirmed_at=timezone.now(),
            )
            user.set_password(options["password"])
            user.save()

        self.stdout.write(self.style.SUCCESS(f"Yaratildi: {user.email} ({user.role})"))
        self.stdout.write("")
        self.stdout.write(
            "Authenticator ilovasiga qo'shing (Google Authenticator, Authy, 1Password):"
        )
        self.stdout.write(self.style.WARNING(f"  Sir:  {secret}"))
        self.stdout.write(f"  URI:  {provisioning_uri(secret, account=user.email)}")
        self.stdout.write("")
        self.stdout.write("⚠️ Bu sir boshqa ko'rsatilmaydi. Hozir qo'shing.")
        self.stdout.write("Kirish: /platform/login")
