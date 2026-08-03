"""Chiqim jadvallariga organization_id qo'riqchisini ulaydi."""

from django.db import migrations

from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):
    dependencies = [("expenses", "0001_initial"), ("core", "0001_tenancy_guards")]
    operations = [*attach_tenant_guards("expense_category"), *attach_tenant_guards("expense")]
