"""
Audit 2026-11-12 (C1): `tariffs` va `discounts` — o'z modullari.

Ilgari ikkalasi `payments` ruxsati bilan ochilardi. Endi alohida, va bu
migratsiyasiz mavjud bog'chalarda tarif ekrani HAMMAGA yopilib qolardi.
Shuning uchun:

* katalogga `tariffs.*` va `discounts.*` qatorlari qo'shiladi;
* tizim rollari `org_owner` va `director` — shablondagidek to'liq;
* `payments.read` i bor har qanday boshqa rol (kassir, menejer, bog'cha
  o'zi yasagan rollar) — faqat o'qish. Yozishni ega o'zi beradi.

RLS ostida — har bir tashkilot alohida (`children/0007` naqshi).
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import migrations

MODULES = ("tariffs", "discounts")
ACTIONS = ("read", "create", "update", "delete", "export", "approve")
LABELS = {"tariffs": "Tariflar", "discounts": "Imtiyozlar"}
FULL_ROLES = ("org_owner", "director")


def _catalog(apps: Any) -> dict[str, Any]:
    Permission = apps.get_model("accounts", "Permission")
    for module in MODULES:
        for action in ACTIONS:
            Permission.objects.get_or_create(
                code=f"{module}.{action}",
                defaults={
                    "id": uuid.uuid4(),
                    "module": module,
                    "action": action,
                    "label": f"{LABELS[module]} — {action}",
                },
            )
    return {p.code: p for p in Permission.objects.filter(module__in=MODULES)}


def grant(apps: Any, organization_id: Any) -> None:
    """Bitta tashkilotning rollariga yangi modullarni beradi (idempotent)."""
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")
    permissions = _catalog(apps)

    for role in Role.objects.filter(organization_id=organization_id):
        if role.code in FULL_ROLES and role.is_system:
            wanted = set(permissions)
        elif RolePermission.objects.filter(role=role, permission__code="payments.read").exists():
            wanted = {f"{module}.read" for module in MODULES}
        else:
            continue
        current = set(
            RolePermission.objects.filter(role=role, permission__module__in=MODULES).values_list(
                "permission__code", flat=True
            )
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(id=uuid.uuid4(), role=role, permission=permissions[code])
                for code in sorted(wanted - current)
            ]
        )


def forwards(apps: Any, schema_editor: Any) -> None:
    connection = schema_editor.connection
    Organization = apps.get_model("organizations", "Organization")
    _catalog(apps)

    if connection.vendor != "postgresql":  # pragma: no cover
        for organization_id in Organization.objects.values_list("id", flat=True):
            grant(apps, organization_id)
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
            grant(apps, organization_id)
    finally:
        clear_tenant_setting()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_reports_finance_permission"),
        ("organizations", "0001_initial"),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
