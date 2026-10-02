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
        ('subscriptions', '0003_radix_pricing'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscription',
            name='status',
            field=models.CharField(choices=[('trialing', 'Sinov davri'), ('pending_payment', 'Toʻlov kutilmoqda'), ('active', 'Faol'), ('past_due', 'Muddati oʻtgan'), ('suspended', 'Toʻxtatilgan'), ('cancelled', 'Bekor qilingan')], default='trialing', max_length=20),
        ),
        migrations.AlterField(
            model_name='subscriptioninvoice',
            name='status',
            field=models.CharField(choices=[('issued', 'Yozilgan'), ('paid', 'Toʻlangan'), ('overdue', 'Muddati oʻtgan'), ('cancelled', 'Bekor qilingan')], default='issued', max_length=20),
        ),
        migrations.AlterField(
            model_name='subscriptionpayment',
            name='method',
            field=models.CharField(choices=[('bank_transfer', 'Bank oʻtkazmasi'), ('card', 'Karta'), ('cash', 'Naqd')], default='bank_transfer', max_length=20),
        ),
        migrations.AlterField(
            model_name='usagesnapshot',
            name='measurement_method',
            field=models.CharField(choices=[('daily_peak', 'Kunlik eng yuqori'), ('manual_adjustment', 'Qoʻlda tuzatish')], default='daily_peak', max_length=30),
        ),
    ]
