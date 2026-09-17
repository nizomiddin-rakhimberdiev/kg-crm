"""
Standalone nusxani ishga tayyorlaydi — bitta bog'cha, bitta ega.

SaaS'da bog'chani vendor konsoli ochadi (ADR-10). Standalone'da vendor
tekisligi umuman yo'q (ADR-13), ya'ni birinchi tashkilotni yaratadigan
BOSHQA yo'l kerak — aks holda yangi o'rnatilgan tizimga hech kim kira
olmasdi.

Ishlatish::

    python manage.py setup_standalone \\
        --name "Quyosh bog'chasi" \\
        --email egasi@example.com \\
        --full-name "Aziza Karimova" \\
        --password '<parol>'

Buyruq ATAYLAB ikkinchi marta ishlamaydi: standalone o'rnatmada bitta
bog'cha bo'ladi. Ikkinchi tashkilot paydo bo'lishi — yo xato, yo
mijozning SaaS'ga o'tishi kerak bo'lgan holati.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.core.deployment import is_standalone
from apps.core.tenancy import platform_context


class Command(BaseCommand):
    help = "Standalone o'rnatma uchun birinchi (yagona) bog'chani yaratadi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--name", required=True, help="Bog'cha nomi")
        parser.add_argument("--email", required=True, help="Egasining emaili (login)")
        parser.add_argument("--full-name", required=True, help="Egasining to'liq ismi")
        parser.add_argument("--password", required=True, help="Boshlang'ich parol")
        parser.add_argument("--phone", default="", help="Telefon (ixtiyoriy)")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.accounts.services import register_organization
        from apps.organizations.models import Organization

        if not is_standalone():
            raise CommandError(
                "Bu buyruq faqat DEPLOYMENT_MODE=standalone da ishlaydi. "
                "SaaS nusxasida bog'cha vendor konsoli orqali ochiladi (ADR-10)."
            )

        with platform_context():
            existing = Organization.objects.first()
            if existing is not None:
                raise CommandError(
                    f"Bu o'rnatmada bog'cha allaqachon bor: {existing.name}. "
                    "Standalone nusxa bitta bog'cha uchun mo'ljallangan (ADR-13)."
                )

        result = register_organization(
            organization_name=options["name"],
            contact_email=options["email"],
            full_name=options["full_name"],
            password=options["password"],
            contact_phone=options["phone"],
        )

        self.stdout.write(self.style.SUCCESS(f"\n{result.organization.name} tayyor."))
        self.stdout.write(f"  login:  {result.owner.email}")
        self.stdout.write("  parol:  (siz kiritgan parol)")
        self.stdout.write("\nObuna, tarif va sinov muddati YO'Q — tizim to'liq ochiq (ADR-13).\n")
