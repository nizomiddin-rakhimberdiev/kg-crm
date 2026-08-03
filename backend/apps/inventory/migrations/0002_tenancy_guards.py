"""Ombor jadvallariga organization_id qo'riqchisini ulaydi."""

from django.db import migrations

from apps.core.db import attach_tenant_guards


class Migration(migrations.Migration):
    dependencies = [("inventory", "0001_initial"), ("core", "0001_tenancy_guards")]
    operations = [
        *attach_tenant_guards("warehouse"),
        *attach_tenant_guards("product_category"),
        *attach_tenant_guards("product"),
        *attach_tenant_guards("supplier"),
        *attach_tenant_guards("stock_movement"),
    ]
