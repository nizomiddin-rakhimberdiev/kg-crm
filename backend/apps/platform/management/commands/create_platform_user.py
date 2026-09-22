"""
Vendor xodimi hisobini yaratadi yoki parolini yangilaydi (ADR-10).

Buyruq orqali, API orqali EMAS: platforma hisobi yaratish endpointi
bo'lsa, u tabiiy ravishda eng qimmatli nishonga aylanardi. Serverga
kira oladigan odam esa allaqachon shu darajadagi kirishga ega.

2FA (`PLATFORM_2FA_REQUIRED`, ADR-15) yoqilgan bo'lsa, TOTP sirini
ekranga chiqaradi — uni Authenticator ilovasiga qo'shish kerak. Sir
faqat SHU YERDA ko'rinadi; keyin uni qayta ko'rsatib bo'lmaydi.
O'chiq bo'lsa ham sir yaratiladi va saqlanadi — 2FA keyin yoqilganda
hisob qulflanib qolmasin.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core.tenancy import platform_context
from apps.platform.models import PlatformRole, PlatformUser
from apps.platform.totp import generate_secret, provisioning_uri


class Command(BaseCommand):
    help = "Platforma (vendor) xodimi hisobini yaratadi yoki parolini yangilaydi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", help="Yangi hisob uchun majburiy")
        parser.add_argument("--password", required=True)
        parser.add_argument(
            "--role",
            default=PlatformRole.ADMIN,
            choices=[PlatformRole.ADMIN, PlatformRole.SUPPORT],
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Hisob mavjud bo'lsa — parolni (va berilgan bo'lsa ism/rolni) yangilaydi",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        email = options["email"]
        with platform_context():
            existing = PlatformUser.objects.filter(email__iexact=email).first()
            if existing is not None and not options["update"]:
                raise CommandError(f"'{email}' allaqachon mavjud. Parolni yangilash: --update")

            if existing is not None:
                user = existing
                if options.get("name"):
                    user.full_name = options["name"]
                if options.get("role"):
                    user.role = options["role"]
                user.is_active = True
                user.set_password(options["password"])
                user.save()
                secret = None
            else:
                if not options.get("name"):
                    raise CommandError("Yangi hisob uchun `--name` kerak.")
                secret = generate_secret()
                user = PlatformUser(
                    email=email,
                    full_name=options["name"],
                    role=options["role"],
                    totp_secret=secret,
                    # Darhol tasdiqlangan: buyruqni serverda ishga tushirgan
                    # odam allaqachon eng yuqori darajadagi kirishga ega.
                    totp_confirmed_at=timezone.now(),
                )
                user.set_password(options["password"])
                user.save()

        verb = "Yangilandi" if secret is None else "Yaratildi"
        self.stdout.write(self.style.SUCCESS(f"{verb}: {user.email} ({user.role})"))
        self.stdout.write("Kirish: /platform/login")

        if secret is None:
            return

        self.stdout.write("")
        if settings.PLATFORM_2FA_REQUIRED:
            self.stdout.write(
                "Authenticator ilovasiga qo'shing (Google Authenticator, Authy, 1Password):"
            )
        else:
            self.stdout.write(
                "2FA hozir O'CHIQ (PLATFORM_2FA_REQUIRED=false) — kirish email + parol bilan. "
                "Keyin yoqsangiz, shu sir kerak bo'ladi; saqlab qo'ying:"
            )
        self.stdout.write(self.style.WARNING(f"  Sir:  {secret}"))
        self.stdout.write(f"  URI:  {provisioning_uri(secret, account=user.email)}")
        self.stdout.write("")
        self.stdout.write("⚠️ Bu sir boshqa ko'rsatilmaydi.")
