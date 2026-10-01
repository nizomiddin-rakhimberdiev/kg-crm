"""
Noto'g'ri telefon raqamlarini SANAB BERADI — o'zgartirmaydi (PLAN 2.4).

Nega tuzatmaydi: "12345" ning o'rniga nima yozish kerakligini tizim
bilmaydi, va taxmin qilib yozish ota-onaning SMS'ini butunlay boshqa
odamga yuborardi. Ro'yxat esa mudiraga beriladi va u ota-onadan
so'raydi.

Nega migratsiya emas: mavjud tenantlarda allaqachon noto'g'ri
raqamlar bor va `CHECK` qo'shadigan migratsiya o'sha qatorlarni
yozishni to'xtatib qo'yardi — ya'ni bolaning kartasini saqlab
bo'lmaydigan holat.

    python manage.py report_bad_phones
    python manage.py report_bad_phones --tenant oriental-kinderland
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.phone import is_valid_phone
from apps.core.tenancy import organization_context, platform_context
from apps.organizations.models import Organization

#: (ilova, model, ekranda ko'rinadigan nom)
#
# Ism `str(row)` dan olinadi: `full_name` ko'pincha xossa, maydon emas,
# ya'ni `only()` ga berib bo'lmaydi.
SOURCES: tuple[tuple[str, str, str], ...] = (
    ("children", "Guardian", "Vasiy"),
    ("hr", "Employee", "Xodim"),
    ("accounts", "User", "Tizim hisobi"),
    ("branches", "Branch", "Filial"),
)


class Command(BaseCommand):
    help = "Formatga mos kelmaydigan telefon raqamlarini ko'rsatadi (hech narsa o'zgartirmaydi)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--tenant", help="Faqat shu tashkilot (slug)")

    def handle(self, *args: Any, **options: Any) -> None:
        from django.apps import apps as django_apps

        with platform_context():
            organizations = Organization.objects.all()
            if options.get("tenant"):
                organizations = organizations.filter(slug=options["tenant"])
            targets = list(organizations.values_list("id", "slug", "name"))

        total = 0
        for organization_id, slug, name in targets:
            found: list[str] = []
            with organization_context(organization_id):
                for app_label, model_name, label in SOURCES:
                    model = django_apps.get_model(app_label, model_name)
                    for row in model.objects.exclude(phone=""):
                        if not is_valid_phone(row.phone):
                            found.append(f"    {label}: {row} — {row.phone!r}")

            if found:
                total += len(found)
                self.stdout.write(f"\n{name} ({slug}) — {len(found)} ta:")
                for line in found:
                    self.stdout.write(line)

        self.stdout.write("")
        if total:
            self.stdout.write(
                self.style.WARNING(
                    f"Jami {total} ta noto'g'ri raqam. Ularga SMS yetib bormaydi — "
                    "ro'yxatni mudiraga bering, u ota-onadan so'raydi."
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Barcha raqamlar formatga mos."))
