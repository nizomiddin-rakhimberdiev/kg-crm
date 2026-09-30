"""
Sozlamalarni aniqlash (docs/03 §18.1).

Tartib: filialga xos qiymat → tashkilot global qiymati → koddagi default.
"""

from __future__ import annotations

from typing import Any

from apps.settings_app.models import SystemSetting

__all__ = ["get_setting", "set_setting", "effective_settings", "DEFAULTS"]

# Koddagi defaultlar — bazada yozuv bo'lmasa shular ishlatiladi.
# Ular ataylab shu yerda: yangi sozlama qo'shish migratsiya ham,
# har bir tashkilotga qator yozishni ham talab qilmaydi.
DEFAULTS: dict[str, Any] = {
    # Bog'chaning SUKUT tili. Xodim brauzerida o'z tanlovi bo'lmasa, ilova
    # shu tilda ochiladi (ADR-16). Til baribir har bir odam uchun alohida
    # almashtiriladi — bu faqat "biz asosan ruscha ishlaymiz" degan holatda
    # har safar qo'lda o'zgartirishni yo'q qiladi.
    "general.default_language": "uz",
    "finance.reminder_day": 5,
    # Oylik to'lov kuni — hisob-faktura muddati shu kunga qo'yiladi.
    "finance.due_day": 10,
    # --- Birinchi oy (Q2, Q3) ---
    #
    # Oy o'rtasida kelgan bola uchun birinchi hisob-faktura qanday
    # yoziladi: `full` (to'liq oy), `prorated` (ish kunlari bo'yicha),
    # `next_month` (bu oy yozilmaydi). Sukut — proporsional: ota-ona
    # kelmagan kunlari uchun to'lamasligi eng adolatli va eng kam
    # bahsli variant.
    "finance.first_month_mode": "prorated",
    # Birinchi hisob-faktura muddati qabul sanasidan kamida shuncha kun
    # keyin bo'ladi. Ya'ni oyning 30-kunida kelgan bola fakturasi
    # yaratilgan kuniyoq kechikkan bo'lib qolmaydi.
    "finance.first_invoice_grace_days": 5,
    "notifications.sms_enabled": True,
    "notifications.payment_receipt": True,
    "attendance.auto_absent": False,
    # --- Oylik maosh ushlanmalari (ADR-18) ---
    #
    # Stavkalar KODDA emas, sozlamada: ular qaror bilan, ba'zan yil
    # o'rtasida o'zgaradi, va stavkani servisga yozib qo'yish qonunga
    # bo'ysunish uchun reliz va deploy talab qilardi.
    #
    # Foizda saqlanadi (12 = 12%), chunki buxgalter hujjatda aynan
    # shu ko'rinishda ko'radi.
    # SUKUT — 0, ya'ni O'CHIRILGAN (Q10).
    #
    # Ilgari bu yerda 12 % turardi va sozlamaga umuman tegmagan bog'cha
    # ham xodimdan pul ushlab qolardi — hech kim tanlamagan qaror
    # bo'yicha. Soliq ushlash qonuniy majburiyat va uni bog'cha ongli
    # ravishda yoqishi kerak, tizim taxmin qilib emas.
    "payroll.income_tax_rate": 0,
    "payroll.pension_rate": 0,
    # Ish beruvchi xarajati — xodimdan USHLANMAYDI, bog'cha ustiga
    # to'laydi. Shuning uchun u sof maoshga emas, hisoblashning
    # UMUMIY QIYMATIGA qo'shiladi.
    "payroll.social_tax_rate": 0,
    # --- Ish kalendari (ADR-19) ---
    #
    # ISO raqamlash: 1 = dushanba … 7 = yakshanba. Shanba ishlaydigan
    # bog'cha — sozlama, sxema o'zgarishi emas.
    "attendance.working_weekdays": "1,2,3,4,5",
}


def get_setting(*, key: str, branch: Any = None) -> Any:
    """Amaldagi qiymat: filial → global → koddagi default."""
    if branch is not None:
        specific = SystemSetting.objects.filter(key=key, branch=branch).first()
        if specific is not None:
            return specific.value

    common = SystemSetting.objects.filter(key=key, branch__isnull=True).first()
    if common is not None:
        return common.value

    return DEFAULTS.get(key)


def set_setting(*, organization: Any, key: str, value: Any, branch: Any = None) -> SystemSetting:
    """Qiymatni o'rnatadi (filialga xos yoki global)."""
    setting, _ = SystemSetting.objects.update_or_create(
        key=key, branch=branch, defaults={"organization": organization, "value": value}
    )
    return setting


def effective_settings(*, branch: Any = None) -> dict[str, Any]:
    """
    Barcha amaldagi sozlamalar — defaultlar bilan birga.

    Frontend to'liq ro'yxatni ko'rsatishi kerak, faqat o'zgartirilganlarini
    emas: foydalanuvchi "bu sozlama umuman bormi?" degan savolga javob
    izlab yurmasin.
    """
    resolved = dict(DEFAULTS)

    for setting in SystemSetting.objects.filter(branch__isnull=True):
        resolved[setting.key] = setting.value
    if branch is not None:
        for setting in SystemSetting.objects.filter(branch=branch):
            resolved[setting.key] = setting.value

    return resolved
