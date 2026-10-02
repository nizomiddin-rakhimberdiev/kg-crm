"""
Faqat `choices` yorliqlari (PLAN 4.1, Q11).

Apostroflar normallashtirilganda `gettext_lazy("...oʻ...")` yorliqlari
o'zgardi, va Django ularni modelning bir qismi deb biladi. Bazada
HECH NARSA o'zgarmaydi — `sqlmigrate` bo'sh (`no-op`): `choices`
Postgresda saqlanmaydi.

Nega shunday bo'lsa ham migratsiya kerak: `makemigrations --check`
darvozasi aks holda har CI'da qizarib turardi va keyingi HAQIQIY
sxema o'zgarishi shu shovqin orasida ko'rinmay ketardi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0003_expense_cash_account'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expense',
            name='status',
            field=models.CharField(choices=[('pending', 'Kutilmoqda'), ('approved', 'Tasdiqlangan'), ('rejected', 'Rad etilgan'), ('paid', 'Toʻlangan')], default='pending', max_length=12),
        ),
    ]
