"""
Tushunarsiz sukut toifa nomlarini yangilaydi (audit, 2026-10-21).

**Nima uchun.** Mustaqil auditda chiqim toifalari orasida "Naqd qism",
"Karta qism" va "Target" uchrab, "nimani anglatishi noma'lum" deb
belgilandi. Yangi filiallar endi tushunarli nom oladi
(`DEFAULT_CATEGORIES`), lekin toifalar HAR BIR filialda ma'lumot — ular
o'z-o'zidan o'zgarmaydi.

**Nima qiladi.** Faqat o'sha eski sukut nomini HALI SAQLAB TURGAN va
kutilgan ota-toifasi ostidagi qatorning nomini o'zgartiradi. Bog'cha
toifani o'zi qayta nomlagan bo'lsa — tegmaydi; nom bir xil bo'lib,
lekin boshqa ota-toifada bo'lsa — tegmaydi. Chiqimlar toifaga `id`
bilan bog'langan, ya'ni tarix va hisobotlar o'zgarmaydi.

**Xavfsizlik:** sukut bo'yicha dry-run; takror ishga tushirish xavfsiz.

Ishlatish::

    python manage.py rename_default_categories                 # faqat ko'rsatadi
    python manage.py rename_default_categories --slug orientalkinderland
    python manage.py rename_default_categories --apply
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context
from apps.expenses.models import ExpenseCategory

#: (ota-toifa, eski nom) → yangi nom.
RENAMES: dict[tuple[str, str], str] = {
    ("Ish haqi", "Naqd qism"): "Naqd berilgan oylik",
    ("Ish haqi", "Karta qism"): "Bankka oʻtkazilgan oylik",
    ("Marketing", "Target"): "Maqsadli reklama (target)",
}


class Command(BaseCommand):
    help = "Tushunarsiz sukut chiqim toifalarini qayta nomlaydi (sukut: dry-run)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", help="Faqat shu tashkilot (sukut: hammasi).")
        parser.add_argument(
            "--apply", action="store_true", help="Haqiqatan yozish. Usiz — faqat hisobot."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        apply: bool = options["apply"]
        from apps.organizations.models import Organization

        with platform_context():
            orgs = Organization.objects.order_by("slug")
            if options["slug"]:
                orgs = orgs.filter(slug=options["slug"])
                if not orgs.exists():
                    raise CommandError(f"Tashkilot topilmadi: {options['slug']}")
            targets = list(orgs.values_list("id", "slug"))

        self.stdout.write(
            "Rejim: " + ("YOZILADI" if apply else "DRY-RUN — hech narsa yozilmaydi") + "\n"
        )
        total = 0
        for org_id, slug in targets:
            with organization_context(org_id), transaction.atomic():
                for (parent_name, old), new in RENAMES.items():
                    rows = list(
                        ExpenseCategory.objects.filter(
                            name=old, parent__name=parent_name
                        ).select_related("parent", "branch")
                    )
                    for row in rows:
                        total += 1
                        self.stdout.write(
                            f"  {slug} · {row.branch.name}: «{parent_name} → {old}» → «{new}»"
                        )
                        if apply:
                            row.name = new
                            row.save(update_fields=["name"])
        self.stdout.write(
            self.style.SUCCESS(f"\n{total} ta toifa " + ("yangilandi." if apply else "topildi."))
        )
