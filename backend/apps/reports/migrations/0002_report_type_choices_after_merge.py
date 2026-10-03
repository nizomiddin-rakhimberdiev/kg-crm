"""
Choices-only migration after merging main: report-type labels from both
lines. Django keeps `choices` in Python, so `sqlmigrate` is empty.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportexport',
            name='report_type',
            field=models.CharField(choices=[('revenue', 'revenue'), ('expenses', 'expenses'), ('payroll', 'payroll'), ('attendance', 'attendance'), ('debtors', 'debtors'), ('profit-loss', 'profit-loss'), ('staff-attendance', 'staff-attendance')], max_length=30),
        ),
    ]
