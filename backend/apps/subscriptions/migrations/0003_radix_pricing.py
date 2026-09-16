"""Radix CRM narxlarining yangi, tarixni buzmaydigan plan versiyasi."""

from datetime import date
from decimal import Decimal

from django.db import migrations

EFFECTIVE_FROM = date(2026, 9, 14)
PREVIOUS_PLAN_START = date(2026, 1, 1)


def apply_radix_pricing(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    # Oldingi plan FK bilan mavjud subscription/invoice tarixiga bog'langan;
    # uni o'chirmaymiz va narxini joyida tahrirlamaymiz.
    SubscriptionPlan.objects.filter(code="standard", valid_from=PREVIOUS_PLAN_START).update(
        valid_to=date(2026, 9, 13)
    )
    SubscriptionPlan.objects.get_or_create(
        code="standard",
        valid_from=EFFECTIVE_FROM,
        defaults={
            "name": "Standart — Radix CRM",
            "currency": "UZS",
            "base_price": Decimal("400000.00"),
            "included_children": 50,
            "overage_step_children": 10,
            "overage_step_price": Decimal("50000.00"),
            "valid_to": None,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0002_seed_launch_plan")]
    operations = [migrations.RunPython(apply_radix_pricing, migrations.RunPython.noop)]
