"""
Vasiyning Telegram bog'lanishi (PLAN 3.7, ADR-23).

Uchta yangi ustun ham bo'sh qiymat bilan qo'shiladi — mavjud qatorlar
o'zgarmaydi va "ulanmagan" degani. Unikal cheklovlar qisman
(`<> ''`), ya'ni bo'sh qiymatlar bir-biriga to'qnashmaydi.

Teskari yo'nalish: ustunlar olib tashlanadi. Ulangan suhbatlar
yo'qoladi va ota-onalar qayta ulanishi kerak bo'ladi — shuning uchun
bu migratsiyani orqaga qaytarishdan oldin `telegram_chat_id` larni
eksport qilib oling.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('branches', '0002_branch_tenancy_guard'),
        ('children', '0009_sms_language'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='guardian',
            name='telegram_chat_id',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='guardian',
            name='telegram_code',
            field=models.CharField(blank=True, max_length=48),
        ),
        migrations.AddField(
            model_name='guardian',
            name='telegram_linked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name='guardian',
            constraint=models.UniqueConstraint(condition=models.Q(('telegram_code', ''), _negated=True), fields=('telegram_code',), name='uq_guardian_telegram_code'),
        ),
        migrations.AddConstraint(
            model_name='guardian',
            constraint=models.UniqueConstraint(condition=models.Q(('telegram_chat_id', ''), _negated=True), fields=('organization', 'telegram_chat_id'), name='uq_guardian_telegram_chat'),
        ),
    ]
