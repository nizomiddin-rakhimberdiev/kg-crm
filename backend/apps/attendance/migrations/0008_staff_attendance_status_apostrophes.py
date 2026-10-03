"""
Choices-only: staff-attendance status labels normalised to the Uzbek
apostrophes (Q11) after merging main. No SQL — `sqlmigrate` is empty.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0007_merge_20261003_0746'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staffattendance',
            name='status',
            field=models.CharField(choices=[('present', 'Keldi'), ('absent', 'Kelmadi'), ('sick', 'Kasal'), ('leave', 'Taʼtilda')], max_length=10),
        ),
    ]
