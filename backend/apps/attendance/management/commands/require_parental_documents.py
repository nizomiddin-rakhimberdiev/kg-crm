"""
"Ota-ona arizasi" turiga hujjatni majburiy qiladi (egasining qarori, 2026-11-12).

ADR-19: kredit hujjatdan keladi. Ariza o'zi hujjat — uning raqami yoki
sanasi iz qoldiradi. Yangi tashkilotlar buni `DEFAULT_KINDS` dan oladi;
mavjudlari shu buyruq bilan yangilanadi. Faqat hali sukutda turgan
(`requires_document=False`) turlarga tegiladi.

Sukut bo'yicha dry-run: hech narsa o'zgarmaydi, faqat ro'yxat.

    python manage.py require_parental_documents
    python manage.py require_parental_documents --slug analiz --apply
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.core.tenancy import organization_context, platform_context


class Command(BaseCommand):
    help = "Ota-ona arizasi turida hujjatni majburiy qiladi (dry-run sukut)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", help="Faqat shu tashkilot; bo'lmasa — hammasi")
        parser.add_argument("--apply", action="store_true", help="Haqiqatan yangilash")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.attendance.models_absence import AbsenceKind, ClaimKind
        from apps.organizations.models import Organization

        slug, apply_it = options.get("slug"), options["apply"]
        with platform_context():
            organizations = list(Organization.objects.order_by("name"))
        if slug:
            organizations = [o for o in organizations if o.slug == slug]
            if not organizations:
                raise CommandError(f"Tashkilot topilmadi: {slug}")

        mode = self.style.ERROR("YANGILASH") if apply_it else self.style.WARNING("dry-run")
        self.stdout.write(f"Rejim: {mode}")
        total = 0
        for organization in organizations:
            with organization_context(organization.id):
                kinds = AbsenceKind.objects.filter(code=ClaimKind.PARENTAL, requires_document=False)
                count = kinds.count()
                if not count:
                    continue
                total += count
                self.stdout.write(f"{organization.name} ({organization.slug}): {count} ta tur")
                if apply_it:
                    kinds.update(requires_document=True)
        verb = "Yangilandi" if apply_it else "Yangilanadi"
        self.stdout.write(self.style.SUCCESS(f"{verb}: {total} ta"))
