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
    # --- Bosqich 12.1: hisoblash qoidalari (Oriental Kinderland qiymatlari) ---
    #
    # Yangi bolaning birinchi shuncha ISH kuni bepul (sinov). Bola sinov
    # ichida ketsa — hech narsa yozilmaydi; qolsa — to'lov sinovdan
    # keyingi kundan. `0` — sinov yo'q.
    "finance.trial_days": 3,
    # Hisoblangan summa shu qadamgacha yaxlitlanadi (so'm). Kunlik
    # stavka emas, KUNLAR × STAVKA natijasi: bir xil holatdagi ikki
    # bolaga har doim bir xil raqam chiqadi. `1` — butun so'mgacha.
    "finance.rounding_step": 1000,
    # --- Bosqich 12.2: imtiyozlar (Oriental Kinderland qiymatlari) ---
    #
    # Aka-uka: bir oiladagi (umumiy vasiy) har bir bolaga shuncha so'm
    # chegirma. `all` — hammasiga, birinchisiga ham; `after_first` —
    # birinchi (eng oldin qabul qilingan) bola to'liq to'laydi.
    "benefits.sibling_amount": 100000,
    "benefits.sibling_rule": "all",
    # Foiz bilan beriladigan turlar.
    "benefits.staff_child_percent": 50,
    "benefits.low_income_percent": 100,
    "benefits.full_percent": 100,
    "notifications.sms_enabled": True,
    # --- Asosiy kanal (PLAN 3.7, ADR-23) ---
    #
    # `telegram` yoki `sms`. Sukut — Telegram: u bepul, matn uzunligi
    # cheklanmagan va O'zbekistonda deyarli har bir ota-onada bor.
    # SMS'ga o'tish bitta sozlama, lekin u shlyuz shartnomasini talab
    # qiladi va har xabar pul turadi.
    #
    # Zaxira kanal ATAYLAB avtomatik emas: Telegram ulanmagan
    # ota-onaga SMS yuborish faqat SMS provayderi HAQIQATAN ulangan
    # bo'lsa ma'noli. Aks holda xabar "test rejimi" bo'lib qolardi va
    # bog'cha ota-onani botga ulash kerakligini bilmasdi.
    "notifications.default_channel": "telegram",
    # "Your child did not come today" (design §3.3, P6-5). OFF by default:
    # a kindergarten that marks the register late in the morning would
    # otherwise alarm parents whose child simply arrived after 9. The
    # message never moves money — fee credits come only from an approved
    # absence claim (ADR-19).
    "notifications.absence_alert": False,
    # --- Yuborish oynasi (Q9, PLAN 3.3) ---
    #
    # Soat 08:00 dan oldin yoki 21:00 dan keyin tayyor bo'lgan xabar
    # yuborilmaydi — navbatda turadi va ertalab ketadi. Tungi SMS
    # ota-onani uyg'otadi va bog'cha haqida eng yomon taassurot
    # qoldiradi; qarz eslatmasi esa bir necha soat kutsa hech narsa
    # yo'qotmaydi.
    "notifications.send_from_hour": 8,
    "notifications.send_to_hour": 21,
    # Bir bola bo'yicha kuniga nechta qarz eslatmasi.
    #
    # 1 — chunki ikkinchi SMS yangi ma'lumot bermaydi, faqat bezovta
    # qiladi. Ommaviy yuborish tugmasi ikki marta bosilsa ham ota-ona
    # buni sezmaydi.
    "notifications.debt_reminders_per_day": 1,
    # Xato bo'lgan xabarni necha marta qayta urinish.
    "notifications.max_retries": 3,
    # Bitta SMS bo'lagining narxi (so'm) — taxminiy tannarx uchun.
    #
    # 0 = noma'lum, ekranda narx ko'rsatilmaydi. Raqamni bog'cha o'z
    # shartnomasidan kiritadi: provayder tariflari o'zgaradi va uni
    # kodga yozib qo'yish eskirgan ma'lumotni ishonchli qilib
    # ko'rsatardi. Hisob BO'LAKLAR bo'yicha: kirill xabari 70 belgidan
    # keyin ikkinchi bo'lakka o'tadi (apps/notifications/segments.py).
    "notifications.sms_price": "0",
    "notifications.payment_receipt": True,
    "attendance.auto_absent": False,
    # Tarbiyachi necha kun orqaga davomat belgilay oladi (PLAN 2.6).
    #
    # 1 = bugun va kecha. Oldingi kunlarni faqat direktor yoki egasi
    # o'zgartiradi — va o'shanda sabab so'raladi hamda auditga yoziladi.
    # Nega chegara bor: o'tgan oyning davomatini jimgina o'zgartirish
    # qayta hisobga va hisobotga ta'sir qiladi.
    "attendance.teacher_edit_days": 1,
    # Bola yoshi chegarasi (PLAN 2.4). Sozlama, chunki bog'chalar
    # turlicha: ba'zilari 2 yoshdan, ba'zilari 7 yoshgacha oladi.
    "children.min_age": 0,
    "children.max_age": 8,
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
    # --- Shartnoma rekvizitlari (PLAN 9.3) ---
    #
    # Shartnoma matni bog'chaning o'z hujjati, lekin undagi bir necha
    # raqam TIZIMDA ham bor (narx, to'lov kuni). Qolganlari — direktor,
    # bank rekvizitlari, bir kunlik ovqat puli — hech qayerda yo'q edi,
    # va ularsiz shablon to'ldirilmas edi. Sozlama, chunki ular
    # bog'chaga xos va yilda bir marta o'zgaradi.
    "contracts.director_name": "",
    "contracts.bank_name": "",
    "contracts.bank_account": "",
    "contracts.bank_mfo": "",
    # Bola kelmagan kun uchun qaytariladigan ovqat puli (so'm/kun).
    # Bosqich 12.3: 1–2 kunlik maʼlumotnoma aynan shu summani qaytaradi
    # (`AbsenceKind.daily_amount` bo'sh bo'lsa). Oriental Kinderland: 37 500.
    "contracts.daily_meal_fee": "37500",
    # Yil davomida to'lovsiz saqlanadigan kunlar soni.
    "contracts.free_absence_days": 30,
    # Bolani saqlash vaqti (soat) — shartnomaning 1-bandi.
    "contracts.daily_hours": 10,
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
