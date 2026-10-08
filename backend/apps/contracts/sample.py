"""
Namunaviy shartnoma matni (PLAN 9.3).

Bu — mijozning HAQIQIY shartnomasi (Oriental Kinderland, 2026), nomlar,
sanalar va summalar o'rniga `{{...}}` maydonlar qo'yilgan holda. Ya'ni
bog'cha hujjatni "yuklamaydi" — u tayyor matndan boshlaydi va o'ziga
moslashtiradi: bandlarni o'chiradi, qo'shadi, so'zlarini o'zgartiradi.

Nega kodda, bazada emas: bu mijoz ma'lumoti EMAS, balki boshlang'ich
nuqta. Bazaga yozilsa, uni kim yozgani va kim o'zgartirishi mumkinligi
noaniq bo'lardi; har bir tashkilot esa shablonni saqlaganda o'zining
nusxasini oladi (`contract_template`).

Tilini tarjima qilmaymiz (ADR-16): shartnoma o'zbek tilida tuziladi va
uning yuridik matnini mashina tarjimasi bilan berish xavfli bo'lardi.
"""

from __future__ import annotations

__all__ = ["SAMPLE_CONTRACT", "SAMPLE_NAME"]

SAMPLE_NAME = "Ota-ona bilan shartnoma (namuna)"

SAMPLE_CONTRACT = """\
{{bogcha.yuridik_nomi}} NOMLI NODAVLAT MAKTABGACHA TA'LIM TASHKILOTI VA
TARBIYALANUVCHINING OTA-ONASI (QONUNIY VAKILI) O'RTASIDAGI
SHARTNOMA № {{shartnoma.raqam}}

{{filial.manzil}}                                   {{shartnoma.sana}}

{{bogcha.nomi}} nomli nodavlat maktabgacha ta'lim tashkiloti (keyingi
o'rinlarda NMTT deb yuritiladi) nomidan Nizom asosida faoliyat yurituvchi
direktori {{bogcha.direktor}} bir tarafdan va tarbiyalanuvchining ota-onasi
(qonuniy vakili) {{vasiy.fio}} (keyingi o'rinlarda qonuniy vakil) ikkinchi
tarafdan, tarbiyalanuvchi {{bola.tugilgan_yil}}-yilda tug'ilgan {{bola.fio}}
(keyingi o'rinlarda tarbiyalanuvchi deb yuritiladi), quyidagilar haqida
shartnoma tuzdilar.

I. SHARTNOMA PREDMETI

1. NMTT mazkur shartnoma shartlariga asosan tarbiyalanuvchining barcha
huquqlarini ta'minlagan holda, unga sifatli ta'lim-tarbiya berish, sog'lig'ini
muhofaza qilish va mustahkamlash, intellektual, axloqiy, ma'naviy, estetik va
jismoniy rivojlanishi uchun shart-sharoit yaratib berish majburiyatini,
qonuniy vakil esa tarbiyalanuvchini NMTTdagi tegishli guruh tarbiyachisiga
topshirish, ota-ona to'lovini o'z vaqtida amalga oshirish va NMTTning ichki
tartib-qoidalariga rioya qilish majburiyatini oladi.

Tarbiyalanuvchini NMTTda saqlash vaqti {{bogcha.saqlash_soati}} soatni tashkil
qiladi. Guruh: {{bola.guruh}}.

2. NMTTda bolalarni saqlash uchun to'lanadigan tushumlar maqsadli tartibda
tarbiyalanuvchilarni oziq-ovqat bilan ta'minlash hamda NMTTning
moddiy-texnik bazasini yaxshilashga yo'naltiriladi.

II. NMTTNING HUQUQ VA MAJBURIYATLARI

3. NMTT quyidagi huquqlarga ega:
- tarbiyalanuvchini oila muhitida tarbiyalash bo'yicha takliflar berish va
  qonuniy vakillar bilan hamkorlik qilish;
- qonuniy vakilning istagi va tarbiyalanuvchining yoshini inobatga olib,
  bolalarni guruhlarga taqsimlash;
- tarbiyalanuvchining sog'lig'i bo'yicha NMTTda bo'lishini taqiqlovchi hollar
  yuz berganida, uni vaqtincha qabul qilishni rad etish;
- to'lov shartnomada belgilangan muddatdan keyin ikki hafta mobaynida uzrli
  sabablarsiz to'lanmagan taqdirda, shartnoma amalini to'xtatish;
- qonuniy vakilning ruxsatisiz tarbiyalanuvchini boshqa shaxslarga berishni
  rad qilish.

4. NMTTning majburiyatlari:
- bolaning NMTTda bo'lishi vaqtida uning sog'lig'i va hayotini asrash, har
  tomonlama rivojlanishi uchun xavfsiz sharoit yaratish;
- davlat talablariga muvofiq ta'lim-tarbiya jarayonini tashkil etish;
- belgilangan sanitariya qoidalariga muvofiq sifatli ovqatlanishni ta'minlash;
- tarbiyalanuvchiga birinchi tez tibbiy yordam ko'rsatishni tashkil etish;
- qonuniy vakilga NMTT faoliyatiga doir ma'lumotlarni taqdim qilish;
- NMTTdagi o'zgarishlar haqida o'z vaqtida xabardor qilish.

III. QONUNIY VAKILNING HUQUQ VA MAJBURIYATLARI

5. Qonuniy vakil quyidagi huquqlarga ega:
- tarbiyalanuvchining huquq va qonuniy manfaatlarini himoya qilish;
- NMTT Ustavi bilan tanishish va tadbirlarda ishtirok etish;
- NMTT faoliyatini takomillashtirish bo'yicha takliflar kiritish;
- NMTT rahbariyatini 7 kun oldin xabardor qilgan holda shartnomani
  muddatidan avval bir taraflama bekor qilish.

6. Qonuniy vakilning majburiyatlari:
- ota-ona to'lovini o'z vaqtida amalga oshirish;
- tarbiyalanuvchining sog'lig'i haqidagi tibbiy xulosani va o'z aloqa
  ma'lumotlarini taqdim etish (telefon: {{vasiy.telefon}});
- bola betob bo'lganda zudlik bilan xabar berish va sog'aygach tibbiy
  ma'lumotnoma taqdim etish;
- tarbiyalanuvchi kelmagan kunlar uchun oldindan ariza berish;
- NMTT xodimlari va boshqa qonuniy vakillarga hurmat bilan munosabatda
  bo'lish;
- yashash joyi yoki telefon raqami o'zgarsa, bu haqda xabar berish.

IV. TO'LOV TARTIBI

7. Tarbiyalanuvchining NMTTda bo'lgan davri uchun bir oylik to'lovi
{{tarif.summa}} so'm ({{tarif.nomi}}).

8. Ota-ona to'lovi har oyning {{tolov.kuni}}-sanasidan kechiktirmasdan
to'lanadi. To'lovlar bolaning shu oyda NMTTga qatnaydigan kunlariga
mutanosib ravishda hisoblanadi.

9. Bolaning kasalligi yoki karantin tufayli kelmaganligi tibbiy
ma'lumotnoma bilan tasdiqlanishi shart. Uzrli sabab ko'rsatilgan oldindan
yozilgan ariza tarbiyalanuvchining joyi to'lovsiz saqlanib turishiga asos
bo'ladi; bir yilda ko'pi bilan {{tolov.bepul_kunlar}} ish kuni.

10. Tarbiyalanuvchi asosli sabab bilan kelmagan kunlar uchun jami to'lov
summasidan bir kunga {{tolov.ovqat_puli}} so'm miqdorida ovqat puli
ayriladi. Qolgan barcha holatlarda to'lov umumiy asoslarda to'lanadi.

V. TARAFLARNING JAVOBGARLIGI VA NIZOLAR

11. Taraflar shartnoma shartlarini bajarmagan yoki lozim darajada
bajarmagan hollarda O'zbekiston Respublikasining amaldagi qonun
hujjatlariga muvofiq javobgar bo'ladilar.

12. Nizolar kelib chiqqan taqdirda taraflar ularni sudgacha hal etish
choralarini ko'radilar; hal qilinmagan nizolar sud tartibida ko'riladi.

VI. YAKUNIY QOIDALAR

13. Mazkur shartnoma imzolangan kundan kuchga kiradi va tarbiyalanuvchi
maktabgacha ta'lim tashkilotini bitirgunicha yoki undan ketgunicha amal
qiladi.

14. Shartnoma o'zbek tilida, bir xil yuridik kuchga ega ikki nusxada
tuziladi: biri NMTTda, ikkinchisi qonuniy vakilda saqlanadi.

VII. TARAFLARNING REKVIZITLARI

NMTT:                                   Qonuniy vakil:
{{bogcha.yuridik_nomi}}                 {{vasiy.fio}}
Manzil: {{filial.manzil}}               Telefon: {{vasiy.telefon}}
STIR: {{bogcha.stir}}
Bank: {{bogcha.bank}}
H/r: {{bogcha.hisob_raqam}}
MFO: {{bogcha.mfo}}
Telefon: {{bogcha.telefon}}

Direktor: ____________ {{bogcha.direktor}}        Imzo: ____________

Shartnomaning 2-nusxasini oldim: ____________   Sana: {{shartnoma.sana}}
"""
