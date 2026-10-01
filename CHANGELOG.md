# O'zgarishlar tarixi

Format: [Keep a Changelog](https://keepachangelog.com/uz/1.1.0/) ·
Versiyalash: sana bo'yicha (loyiha hali hosted SaaS, reliz raqami yo'q).

## [Chiqarilmagan] — katta yangilanish

Reja: [`docs/big-update/PLAN.md`](./docs/big-update/PLAN.md) ·
Bajarilgani: [`docs/big-update/PROGRESS.md`](./docs/big-update/PROGRESS.md)

### Qo'shildi
- 0-bosqich: 40 ta qizil test (`pytest -m big_update`, frontendda `it.fails`)
  2026-09-30 production auditidagi kamchiliklarni takrorlaydi.
- **1-bosqich — moliyaviy to'g'rilik (ADR-20).** `payment_allocation`:
  qaysi pul qaysi hisob-fakturani yopgani. Balans formulasi bitta
  faylda (`finance/balance.py`). Birinchi oy proporsional, muddat
  qabul sanasidan. Generatsiya oldidan preview. Kvitansiya (A4 va
  80 mm). To'lovlar jurnali filtr va yig'indi bilan. Ombor xaridi
  chiqim va kassaga tushadi. Oylikda tushib qolgan xodim signali va
  ishga kirgan oyi proporsional. Narx yagona modulda.

- **2-bosqich — bola kartasi, validatsiya, rollar (ADR-21).** Telefon
  raqami hamma joyda normalizatsiya qilinadi. Bola holati sana va
  sabab bilan, arxiv `is_active` dan ajratildi. Qidiruv apostrof va
  alifbo farqini ko'rmaydi. Guruhga tarbiyachi biriktiriladi va u
  faqat o'z guruhini ko'radi. Bola kartasi qayta qurildi: hisob,
  tahrirlash, vasiylar, tablar.

- **3-bosqich — SMS va qarzdorlar (ADR-22).** Eskiz.uz provayderi
  (token keshi, xato matni, tasdiqlangan jo'natuvchi majburiy).
  Yetkazilmagan xabar endi "Yuborildi" deb yozilmaydi — `test_mode`
  holati va yopilmaydigan banner. Yuborish oynasi 08:00–21:00,
  kuniga bitta eslatma, qayta urinish soni — hammasi sozlamada.
  Oylik SMS soni va taxminiy xarajat (bo'laklar bo'yicha). Shablon
  muharriri: o'zgaruvchi tugmalari, belgi/bo'lak hisoblagichi,
  preview, o'zbekcha va ruscha matnlar. Qarzdorlar sahifasi:
  kechikkan kunlar, oxirgi eslatma, filtrlar, saralash, Excel,
  qator va ommaviy eslatma — ikkalasi ham aniq son ko'rsatilgan
  tasdiq bilan. Yangi ariza sotuv Telegram chatiga tushadi, lead'da
  "keyingi qo'ng'iroq" sanasi.

### O'zgardi
- Ortiqcha to'lov endi rad etilmaydi — ortig'i avansga aylanadi (Q1).
- `payroll.income_tax_rate` va `payroll.pension_rate` sukut qiymati
  0 ga tushdi (Q10). Yakunlangan hisoblar o'zgarmaydi.
- Narxi ko'rsatilgan ombor xaridi chiqim yozuvini yaratadi (Q13).
- `DELETE /children/{id}` endi ARXIVLAYDI (Q6); qattiq o'chirish
  alohida, 24 soatlik oynada.
- Noto'g'ri formatdagi telefon raqami qabul qilinmaydi (Q7). Mavjud
  yozuvlar tegilmaydi — `report_bad_phones` ro'yxat beradi.
- Tarbiyachi davomatni faqat oxirgi kunlar uchun belgilaydi
  (`attendance.teacher_edit_days`, sukut 1 = bugun va kecha).
- Console provayder orqali ketgan xabar "Yuborildi" emas, **"Test
  rejimi"**. Eski qatorlar o'zgarmaydi.
- Noto'g'ri raqamga urinilmaydi: xabar darhol `failed` bo'ladi va
  sababi jurnalda qoladi.
- Yuborish oynasidan tashqarida tayyor bo'lgan xabar o'chirilmaydi —
  navbatda qoladi va ertalab ketadi.
- SMS matnidagi `ʻ` va `ʼ` oddiy `'` ga almashtiriladi (Q11): ular
  xabarni UCS-2 ga o'tkazib narxni ikki baravar qilardi.
- Ko'chirmada `tuition`/`payment` kabi xom kodlar o'rniga odam tili.

---

## 2026-09-30 — Radix Brendbuk 1.1

### O'zgardi
- Butun ilova va sayt yangi brendda: Ildiz/Nihol/O'rik/Sut/Tosh palitrasi,
  Onest + Golos Text + JetBrains Mono shriftlari, haqiqiy logotip.
- Ko'k va binafsha Tailwind shkalalari brend ranglariga qayta yo'naltirildi.

### Qo'shildi
- `src/components/brand/Logo.tsx` — brendbuk qoidalari bilan.
- `src/__tests__/brand.test.ts` — adashgan ko'k sinf yoki qattiq rangda build to'xtaydi.
- `scripts/og.mjs` — ulashish rasmlarini sahifa matnidan chizadi.
- `docs/05 §18` — brend tizimi hujjati.
