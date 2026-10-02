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
        ('children', '0010_guardian_telegram'),
    ]

    operations = [
        migrations.AlterField(
            model_name='child',
            name='enrollment_status',
            field=models.CharField(choices=[('prospect', 'Nomzod'), ('active', 'Faol'), ('paused', 'Toʻxtatilgan'), ('graduated', 'Bitirgan'), ('withdrawn', 'Chiqib ketgan')], default='active', max_length=20),
        ),
        migrations.AlterField(
            model_name='child',
            name='gender',
            field=models.CharField(choices=[('male', 'Oʻgʻil bola'), ('female', 'Qiz bola')], max_length=10),
        ),
        migrations.AlterField(
            model_name='enrollment',
            name='status',
            field=models.CharField(choices=[('active', 'Faol'), ('ended', 'Tugagan'), ('transferred', 'Koʻchirilgan')], default='active', max_length=20),
        ),
    ]
