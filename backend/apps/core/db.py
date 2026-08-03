"""
Migratsiyalar uchun tenant qo'riqchilarini biriktirish yordamchisi.

Har bir yangi tenant-scoped jadval o'z migratsiyasida shuni chaqiradi::

    from apps.core.db import attach_tenant_guards

    operations = [
        migrations.CreateModel(...),
        *attach_tenant_guards("child"),
    ]

Shunday qilib "organization_id o'zgarmas" qoidasi har bir jadvalda bir xil
usulda, unutilmasdan qo'llanadi (docs/03 §22).
"""

from __future__ import annotations

from django.db import migrations

__all__ = ["attach_tenant_guards"]


def attach_tenant_guards(table_name: str) -> list[migrations.RunSQL]:
    """`table_name` jadvaliga organization_id immutability trigger'ini ulaydi."""
    trigger = f"trg_{table_name}_organization_immutable"
    # Jadval nomi qo'shtirnoqqa olinadi: `user` kabi nomlar Postgres'da
    # zahiralangan so'z va tirnoqsiz sintaksis xatosi beradi.
    quoted = f'"{table_name}"'
    return [
        migrations.RunSQL(
            sql=(
                f"CREATE TRIGGER {trigger} "
                f"BEFORE UPDATE ON {quoted} "
                f"FOR EACH ROW EXECUTE FUNCTION kg_guard_organization_immutable();"
            ),
            reverse_sql=f"DROP TRIGGER IF EXISTS {trigger} ON {quoted};",
        )
    ]
