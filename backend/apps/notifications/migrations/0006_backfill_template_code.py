"""
Mavjud xabarlarga turini yozadi (PLAN 3.7).

Ustun qo'shilishi bilan u bo'sh bo'ladi, ya'ni migratsiyadan keyin
"bu vasiyga bugun qarz eslatmasi ketganmi?" degan savol MAVJUD
qatorlar bo'yicha javobsiz qolardi — va kunlik chegara shu kuni
ishlamasdi: ota-ona ikkinchi eslatmani olardi.

Tur shablon qatoridan ko'chiriladi; shabloni yo'q eski qatorlar
bo'sh qoladi (ular uchun manba yo'q — taxmin qilish noto'g'ri
ma'lumot yozish bo'lardi).

RLS ostida ishlaydi — har bir tashkilot alohida aylanib chiqiladi
(`children/0007_backfill_search_key` bilan bir xil naqsh).
"""

from __future__ import annotations

from typing import Any

from django.db import migrations


def _fill(apps: Any, organization_id: Any) -> None:
    Notification = apps.get_model("notifications", "Notification")

    rows = []
    queryset = Notification.objects.filter(
        organization_id=organization_id,
        template_code="",
        template__isnull=False,
    ).select_related("template")
    for notification in queryset.iterator(chunk_size=500):
        notification.template_code = notification.template.code
        rows.append(notification)
        if len(rows) >= 500:
            Notification.objects.bulk_update(rows, ["template_code"], batch_size=500)
            rows = []
    if rows:
        Notification.objects.bulk_update(rows, ["template_code"], batch_size=500)


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
        ("notifications", "0005_notification_kind"),
        ("organizations", "0001_initial"),
    ]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
