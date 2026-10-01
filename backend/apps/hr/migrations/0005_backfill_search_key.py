"""Xodimlar uchun qidiruv kalitini to'ldiradi (PLAN 2.7)."""

from __future__ import annotations

from typing import Any

from django.db import migrations


def _fill(apps: Any, organization_id: Any) -> None:
    from apps.core.translit import search_key

    Employee = apps.get_model("hr", "Employee")
    rows = []
    for employee in Employee.objects.filter(organization_id=organization_id).iterator(
        chunk_size=500
    ):
        employee.search_key = search_key(
            f"{employee.last_name} {employee.first_name} {employee.phone}"
        )
        rows.append(employee)
    Employee.objects.bulk_update(rows, ["search_key"], batch_size=500)


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
    dependencies = [("hr", "0004_search_key"), ("organizations", "0001_initial")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
