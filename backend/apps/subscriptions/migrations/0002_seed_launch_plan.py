"""
Ishga tushirish planini seed qiladi (docs/01 §4.2).

Migratsiya orqali, admin panelidan qo'lda emas: yangi o'rnatishda plan
bo'lmasa, birinchi ro'yxatdan o'tgan mijoz sinov obunasini ham
ololmaydi — ya'ni tizim jimgina ishlamay qoladi.

Narx O'ZGARTIRILMAYDI, faqat yangi versiya qo'shiladi: mavjud obunalar
o'zi sotib olgan versiyaga ishora qilib qoladi (docs/03 §20.1).
"""

from datetime import date
from decimal import Decimal

from django.db import migrations

LAUNCH_PLAN = {
    "code": "standard",
    "name": "Standart",
    "currency": "UZS",
    "base_price": Decimal("500000.00"),
    "included_children": 50,
    "overage_step_children": 10,
    "overage_step_price": Decimal("80000.00"),
    "valid_from": date(2026, 1, 1),
    "valid_to": None,
}


def seed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    SubscriptionPlan.objects.get_or_create(
        code=LAUNCH_PLAN["code"],
        valid_from=LAUNCH_PLAN["valid_from"],
        defaults=LAUNCH_PLAN,
    )


def unseed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscriptions", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(
        code=LAUNCH_PLAN["code"], valid_from=LAUNCH_PLAN["valid_from"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("subscriptions", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
