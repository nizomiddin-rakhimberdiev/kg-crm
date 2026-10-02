"""
`invite_accepted` — taklif havolasidan birinchi parol o'rnatildi
(PLAN 5.5).

`password_reset` dan ALOHIDA hodisa: jurnalda "hisob jonlandi" degan
fakt "parolini unutdi" dan boshqa narsa, va birinchisi mijozning
boshlanish sanasi.

**Bazada hech narsa o'zgarmaydi**: `choices` Django tomonida yashaydi,
ustun turi ham, uzunligi ham o'sha. `sqlmigrate` bo'sh qaytadi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0002_login_blocked'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(choices=[('login', 'Kirish'), ('login_failed', 'Muvaffaqiyatsiz kirish'), ('login_blocked', 'Kirish bloklandi'), ('password_reset_requested', "Parol tiklash so'raldi"), ('password_reset', 'Parol tiklandi'), ('invite_accepted', 'Taklif qabul qilindi'), ('logout', 'Chiqish'), ('signup', "Ro'yxatdan o'tish"), ('password_change', "Parol o'zgardi"), ('create', 'Yaratildi'), ('update', 'Yangilandi'), ('delete', "O'chirildi")], max_length=32),
        ),
    ]
