"""Oylik jadvallariga organization_id qo'riqchisini ulaydi."""

from django.db import migrations

from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):
    dependencies = [("payroll", "0001_initial"), ("core", "0001_tenancy_guards")]
    operations = [*attach_tenant_guards("payroll_run"), *attach_tenant_guards("payroll_item")]
