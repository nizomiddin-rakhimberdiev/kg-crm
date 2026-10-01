"""
Mavjud yozuvlar uchun qidiruv kalitini to'ldiradi (PLAN 2.7).

Ustun qo'shilishi bilan u bo'sh bo'ladi, ya'ni migratsiyadan keyin
MAVJUD bolalar qidiruvda topilmay qolardi. Bu eng yomon turdagi
regressiya: hech qanday xato yo'q, shunchaki ro'yxat bo'sh.

RLS ostida ishlaydi — har bir tashkilot alohida aylanib chiqiladi
(`cash/0002_backfill_history` bilan bir xil naqsh).
"""

from __future__ import annotations

from typing import Any

from django.db import migrations


def _fill(apps: Any, organization_id: Any) -> None:
    from apps.core.translit import search_key

    Child = apps.get_model("children", "Child")
    Guardian = apps.get_model("children", "Guardian")

    rows = []
    for child in Child.objects.filter(organization_id=organization_id).iterator(chunk_size=500):
        child.search_key = search_key(
            f"{child.last_name} {child.first_name} {child.middle_name}"
        )
        rows.append(child)
    Child.objects.bulk_update(rows, ["search_key"], batch_size=500)

    rows = []
    for guardian in Guardian.objects.filter(organization_id=organization_id).iterator(
        chunk_size=500
    ):
        guardian.search_key = search_key(
            f"{guardian.last_name} {guardian.first_name} {guardian.phone}"
        )
        rows.append(guardian)
    Guardian.objects.bulk_update(rows, ["search_key"], batch_size=500)


def backfill(apps: Any, schema_editor: Any) -> None:
    connection = schema_editor.connection
    Organization = apps.get_model("organizations", "Organization")

    if connection.vendor != "postgresql":  # pragma: no cover
        for organization_id in Organization.objects.values_list("id", flat=True):
            _fill(apps, organization_id)
        return

    from apps.core.rls import (
        apply_tenant_setting,
        clear_tenant_setting,
        disable_platform_mode,
        enable_platform_mode,
    )

    enable_platform_mode()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM organization")
            organization_ids = [row[0] for row in cursor.fetchall()]
    finally:
        disable_platform_mode()

    try:
        for organization_id in organization_ids:
            apply_tenant_setting(organization_id)
            _fill(apps, organization_id)
    finally:
        clear_tenant_setting()


class Migration(migrations.Migration):
    dependencies = [
        ("children", "0006_search_key"),
        ("organizations", "0001_initial"),
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
