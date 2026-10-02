"""
Bog'chaning logotipi (PLAN 4.6).

Ustun bo'sh qiymat bilan qo'shiladi — mavjud tashkilotlar o'zgarmaydi
va bo'sh logotip "bosh harfni ko'rsat" degani. Teskari yo'nalishda
ustun olib tashlanadi; yuklangan fayllar media papkasida qoladi
(ularni o'chirish migratsiyaning ishi emas).
"""

import apps.organizations.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='logo',
            field=models.ImageField(blank=True, upload_to=apps.organizations.models.organization_logo_path),
        ),
    ]
