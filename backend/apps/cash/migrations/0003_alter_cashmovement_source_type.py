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
        ('cash', '0002_backfill_history'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cashmovement',
            name='source_type',
            field=models.CharField(choices=[('payment', 'Toʻlov'), ('payment_reversal', 'Toʻlov qaytarildi'), ('expense', 'Chiqim'), ('payroll', 'Oylik maosh'), ('advance', 'Avans'), ('transfer', 'Qoplar orasida oʻtkazma'), ('opening', 'Boshlangʻich qoldiq'), ('manual', 'Qoʻlda tuzatish')], max_length=20),
        ),
    ]
