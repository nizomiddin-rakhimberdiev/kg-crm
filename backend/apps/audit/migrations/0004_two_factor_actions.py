"""
2FA hodisalari (PLAN 5.4, ADR-24).

Yoqish va o'chirish — hisob xavfsizligining o'zgarishi; zaxira kodining
ishlatilishi esa "telefonim yo'q" holatining belgisi va kodlar
tugayotganini ko'rsatadi.

**Bazada hech narsa o'zgarmaydi**: `choices` Django tomonida yashaydi,
ustun turi ham, uzunligi ham o'sha (`two_factor_codes_renewed` — 24
belgi, chegara 32). `sqlmigrate` bo'sh qaytadi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0003_invite_accepted_action'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(choices=[('login', 'Kirish'), ('login_failed', 'Muvaffaqiyatsiz kirish'), ('login_blocked', 'Kirish bloklandi'), ('password_reset_requested', "Parol tiklash so'raldi"), ('password_reset', 'Parol tiklandi'), ('invite_accepted', 'Taklif qabul qilindi'), ('two_factor_enabled', '2FA yoqildi'), ('two_factor_disabled', "2FA o'chirildi"), ('two_factor_backup_used', 'Zaxira kodi ishlatildi'), ('two_factor_codes_renewed', 'Zaxira kodlari yangilandi'), ('logout', 'Chiqish'), ('signup', "Ro'yxatdan o'tish"), ('password_change', "Parol o'zgardi"), ('create', 'Yaratildi'), ('update', 'Yangilandi'), ('delete', "O'chirildi")], max_length=32),
        ),
    ]
