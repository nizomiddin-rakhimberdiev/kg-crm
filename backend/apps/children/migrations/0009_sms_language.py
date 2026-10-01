"""
Vasiyning SMS tili (PLAN 3.4).

Yangi ustun `blank=True` va sukut bo'sh satr — mavjud qatorlar
o'zgarmaydi va bo'sh qiymat "bog'chaning sukut tili" degani.
Shuning uchun u mavjud tenantlar uchun xavfsiz va qaytariladigan.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('children', '0008_medical_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='guardian',
            name='language',
            field=models.CharField(blank=True, max_length=2),
        ),
    ]
