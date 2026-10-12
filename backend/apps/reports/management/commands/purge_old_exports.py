"""
Eskirgan eksport fayllarini oʻchiradi.

**Nega kerak.** Eksport — vaqtinchalik hujjat: foydalanuvchi uni
yuklab oladi va unutadi. Lekin uni hech narsa oʻchirmasdi, yaʼni
`debtors-20260923-1001.csv` — oilalarning ismi va qarzi bilan —
serverda cheksiz yotaverardi.

Bu shunchaki joy masalasi emas edi. Tuzatilgunga qadar `/media/`
nginx orqali **autentifikatsiyasiz** berilardi, eksport nomlari esa
UUID emas — sana va daqiqani sanab chiqish yetarli boʻlardi. Teshik
yopildi (ruxsat roʻyxati, PLAN 11.5), lekin eski fayllar qolgani
qoldi: ular ochiq boʻlgan davrda koʻchirilgan boʻlishi mumkin, va
ularni saqlab turishning sababi yoʻq — har qanday eksport bir
bosishda qaytadan yasaladi.

Sukut boʻyicha **dry-run**. Fayl ham, qator ham ketadi: yoʻqolgan
faylga ishora qiladigan `ready` qator foydalanuvchini "yuklab olish"
tugmasi jimgina ishlamaydigan holatga olib borardi.

Ishlatish::

    python manage.py purge_old_exports                 # dry-run, 30 kun
    python manage.py purge_old_exports --days 7
    python manage.py purge_old_exports --apply
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.tenancy import organization_context, platform_context
from apps.organizations.models import Organization
from apps.reports.models import ReportExport

DEFAULT_DAYS = 30


class Command(BaseCommand):
    help = "Eskirgan eksport fayllarini oʻchiradi (dry-run sukut boʻyicha)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        days = options["days"]
        apply_it = options["apply"]
        cutoff = timezone.now() - timedelta(days=days)

        # Tashkilotlar roʻyxati platforma rejimida, tozalash esa HAR
        # BIRINING oʻz kontekstida.
        #
        # `report_export` — operatsion jadval, yaʼni unda platforma
        # uchun chiqish yoʻq (ADR-10): `platform_context()` ichida u
        # BOʻSH koʻrinadi. Birinchi variant aynan shunday yozilgan edi
        # va "tozalaydigan narsa yoʻq" deb chiqardi — fayllar esa
        # joyida qolaverardi. Jim muvaffaqiyat eng yomon turdagi
        # nosozlik.
        with platform_context():
            organizations = list(Organization.objects.all())

        stale: list[Any] = []
        for organization in organizations:
            with organization_context(organization.id):
                stale.extend(ReportExport.objects.filter(created_at__lt=cutoff))

        self.stdout.write(
            self.style.MIGRATE_HEADING(f"\n{days} kundan eski eksportlar: {len(stale)} ta")
        )
        if not stale:
            self.stdout.write("  (eskirgani yoʻq)")

        # Yetimlar ALOHIDA savol: eskirgan qator boʻlmasa ham ular
        # boʻlishi mumkin. Dastlab bu yerda erta `return` turgan edi va
        # tozalash ularga umuman yetib bormasdi.
        removed_files = 0
        for export in stale:
            name = export.file.name or "—"
            self.stdout.write(f"  {export.created_at:%Y-%m-%d}  {export.report_type:<12} {name}")
            if not apply_it:
                continue
            with organization_context(export.organization_id):
                if export.file:
                    # Fayl yoʻq boʻlsa ham qator ketadi — tozalash
                    # yarim qolmasin.
                    export.file.delete(save=False)
                    removed_files += 1
                export.delete()

        orphans = self._orphans(organizations)
        if orphans:
            self.stdout.write(
                self.style.MIGRATE_HEADING(f"\nQatorsiz (yetim) fayllar: {len(orphans)} ta")
            )
            for name in orphans:
                self.stdout.write(f"  {name}")
            if apply_it:
                for name in orphans:
                    default_storage.delete(name)
                removed_files += len(orphans)

        self.stdout.write("")
        if not stale and not orphans:
            self.stdout.write("  (tozalaydigan narsa yoʻq)")
            return

        if apply_it:
            self.stdout.write(
                self.style.SUCCESS(f"OʻCHIRILDI: {len(stale)} ta yozuv, {removed_files} ta fayl")
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Hech narsa oʻchirilmadi. Bajarish uchun:\n"
                    f"  python manage.py purge_old_exports --days {days} --apply"
                )
            )

    @staticmethod
    def _orphans(organizations: list[Any]) -> list[str]:
        """
        `exports/` ichidagi, birorta qator ishora qilmaydigan fayllar.

        Ular paydo boʻladi, chunki Django `queryset.delete()`
        `FileField` blobini OʻCHIRMAYDI: tashkilot tozalanganda
        qatorlar ketadi, fayl esa diskda qoladi. Bunday fayl hech kim
        yuklab ololmaydigan maʼlumot — lekin u maʼlumotligicha
        qolaveradi, va eksport ichida oilalarning ismi va qarzi
        boʻladi.
        """
        known: set[str] = set()
        for organization in organizations:
            with organization_context(organization.id):
                known.update(
                    name for name in ReportExport.objects.values_list("file", flat=True) if name
                )

        found: list[str] = []
        stack = ["exports"]
        while stack:
            folder = stack.pop()
            try:
                subfolders, files = default_storage.listdir(folder)
            except (FileNotFoundError, NotImplementedError):
                continue
            stack.extend(f"{folder}/{sub}" for sub in subfolders)
            found.extend(f"{folder}/{name}" for name in files if f"{folder}/{name}" not in known)
        return sorted(found)
