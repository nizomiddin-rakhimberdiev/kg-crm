"""
Shablon tili (PLAN 3.4, ADR-16).

Mavjud shablonlar `uz` bo'lib qoladi — ular shu tilda yozilgan.
Unikal cheklov tilni ham qamraydi, ya'ni bir kod uchun o'zbekcha va
ruscha shablon yonma-yon turadi. Mavjud qatorlar bir-biriga
to'qnashmaydi: ular avval (tashkilot, kod, kanal, filial) bo'yicha
unikal edi va endi hammasi `uz` ga tushadi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('branches', '0002_branch_tenancy_guard'),
        ('notifications', '0003_test_mode_status'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='notificationtemplate',
            name='uq_template_code_channel_branch',
        ),
        migrations.RemoveConstraint(
            model_name='notificationtemplate',
            name='uq_template_code_channel_global',
        ),
        migrations.AddField(
            model_name='notificationtemplate',
            name='language',
            field=models.CharField(choices=[('uz', "O'zbekcha"), ('ru', 'Ruscha'), ('en', 'Inglizcha')], default='uz', max_length=2),
        ),
        migrations.AddConstraint(
            model_name='notificationtemplate',
            constraint=models.UniqueConstraint(fields=('organization', 'code', 'channel', 'language', 'branch'), name='uq_template_code_channel_branch'),
        ),
        migrations.AddConstraint(
            model_name='notificationtemplate',
            constraint=models.UniqueConstraint(condition=models.Q(('branch__isnull', True)), fields=('organization', 'code', 'channel', 'language'), name='uq_template_code_channel_global'),
        ),
    ]
