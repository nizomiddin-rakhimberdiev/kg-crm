"""
Xabarning turi — shablon FK'sidan alohida ustun (PLAN 3.7).

`template_id` `SET_NULL` va `NULL` bo'lishi mumkin, shuning uchun
unga tayanib "bu qanday xabar edi?" degan savolga javob berib
bo'lmaydi. Kunlik eslatma chegarasi aynan shu savolga tayanadi.

Ustun bo'sh qiymat bilan qo'shiladi; mavjud qatorlar keyingi
migratsiyada to'ldiriladi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('branches', '0002_branch_tenancy_guard'),
        ('children', '0009_sms_language'),
        ('notifications', '0004_sms_language'),
        ('organizations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='template_code',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['guardian', 'template_code', '-created_at'], name='ix_notification_kind'),
        ),
    ]
