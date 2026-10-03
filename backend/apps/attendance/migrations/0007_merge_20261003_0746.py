"""
Merge migration: joins main's `0006_staff_attendance` (hotfix 11da61a)
with big-update's `0006_alter_absenceclaim_kind`. No schema change of
its own.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0006_alter_absenceclaim_kind'),
        ('attendance', '0006_staff_attendance'),
    ]

    operations = [
    ]
