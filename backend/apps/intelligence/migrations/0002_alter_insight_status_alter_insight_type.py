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
        ('intelligence', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='insight',
            name='status',
            field=models.CharField(choices=[('new', 'Yangi'), ('seen', 'Koʻrilgan'), ('resolved', 'Hal qilingan'), ('dismissed', 'Rad etilgan'), ('auto_resolved', 'Oʻzi hal boʻlgan')], default='new', max_length=14),
        ),
        migrations.AlterField(
            model_name='insight',
            name='type',
            field=models.CharField(choices=[('payment_delay', 'Toʻlov kechikishi'), ('attendance_drop', 'Davomat pasayishi')], max_length=40),
        ),
    ]
