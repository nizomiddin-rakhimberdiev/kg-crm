"""
Tenant chegarasini bazada qo'riqlovchi trigger funksiyasi (docs/03 §24).

Nega bu ilova qatlamida emas, bazada:
D1 — "Integrity is enforced in the database, not just the app". Bu qoida
xato, shell sessiyasi yoki ma'lumot tuzatuvchi skript service qatlamini
chetlab o'tganda ham amal qilishi kerak. Aynan o'sha holatlar xavfli.

Trigger'ning o'zi shu yerda bir marta yaratiladi; har bir tenant-scoped
jadval uni `attach_tenant_guards()` yordamchisi orqali biriktiradi.
"""

from django.db import migrations

FORWARD = """
CREATE OR REPLACE FUNCTION kg_guard_organization_immutable()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.organization_id IS DISTINCT FROM NEW.organization_id THEN
        RAISE EXCEPTION
            'organization_id o''zgarmas: % jadvalidagi % qatorini boshqa '
            'tashkilotga ko''chirish mumkin emas (ADR-9)',
            TG_TABLE_NAME, OLD.id
        USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

REVERSE = "DROP FUNCTION IF EXISTS kg_guard_organization_immutable();"


class Migration(migrations.Migration):
    initial = True

    dependencies: list[tuple[str, str]] = []

    operations = [
        migrations.RunSQL(sql=FORWARD, reverse_sql=REVERSE),
    ]
