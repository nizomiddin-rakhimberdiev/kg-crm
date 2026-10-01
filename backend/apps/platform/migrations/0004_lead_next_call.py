"""
Keyingi qo'ng'iroq sanasi (PLAN 3.6).

`null=True` — mavjud arizalar o'zgarmaydi va "reja yo'q" degani.
Indeks "bugun kimga qo'ng'iroq qilish kerak?" so'rovi uchun.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('platform_console', '0003_lead_note_status_changed_en'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='next_call_at',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
    ]
