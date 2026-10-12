"""
Eskirgan va yetim qolgan eksport fayllarini oʻchiradi (PLAN 11.9).

Mantiq `apps/reports/services.py:purge_old_exports()` da — bu yerda
faqat ekranga chiqarish. Sabab: oʻsha mantiq tunda Celery vazifasi
sifatida ham ishlaydi, va buyruq bilan vazifa ikki xil narsa qilsa,
ulardan qaysi biri toʻgʻri ekanini keyin hech kim ayta olmasdi.

Sukut boʻyicha **dry-run**::

    python manage.py purge_old_exports                 # 30 kun, sanaydi
    python manage.py purge_old_exports --days 7
    python manage.py purge_old_exports --apply
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.reports import services

DEFAULT_DAYS = 30


class Command(BaseCommand):
    help = "Eskirgan va yetim eksport fayllarini oʻchiradi (dry-run sukut boʻyicha)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        days = options["days"]
        apply_it = options["apply"]
        result = services.purge_old_exports(days=days, apply=apply_it)

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"\n{days} kundan eski eksportlar: {len(result['rows'])} ta")
        )
        for row in result["rows"]:
            self.stdout.write(f"  {row['created']}  {row['type']:<12} {row['file']}")
        if not result["rows"]:
            self.stdout.write("  (eskirgani yoʻq)")

        if result["orphans"]:
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"\nQatorsiz (yetim) fayllar: {len(result['orphans'])} ta"
                )
            )
            for name in result["orphans"]:
                self.stdout.write(f"  {name}")

        self.stdout.write("")
        if not result["rows"] and not result["orphans"]:
            self.stdout.write("  (tozalaydigan narsa yoʻq)")
            return

        if apply_it:
            self.stdout.write(
                self.style.SUCCESS(
                    f"OʻCHIRILDI: {result['removed_rows']} ta yozuv, "
                    f"{result['removed_files']} ta fayl"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Hech narsa oʻchirilmadi. Bajarish uchun:\n"
                    f"  python manage.py purge_old_exports --days {days} --apply"
                )
            )
