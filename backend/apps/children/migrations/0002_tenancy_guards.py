"""Bolalar domenidagi jadvallarga organization_id qo'riqchisini ulaydi."""

from django.db import migrations

from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):
    dependencies = [
        ("children", "0001_initial"),
        ("core", "0001_tenancy_guards"),
    ]

    operations = [
        *attach_tenant_guards("child"),
        *attach_tenant_guards("guardian"),
        *attach_tenant_guards("child_guardian"),
        *attach_tenant_guards("group"),
        *attach_tenant_guards("enrollment"),
    ]
