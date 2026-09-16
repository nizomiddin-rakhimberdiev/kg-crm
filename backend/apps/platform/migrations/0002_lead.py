"""Platforma darajasidagi public zayavkalar.

Bu jadval ataylab tenant/RLS ro'yxatiga kirmaydi: lead hali mijoz emas.
"""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("platform_console", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Lead",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=150)),
                ("phone", models.CharField(db_index=True, max_length=13)),
                ("kindergarten_name", models.CharField(max_length=200)),
                ("children_count", models.PositiveSmallIntegerField()),
                ("city", models.CharField(max_length=120)),
                ("message", models.TextField(blank=True, max_length=1000)),
                ("language", models.CharField(choices=[("uz", "O'zbekcha"), ("ru", "Русский")], max_length=2)),
                ("source", models.CharField(default="website", max_length=40)),
                ("status", models.CharField(choices=[("new", "Yangi"), ("contacted", "Bog'lanildi"), ("qualified", "Mos keladi"), ("closed", "Yopildi")], default="new", max_length=20)),
                ("consented_at", models.DateTimeField()),
                ("privacy_policy_version", models.CharField(max_length=32)),
                ("submission_id", models.UUIDField(editable=False, unique=True)),
            ],
            options={"db_table": "platform_lead", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="lead",
            index=models.Index(fields=["status", "-created_at"], name="ix_lead_status_created"),
        ),
        migrations.AddIndex(
            model_name="lead",
            index=models.Index(fields=["phone", "-created_at"], name="ix_lead_phone_created"),
        ),
        migrations.AddConstraint(
            model_name="lead",
            constraint=models.CheckConstraint(
                condition=models.Q(("children_count__gte", 1), ("children_count__lte", 10000)),
                name="ck_lead_children_count",
            ),
        ),
    ]
