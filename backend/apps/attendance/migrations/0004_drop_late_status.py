"""
"Kechikdi" holatini olib tashlaydi.

Davomat kun yakunida bitta savolga javob beradi: bola bog'chada bo'ldimi.
Kechikish hech qanday hisob-kitobga (to'lov, ovqat, sig'im) ta'sir qilmasdi,
lekin har kuni har bir bola uchun qo'shimcha qaror talab qilardi.

Mavjud `late` yozuvlari `present` ga o'tkaziladi — hisobotlarda ular
allaqachon "kelgan" deb sanalardi (`(present + late) / total`), ya'ni
raqamlar o'zgarmaydi. Kelish vaqti kerak bo'lganlar uchun `check_in_at`
saqlanib qoladi.
"""

from __future__ import annotations

from typing import Any

from django.db import migrations, models

OLD_STATUS = "late"
NEW_STATUS = "present"


def _forwards(apps: Any, schema_editor: Any) -> None:
    """
    Har bir tashkilot kontekstida yangilaydi.

    `attendance_record` — operatsion jadval, ya'ni RLS uni `FORCE` bilan
    yopgan: kontekstsiz `UPDATE` hech qanday qatorni ko'rmaydi va jimgina
    "muvaffaqiyatli" tugaydi (docs/03 §6.3). Shuning uchun kontekst har bir
    tashkilot uchun aniq o'rnatiladi — siyosat esa hech qayerda bo'shashmaydi.
    """
    connection = schema_editor.connection
    if connection.vendor != "postgresql":  # pragma: no cover - testlarda Postgres
        Attendance = apps.get_model("attendance", "AttendanceRecord")
        Attendance.objects.filter(status=OLD_STATUS).update(status=NEW_STATUS)
        return

    from apps.core.rls import (
        apply_tenant_setting,
        clear_tenant_setting,
        disable_platform_mode,
        enable_platform_mode,
    )

    enable_platform_mode()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM organization")
            organization_ids = [row[0] for row in cursor.fetchall()]
    finally:
        disable_platform_mode()

    try:
        for organization_id in organization_ids:
            apply_tenant_setting(organization_id)
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE attendance_record SET status = %s WHERE status = %s",
                    [NEW_STATUS, OLD_STATUS],
                )
    finally:
        clear_tenant_setting()


def _backwards(apps: Any, schema_editor: Any) -> None:
    """
    Orqaga yo'l ma'lumotni tiklamaydi — qaysi yozuv "kechikkan" bo'lgani
    endi hech qayerda yozilmagan. Faqat sxema qaytadi.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("attendance", "0003_remove_attendancerecord_ck_attendance_not_future_and_more"),
    ]

    operations = [
        migrations.RunPython(_forwards, _backwards),
        migrations.AlterField(
            model_name="attendancerecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("present", "Keldi"),
                    ("absent", "Kelmagan"),
                    ("excused", "Sababli"),
                ],
                max_length=15,
            ),
        ),
    ]
