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
        ('notifications', '0006_backfill_template_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationtemplate',
            name='code',
            field=models.CharField(choices=[('payment_received', 'Toʻlov qabul qilindi'), ('debt_reminder', 'Qarz eslatmasi'), ('absence_notice', 'Kelmagani haqida'), ('custom', 'Erkin xabar')], max_length=50),
        ),
        migrations.AlterField(
            model_name='notificationtemplate',
            name='language',
            field=models.CharField(choices=[('uz', 'Oʻzbekcha'), ('ru', 'Ruscha'), ('en', 'Inglizcha')], default='uz', max_length=2),
        ),
    ]
