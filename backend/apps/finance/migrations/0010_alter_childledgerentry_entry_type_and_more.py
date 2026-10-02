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
        ('finance', '0009_backfill_allocations'),
    ]

    operations = [
        migrations.AlterField(
            model_name='childledgerentry',
            name='entry_type',
            field=models.CharField(choices=[('charge', 'Hisoblangan'), ('payment', 'Toʻlov'), ('discount', 'Chegirma'), ('adjustment', 'Tuzatish'), ('refund', 'Qaytarish')], max_length=15),
        ),
        migrations.AlterField(
            model_name='childledgerentry',
            name='source_type',
            field=models.CharField(choices=[('invoice', 'Hisob-faktura'), ('payment', 'Toʻlov'), ('discount', 'Chegirma'), ('manual', 'Qoʻlda')], max_length=20),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(choices=[('draft', 'Qoralama'), ('issued', 'Chiqarilgan'), ('partially_paid', 'Qisman toʻlangan'), ('paid', 'Toʻlangan'), ('overdue', 'Muddati oʻtgan'), ('cancelled', 'Bekor qilingan')], default='issued', max_length=20),
        ),
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(choices=[('cash', 'Naqd'), ('terminal', 'Terminal'), ('bank_transfer', 'Oʻtkazma'), ('online', 'Payme / Click')], max_length=20),
        ),
    ]
