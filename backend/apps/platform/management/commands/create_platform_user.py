"""
Vendor xodimi hisobini yaratadi yoki parolini yangilaydi (ADR-10).

Buyruq orqali, API orqali EMAS: platforma hisobi yaratish endpointi
bo'lsa, u tabiiy ravishda eng qimmatli nishonga aylanardi. Serverga
kira oladigan odam esa allaqachon shu darajadagi kirishga ega.

2FA (`PLATFORM_2FA_REQUIRED`, ADR-24 — sukut bo'yicha YOQILGAN) uchun
TOTP sirini va **zaxira kodlarini** ekranga chiqaradi. Ikkalasi faqat
SHU YERDA ko'rinadi; keyin ularni qayta ko'rsatib bo'lmaydi.

Telefon sinsa va zaxira kodlari ham yo'q bo'lsa — yagona yo'l shu
buyruq: `--update --new-2fa` yangi sir va yangi kodlar beradi. Bu
ATAYLAB serverda: konsol orqali 2FA ni tiklash endpointi bo'lsa, u
2FA ning o'zini ma'nosiz qilardi.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core import backup_codes
from apps.core.tenancy import platform_context
from apps.core.totp import generate_secret, provisioning_uri
from apps.platform.models import PlatformRole, PlatformUser


class Command(BaseCommand):
    help = "Platforma (vendor) xodimi hisobini yaratadi yoki parolini yangilaydi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", help="Yangi hisob uchun majburiy")
        # Yangi hisob uchun majburiy; `--update` da ixtiyoriy — 2FA ni
        # tiklash (`--new-2fa`) parolni ham almashtirishga majburlamasin.
        parser.add_argument("--password")
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
        parser.add_argument(
            "--new-2fa",
            action="store_true",
            help="Yangi TOTP siri va yangi zaxira kodlari (telefon yo'qolganda)",
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
                if options.get("password"):
                    user.set_password(options["password"])
                secret = None
                codes: list[str] = []
                if options.get("new_2fa"):
                    secret = generate_secret()
                    codes, hashes = backup_codes.generate()
                    user.totp_secret = secret
                    user.totp_confirmed_at = timezone.now()
                    user.totp_backup_codes = hashes
                user.save()
            else:
                if not options.get("name"):
                    raise CommandError("Yangi hisob uchun `--name` kerak.")
                if not options.get("password"):
                    raise CommandError("Yangi hisob uchun `--password` kerak.")
                secret = generate_secret()
                codes, hashes = backup_codes.generate()
                user = PlatformUser(
                    email=email,
                    full_name=options["name"],
                    role=options["role"],
                    totp_secret=secret,
                    # Darhol tasdiqlangan: buyruqni serverda ishga tushirgan
                    # odam allaqachon eng yuqori darajadagi kirishga ega.
                    totp_confirmed_at=timezone.now(),
                    totp_backup_codes=hashes,
                )
                user.set_password(options["password"])
                user.save()

        verb = "Yangilandi" if existing is not None else "Yaratildi"
        self.stdout.write(self.style.SUCCESS(f"{verb}: {user.email} ({user.role})"))
        self.stdout.write("Kirish: /platform/login")

        if secret is None:
            return

        self.stdout.write("")
        if existing is not None:
            # Eski sir va eski zaxira kodlari ENDI ISHLAMAYDI: telefon
            # yo'qolgan bo'lsa, u boshqa birovning qo'lida bo'lishi
            # mumkin.
            self.stdout.write("Eski sir va eski zaxira kodlari bekor qilindi.")
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

        # Zaxira kodlari — telefon sinsa konsolga kiradigan YAGONA
        # yo'l. Ularni qog'ozga yozib, sirdan boshqa joyda saqlash
        # kerak: ikkisi bir joyda bo'lsa, ikkinchi omil omil
        # bo'lmay qoladi.
        self.stdout.write("")
        self.stdout.write(f"Zaxira kodlari ({len(codes)} ta, har biri BIR MARTA ishlaydi):")
        for code in codes:
            self.stdout.write(self.style.WARNING(f"  {code}"))

        self.stdout.write("")
        self.stdout.write("⚠️ Sir ham, kodlar ham boshqa ko'rsatilmaydi.")
