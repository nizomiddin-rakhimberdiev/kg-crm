"""`attendance_record` jadvaliga organization_id qo'riqchisini ulaydi."""

from django.db import migrations

from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0001_initial"),
        ("core", "0001_tenancy_guards"),
    ]

    operations = [*attach_tenant_guards("attendance_record")]
