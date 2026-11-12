"""
Audit 2026-11-12 (H10): ruxsat yorliqlari o'zbek apostrofi bilan.

`permission` — global katalog (docs/03 §6.2), tenant ma'lumoti emas.
Yorliq katalog yozilganda `PERMISSION_LABELS` dan olinadi, ya'ni
"To'lovlar" (ASCII) bazada qolgan edi va rollar sahifasida shunday
ko'rinardi. Bu yerda faqat YORLIQ yangilanadi — kod va bog'lanishlar
o'zgarmaydi.
"""

from __future__ import annotations

from typing import Any

from django.db import migrations


def relabel(apps: Any, schema_editor: Any) -> None:
    from apps.accounts.constants import PERMISSION_LABELS

    Permission = apps.get_model("accounts", "Permission")
    for permission in Permission.objects.all():
        module_label = PERMISSION_LABELS.get(permission.module)
        if not module_label:
            continue
        label = f"{module_label} — {permission.action}"
        if permission.label != label:
            permission.label = label
            permission.save(update_fields=["label"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0011_tariffs_and_discounts_modules")]

    operations = [migrations.RunPython(relabel, migrations.RunPython.noop)]
