"""
`memories.*` ruxsatlarini MAVJUD tashkilotlarning tizim rollariga qo'shadi.

Yangi tashkilot ro'yxatdan o'tganda `seed_system_roles` buni o'zi qiladi;
mavjudlarda esa modul paydo bo'lgan zahoti hech kimda ruxsat bo'lmaydi
(deny-by-default) va bo'lim "ishlamayapti" ko'rinadi.

Faqat `memories.*` qo'shiladi, boshqa ruxsatlarga TEGILMAYDI: egasi
tizim roldan ataylab olib tashlagan ruxsat qaytib kelmasligi kerak.
Servisni import qilmaymiz — kelajakda o'zgargan kod bu migratsiya
ma'nosini o'zgartirmasin. RLS ostida har bir tashkilot alohida aylanadi.
"""

from django.db import migrations

ACTIONS = ("read", "create", "update", "delete", "export", "approve")
FULL = ACTIONS
WRITE = ("read", "create", "update")
GRANTS = {"org_owner": FULL, "director": FULL, "manager": WRITE}


def grant(apps, schema_editor):
    from apps.core.tenancy import organization_context, platform_context

    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")
    Organization = apps.get_model("organizations", "Organization")

    perms = {}
    for action in ACTIONS:
        perm, _ = Permission.objects.get_or_create(
            code=f"memories.{action}",
            defaults={"module": "memories", "action": action, "label": f"Radix AI (xotira va kamera) — {action}"},
        )
        perms[action] = perm

    with platform_context():
        org_ids = list(Organization.objects.values_list("id", flat=True))
    for org_id in org_ids:
        with organization_context(org_id):
            for code, actions in GRANTS.items():
                for role in Role.objects.filter(organization_id=org_id, code=code, is_system=True):
                    for action in actions:
                        RolePermission.objects.get_or_create(role=role, permission=perms[action])


class Migration(migrations.Migration):
    dependencies = [
        ("memories", "0001_initial"),
        ("accounts", "0006_user_photo"),
        ("organizations", "0001_initial"),
    ]
    operations = [migrations.RunPython(grant, migrations.RunPython.noop)]
