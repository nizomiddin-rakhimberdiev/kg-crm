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
        ('hr', '0005_backfill_search_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='employment_status',
            field=models.CharField(choices=[('active', 'Ishlayapti'), ('on_leave', 'Taʼtilda'), ('terminated', 'Ishdan boʻshagan')], default='active', max_length=15),
        ),
    ]
