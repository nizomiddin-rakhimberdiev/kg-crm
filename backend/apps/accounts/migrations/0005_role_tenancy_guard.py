"""`role` jadvaliga organization_id o'zgarmaslik trigger'ini ulaydi."""

from django.db import migrations

from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_user_branch_permission_uq_permission_module_action_and_more"),
        ("core", "0001_tenancy_guards"),
    ]

    operations = [*attach_tenant_guards("role")]
