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

- **3.7 — Telegram asosiy kanal (ADR-23).** Ota-onalarga xabar
  Telegram bot orqali ketadi: bepul, uzunlik cheklanmagan. Bola
  kartasida har bir vasiyning ulanish holati va bir martalik ulash
  havolasi. Bot `/start` va `/stop` ni biladi. Jurnalda kanal
  ko'rinadi, narx faqat SMS uchun hisoblanadi. SMS adapteri joyida —
  bitta `.env` qatori bilan yoqiladi.

- **4-bosqich — UI/UX, dizayn, tarjima.** Formatlash yagona uyda
  (`lib/format.ts`): pul, raqam, miqdor, sana — uz/ru bo'linmaydigan
  bo'shliq, en vergul, valyuta `soʻm`/`сум`/`UZS`. Sana maydonlari
  `dd.mm.yyyy` (brauzer lokalidan mustaqil). Apostroflar Q11 bo'yicha
  normallashtirildi (1200+ satr). Ish kunlari katakchalar bilan
  tanlanadi, har bir sozlamaning odamcha nomi bor, eksport fayllari
  tilga mos nom oladi. Audit jurnalida UUID o'rniga nomlar va
  tarjimadagi maydon nomlari. Yon menyu bo'limlarga ajraldi. Bog'cha
  logotipi: yuklash, sarlavha, login, futer. Obuna banneri summani
  aytadi, "Qanday to'lash" tugmasi bor, faqat egasi va direktorga
  ko'rinadi, yopilsa kuniga bir marta qaytadi. A11y: 12px minimum,
  ikonkali tugmalarga nom, ko'rinadigan fokus, to'lov oynasi
  klaviatura bilan.

- **5-bosqich — xavfsizlik, landing, huquqiy, demo.** Refresh token
  `httpOnly` cookie'da, access faqat xotirada, CSRF. Parolni tiklash
  (30 daqiqa, bir martalik). Hisob bo'yicha kirish cheklovi (10/15 daq).
  Ikki bosqichli tasdiqlash: vendor uchun sukut bo'yicha, mijoz uchun
  ixtiyoriy, 10 ta bir martalik zaxira kodi (ADR-24). Yangi bog'cha
  egasi 72 soatlik taklif havolasi bilan parolni o'zi qo'yadi. nginx:
  CSP, Permissions-Policy, `/` → `/uz` (ruscha brauzer → `/ru`), haqiqiy
  404. Landing: bitta shrift, aloqa bloki, "24 soat ichida" javobi va
  Telegram tugmasi, 12px minimum, telefonda sahifa ikki baravar qisqa.
  Maxfiylik siyosati va foydalanish shartlari qayta yozildi (uz/ru/en).
  `/t/demo` namoyish bog'chasi (`seed_demo_tenant`). 2026-09-30 sinov
  yozuvlarini tozalash buyrug'i (sukut — dry-run). Vendor konsoli:
  tarjima, ruxsatlar tarixi, reja va to'lov davrini o'zgartirish,
  faollik, taxminiy oylik. Zaxira cron o'rnatuvchisi.

### Tuzatildi
- **Dashboard pul harakatidan keyin 2 daqiqa eski qarzni ko'rsatardi** —
  kesh hech qachon bekor qilinmasdi.
- **1-sanadan chiqib ketgan bolaga o'sha oy uchun faktura yozilardi.**
- Bola kartasidan qo'shilgan vasiy telefoni tekshirilmasdi va
  normalizatsiya qilinmasdi (Q7).
- Orqaga sanalgan "chiqib ketdi" holati 409 xato berardi.
- Begona bolaning balansiga so'rov 422 o'rniga 404 qaytaradi.
- Hisobotlar grafigi 11px; telefonda to'lovlar doskasida ismlar kesilardi.
- **Tashkilotni o'chirish (offboarding) tarifi bor bolada yiqilardi** —
  `TariffPlan` o'chirish tartibida bolalardan oldin turardi.
- `seed_demo` davomati faqat bugungi kunni yozardi (o'tgan kun sabab
  talab qiladi).
- `compose.prod.yaml` dagi `VITE_PUBLIC_HOST`/`VITE_LEGAL_ENTITY_NAME`
  Docker'da jimgina yo'qolardi (`ARG` e'lon qilinmagan); standalone
  o'rnatmaning frontendi SaaS rejimida yig'ilardi.

### O'zgardi
- Shriftlar o'z serverimizdan — Google Fonts yo'q; ikkinchi telefon raqami.
- **`PLATFORM_2FA_REQUIRED` sukut bo'yicha `True`** (ADR-24, ADR-15 dagi
  `False` o'rniga).
- Vendor yangi bog'cha ochganda parol YOZMAYDI.
- Manzil nomi (slug) qat'iy tekshiriladi: lotin, raqam, chiziqcha, 3–40.
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
- **Sukut kanal — Telegram.** SMS faqat shlyuz haqiqatan ulangan
  bo'lsa ishlatiladi; test rejimidagi SMS'ga "tushib qolish" yo'q.
- Ulanmagan ota-onaga xabar jimgina o'tkazib yuborilmaydi — "Telegram
  ulanmagan" sababi bilan jurnalda turadi.
- Sozlamalarda "SMS xabarnomalar" → "Xabarnomalar", "SMS tili" →
  "Xabar tili": kanal endi bittadan ko'p.
- `seed_sms_templates` buyrug'i `seed_templates` deb nomlandi va
  yetishmayotgan HAR QANDAY kanal×til shablonini qo'shadi.
- **Eksport fayl nomlari** so'rov tilida: `tushum_2026-10-02.xlsx`.
- **Sana maydonlari** native kalendar o'rniga `dd.mm.yyyy` matn
  maydoni (kalendar tugma ortida qoladi).
- **Obuna banneri faqat egasi va direktorga.**
- Yon menyu bo'limlarga ajraldi; rol nomi hamma joyda bir xil
  registrda.

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
