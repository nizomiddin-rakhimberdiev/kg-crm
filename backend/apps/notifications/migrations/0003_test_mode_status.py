"""
`test_mode` holati (PLAN 3.2).

Faqat `choices` o'zgaradi — bazada ustun turi ham, ma'lumot ham
tegilmaydi. Shuning uchun u mavjud tenantlar uchun xavfsiz va teskari
yo'nalishda ham shunchaki eski ro'yxatni qaytaradi.

Nega kerak: auditda console provayder xabarni "Yuborildi" deb
belgilardi. Mudira jurnalga qarab xabar yetib borgan deb o'ylardi,
aslida esa hech qayerga ketmagan edi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_tenancy_guards"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Navbatda"),
                    ("sent", "Yuborildi"),
                    ("delivered", "Yetkazildi"),
                    ("failed", "Muvaffaqiyatsiz"),
                    ("cancelled", "Bekor qilindi"),
                    ("test_mode", "Test rejimi"),
                ],
                default="queued",
                max_length=12,
            ),
        ),
    ]
