"""
Merge migration: joins main's `0004_child_monthly_fee` (individual price,
hotfix feb68c0) with the big-update children line (0004…0011). No schema
change of its own.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('children', '0004_child_monthly_fee'),
        ('children', '0011_alter_child_enrollment_status_alter_child_gender_and_more'),
    ]

    operations = [
    ]
