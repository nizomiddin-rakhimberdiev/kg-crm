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
            self.stdout.write("  (tozalaydigan narsa yoʻq)")
            return

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

        self.stdout.write("")
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
