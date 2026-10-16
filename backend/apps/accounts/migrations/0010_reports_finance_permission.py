"""
Bosqich 13.6 (ADR-42): `reports.finance` katalog qatori.

`permission` — global katalog (docs/03 §6.2), tenant ma'lumoti emas.
Katalog odatda yangi tashkilot ro'yxatdan o'tganda sinxronlanadi; mavjud
bazada qator shu migratsiya bilan paydo bo'ladi. Hech bir mavjud rolga
berilmaydi: Moliya markazi `payroll.read` egalariga avvalgidek ochiq,
boshqaruvchiga esa ega o'zi beradi.
"""

import uuid

from django.db import migrations

CODE = "reports.finance"


def add(apps, schema_editor):  # type: ignore[no-untyped-def]
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.get_or_create(
        code=CODE,
        defaults={
            "id": uuid.uuid4(),
            "module": "reports",
            "action": "finance",
            "label": "Hisobotlar — finance",
        },
    )


def remove(apps, schema_editor):  # type: ignore[no-untyped-def]
    apps.get_model("accounts", "Permission").objects.filter(code=CODE).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_staff_telegram")]

    operations = [migrations.RunPython(add, remove)]
