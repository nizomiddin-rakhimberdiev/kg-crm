"""`user` jadvaliga organization_id o'zgarmaslik trigger'ini ulaydi."""

from django.db import migrations

from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("core", "0001_tenancy_guards"),
    ]

    operations = [*attach_tenant_guards("user")]
