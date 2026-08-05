"""
Row-Level Security siyosatlari (docs/03 §6.3).

Bu migratsiya **oxirgi** bo'lishi kerak: u barcha jadvallar mavjud
bo'lgandan keyin siyosat qo'yadi. Shuning uchun har bir app'ning oxirgi
migratsiyasiga bog'langan.

RLS "migratsiya emas, siyosat qo'shish" — aynan shuning uchun u shu
paytda, mavjud ma'lumotni ko'chirmasdan qo'shilyapti. Buning sababi
Sprint 0 da qabul qilingan qaror: `organization_id` BIRINCHI
migratsiyadan beri har bir jadvalda. Tenancy'ni kod yozilishidan oldin
hal qilishning haqiqiy foydasi shu yerda ko'rinadi.
"""

from django.db import migrations

from apps.core.rls import build_policy_sql, build_policy_teardown_sql

class Migration(migrations.Migration):
    # Barcha jadvallar mavjud bo'lgandan KEYIN ishlashi kerak.
    dependencies = [
        ("core", "0001_tenancy_guards"),
        ("accounts", "0005_role_tenancy_guard"),
        ("attendance", "0003_remove_attendancerecord_ck_attendance_not_future_and_more"),
        ("branches", "0002_branch_tenancy_guard"),
        ("children", "0003_child_tariff"),
        ("expenses", "0002_tenancy_guards"),
        ("finance", "0004_payment_tenancy_guard"),
        ("hr", "0002_tenancy_guards"),
        ("inventory", "0002_tenancy_guards"),
        ("notifications", "0002_tenancy_guards"),
        ("organizations", "0001_initial"),
        ("payroll", "0002_tenancy_guards"),
        ("reports", "0001_initial"),
        ("settings_app", "0002_tenancy_guards"),
        ("subscriptions", "0002_seed_launch_plan"),
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=build_policy_sql(), reverse_sql=build_policy_teardown_sql())
    ]
