"""
Yangi audit hodisalari (PLAN 5.3, 5.2).

`login_blocked` — xato urinishdan ALOHIDA hodisa: u hujumning belgisi
va jurnaldan "qachon boshlandi, qancha davom etdi" degan savolga
javob chiqishi kerak. Qolgan ikkitasi parol tiklash oqimi uchun.

Ustun 20 → 32 belgi: eng uzun qiymat 24 ta. Mavjud qatorlarga
tegilmaydi (`ALTER TYPE` faqat kengaytiradi).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(choices=[('login', 'Kirish'), ('login_failed', 'Muvaffaqiyatsiz kirish'), ('login_blocked', 'Kirish bloklandi'), ('password_reset_requested', "Parol tiklash so'raldi"), ('password_reset', 'Parol tiklandi'), ('logout', 'Chiqish'), ('signup', "Ro'yxatdan o'tish"), ('password_change', "Parol o'zgardi"), ('create', 'Yaratildi'), ('update', 'Yangilandi'), ('delete', "O'chirildi")], max_length=32),
        ),
    ]
