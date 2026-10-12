"""
Eksportlar abadiy yashamasin (PLAN 11.9).

Eksport — vaqtinchalik hujjat, lekin uni hech narsa oʻchirmasdi.
Ichida esa oilalarning ismi va qarzi boʻladi.
"""

from __future__ import annotations

from datetime import timedelta
from io import StringIO
from typing import Any

import pytest
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.utils import timezone

from apps.core.tenancy import organization_context
from apps.reports.models import ExportStatus, ReportExport

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def _export(tenant: Any, *, days_old: int) -> ReportExport:
    with organization_context(tenant.organization.id):
        export = ReportExport.objects.create(
            organization=tenant.organization,
            report_type="debtors",
            status=ExportStatus.READY,
            row_count=3,
        )
        export.file.save("qarzdorlar.csv", ContentFile(b"ism,qarz\n"), save=True)
        # `created_at` — `auto_now_add`, shuning uchun to'g'ridan-to'g'ri.
        ReportExport.all_objects.filter(pk=export.pk).update(
            created_at=timezone.now() - timedelta(days=days_old)
        )
        export.refresh_from_db()
        return export


def _run(*args: str) -> str:
    out = StringIO()
    call_command("purge_old_exports", *args, stdout=out)
    return out.getvalue()


def test_dry_run_is_the_default(tenant_a: Any):
    old = _export(tenant_a, days_old=60)
    output = _run()

    assert "Hech narsa oʻchirilmadi" in output
    with organization_context(tenant_a.organization.id):
        assert ReportExport.objects.filter(pk=old.pk).exists()


def test_apply_removes_the_row_and_the_file(tenant_a: Any):
    old = _export(tenant_a, days_old=60)
    path = old.file.name
    storage = old.file.storage

    _run("--apply")

    with organization_context(tenant_a.organization.id):
        assert not ReportExport.objects.filter(pk=old.pk).exists()
    assert not storage.exists(path), "fayl ham ketishi kerak, faqat qator emas"


def test_a_recent_export_is_kept(tenant_a: Any):
    fresh = _export(tenant_a, days_old=2)
    _run("--apply")

    with organization_context(tenant_a.organization.id):
        assert ReportExport.objects.filter(pk=fresh.pk).exists()


def test_the_window_is_configurable(tenant_a: Any):
    week_old = _export(tenant_a, days_old=10)
    _run("--days", "7", "--apply")

    with organization_context(tenant_a.organization.id):
        assert not ReportExport.objects.filter(pk=week_old.pk).exists()


def test_an_orphaned_file_is_swept_too(tenant_a: Any):
    """
    Qatori yoʻq fayl — hech kim yuklab ololmaydigan, lekin diskda
    turgan maʼlumot.

    Bunday fayllar paydo boʻladi, chunki Django `queryset.delete()`
    `FileField` blobini OʻCHIRMAYDI: tashkilot tozalanganda
    (`reset_organization_data`) qatorlar ketdi, qarzdorlar roʻyxati
    esa diskda qoldi. Productionda aynan shunday boʻlgan — toʻrtta
    fayl, uchta qator.
    """
    from django.core.files.storage import default_storage

    orphan = "exports/2026/01/yetim-qarzdorlar.csv"
    default_storage.save(orphan, ContentFile(b"ism,qarz\n"))
    assert default_storage.exists(orphan)

    _run("--apply")

    assert not default_storage.exists(orphan), "yetim fayl ham ketishi kerak"


def test_a_file_with_a_live_row_is_kept(tenant_a: Any):
    """Yetimlarni supurish tirik eksportni olib ketmasin."""
    fresh = _export(tenant_a, days_old=1)
    _run("--apply")

    assert fresh.file.storage.exists(fresh.file.name)
