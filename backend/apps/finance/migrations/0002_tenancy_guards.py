"""Moliya jadvallariga organization_id qo'riqchisini ulaydi."""

from django.db import migrations

from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0001_initial"),
        ("core", "0001_tenancy_guards"),
    ]

    operations = [
        *attach_tenant_guards("tariff_plan"),
        *attach_tenant_guards("discount"),
        *attach_tenant_guards("invoice"),
        *attach_tenant_guards("child_ledger_entry"),
    ]
