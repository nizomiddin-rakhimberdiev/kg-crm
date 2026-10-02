"""
Mijoz tomonida ikki bosqichli tasdiqlash (PLAN 5.4, ADR-24).

Uchta ustun, hammasi bo'sh qiymat bilan: mavjud hisoblarda hech
narsa o'zgarmaydi va hech kim kirishdan qolmaydi. 2FA — har bir
foydalanuvchining O'Z qarori (`/auth/2fa/setup`), majburiy emas.

`totp_confirmed_at` sirdan ALOHIDA: sir yaratilgani 2FA yoqilgani
degani emas — odam QR'ni ko'rib ilovaga qo'shmasa, hisob keyingi
kirishda qulflanib qolardi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_user_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='totp_backup_codes',
            field=models.JSONField(blank=True, default=list, editable=False),
        ),
        migrations.AddField(
            model_name='user',
            name='totp_confirmed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='totp_secret',
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
