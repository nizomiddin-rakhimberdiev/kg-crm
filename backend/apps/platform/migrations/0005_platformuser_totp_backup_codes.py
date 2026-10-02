"""
Vendor hisobi uchun zaxira kodlari (PLAN 5.4, ADR-24).

2FA sukut bo'yicha YOQILADI, ya'ni telefoni sinagan vendor xodimi
konsolga kira olmay qoladi. Zaxira kodlari shu holatning yagona
yechimi: serverga kirib sirni almashtirish har doim qo'l ostida
bo'lmaydi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('platform_console', '0004_lead_next_call'),
    ]

    operations = [
        migrations.AddField(
            model_name='platformuser',
            name='totp_backup_codes',
            field=models.JSONField(blank=True, default=list, editable=False),
        ),
    ]
