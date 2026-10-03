# 6-bosqich — texnik dizayn (kod YO'Q)

Holat: **dizayn**, 2026-10-03. ADR-25 `main` da band (RBAC delegatsiya tuzatishi), shuning uchun takliflar ADR-26 dan boshlanadi. Brief: "Hozircha faqat shu hujjatga
texnik dizayn yoz, kod yozma." Har bir bo'lim mavjud arxitekturaga
tayanadi — yangi qarorlar ADR sifatida belgilangan va kod yozilishidan
oldin `docs/02 §2` ga ko'chiriladi.

Mazmun:

1. [Ota-onalar onlayn to'lovi — Payme va Click](#1-ota-onalar-onlayn-tolovi--payme-va-click)
2. [Obuna uchun onlayn to'lov](#2-obuna-uchun-onlayn-tolov)
3. [Ota-onalar Telegram boti](#3-ota-onalar-telegram-boti)
4. [Oshxona / menyu va ombor](#4-oshxona--menyu-va-ombor)
5. [Shartnoma shablonlari](#5-shartnoma-shablonlari)
6. [Mustaqil ro'yxatdan o'tish — 14 kunlik sinov](#6-mustaqil-royxatdan-otish--14-kunlik-sinov)
7. [Bajarish tartibi, xavflar, egasining qarorlari](#7-bajarish-tartibi-xavflar-egasining-qarorlari)

---

## 0. Barcha bo'limlarga umumiy qoidalar

Yangi kod quyidagilarni buzmaydi — ular hujjatlarda allaqachon qotirilgan:

| Qoida | Manba | Bu bosqichda nimani anglatadi |
|---|---|---|
| Uch append-only ledger | invariant 3, 12 | Onlayn to'lov ham `Payment` + `cash_movement` + `child_ledger_entry`, bitta tranzaksiyada. Bekor qilish — qarshi yozuv |
| Pul hujjatga taqsimot bilan bog'lanadi | ADR-20 | To'lov havolasi fakturaga tegishli → taqsimot SHU fakturadan boshlanadi, qoldiq FIFO, ortig'i avans (Q1) |
| Balans formulasi bitta faylda | invariant 13 | Bot ham, to'lov sahifasi ham `finance/balance.py` dan o'qiydi |
| Tenant chegarasi va RLS | ADR-9, invariant 8 | Webhook va bot tenant kontekstisiz keladi → tenant **havola/kod ichidan** aniqlanadi (ADR-23 dagi usul), RLS kengaytirilmaydi |
| Yetkazilmagan xabar "yuborildi" emas | ADR-22 | Bot xabarlari ham `notification` jurnali orqali |
| Pul — faqat `Decimal` | brief, 4-qoida | Payme tiyin (butun son) ↔ so'm: `Decimal(amount) / 100`, `quantize(Decimal("0.01"))`; float hech qayerda |
| Maxfiy kalitlar faqat `.env` / shifrlangan | brief, 9-qoida | Bog'chaning merchant kalitlari bazada **shifrlangan** (§1.4) |
| Standalone rejim | ADR-13 | Har bir bo'lim `DEPLOYMENT_MODE` da nima qilishini aytadi |

---

## 1. Ota-onalar onlayn to'lovi — Payme va Click

### 1.1 Asosiy qaror: pul KIMGA tushadi

**Pul bog'chaning o'z merchant hisobiga tushadi, Radix'ning hisobiga
emas.** Radix to'lov agregatori bo'lmaydi: aks holda u mijozlarning
pulini ushlab turuvchi moliyaviy vositachiga aylanadi (litsenziya,
soliq, qaytarish majburiyatlari) — yakka asoschi uchun bu noto'g'ri
yuk. Demak:

- har bir tashkilot Payme va/yoki Click bilan **o'zi** shartnoma tuzadi
  va merchant kalitlarini Sozlamalarga kiritadi;
- Radix faqat integratsiyani beradi: to'lov havolasi, webhook, ledger.

**ADR-26 (taklif):** *Onlayn to'lov — bog'chaning o'z merchant hisobi
orqali; Radix pulni ushlab turmaydi.*

### 1.2 Oqim

```
Bog'cha → faktura (mavjud)
       → "To'lov havolasi" (yangi): /pay/<token>
Ota-ona → havolani ochadi (botda yoki SMS'da) → summa va faktura
       → "Payme" / "Click" → provayder sahifasi (redirect, skript yo'q)
Provayder → webhook: /api/v1/public/pay/{provider}/{org_token}
         → CheckPerformTransaction / Prepare  — summa va faktura tekshiriladi
         → CreateTransaction                  — online_transaction (pending)
         → PerformTransaction / Complete      — BITTA tranzaksiyada:
              Payment(method=online) + cash_movement("Payme/Click" qopi)
              + ledger kredit + taqsimot (shu fakturadan, keyin FIFO)
         → CancelTransaction (perform'dan keyin) — reverse_payment()
```

CSP o'zgarmaydi: provayder sahifasiga **yo'naltirish** (redirect),
bizning sahifamizda tashqi skript yoki iframe yo'q.

### 1.3 Ma'lumotlar modeli

```
online_payment_link           -- to'lov havolasi
  id, organization_id NOT NULL, branch_id, invoice_id NOT NULL,
  token CHAR(43) UNIQUE        -- base64url(org uuid + 16 tasodifiy bayt)
  amount_snapshot NUMERIC(12,2) -- havola yaratilgandagi qoldiq (ma'lumot uchun)
  expires_at, created_by, created_at

online_transaction            -- provayder tranzaksiyasi (holat mashinasi)
  id, organization_id NOT NULL, branch_id,
  provider ('payme'|'click'), provider_txn_id VARCHAR(64),
  invoice_id NOT NULL, amount NUMERIC(12,2),
  state ('created'|'performed'|'cancelled'|'cancelled_after_perform'),
  payment_id NULL               -- perform'da paydo bo'ladi
  reason SMALLINT NULL, created_at, performed_at, cancelled_at
  UNIQUE (provider, provider_txn_id)   -- takroriy webhook — o'sha qator

merchant_credential           -- bog'chaning Payme/Click kalitlari
  id, organization_id NOT NULL, provider, merchant_id,
  secret_encrypted BYTEA, is_active, created_at
  UNIQUE (organization_id, provider) WHERE is_active
```

- Uchala jadval `organization_id NOT NULL` va RLS siyosati bilan
  (`check_rls` 46 → 49).
- `online_transaction` holati yangilanadi, lekin **pul** unda emas:
  pul `Payment` / `cash_movement` / ledger'da, va ular append-only.
- `Payment.idempotency_key = f"{provider}:{provider_txn_id}"` — mavjud
  `uq_payment_idempotency` ikkinchi `Payment` ni baza darajasida
  rad etadi (invariant 8).

### 1.4 Merchant kalitlarini saqlash

Kalit bazada **shifrlangan** (`cryptography.Fernet`, kalit
`MERCHANT_SECRET_KEY` — `.env` da, bazada emas). Sabab: zaxira nusxa
(`pg_dump`) yoki SQL in'ektsiya kalitlarni ochiq ko'rsatmasin. API
kalitni hech qachon qaytarmaydi — faqat "o'rnatilgan / o'rnatilmagan"
va oxirgi 4 belgi. Kalitni almashtirish auditda.

### 1.5 Webhook — tenant qanday aniqlanadi

Webhook tenant kontekstisiz keladi. ADR-23 dagi usul takrorlanadi:
URL ichida `org_token` (tashkilot UUID'idan hosil qilingan, tasodifiy
qismi bilan) — server tashkilotni aniqlaydi va **o'sha tashkilot
kontekstida** ishlaydi. Platforma rejimi ham, RLS kengaytirish ham yo'q.

Autentifikatsiya:

| Provayder | Tekshiruv |
|---|---|
| Payme | `Authorization: Basic base64("Paycom:" + key)` — bog'chaning kaliti bilan solishtiriladi (`hmac.compare_digest`). Mos kelmasa — JSON-RPC xato `-32504` |
| Click | `sign_string = md5(click_trans_id + service_id + secret + merchant_trans_id [+ merchant_prepare_id] + amount + action + sign_time)` — mos kelmasa `error: -1` |

Qo'shimcha: provayder IP manzillari ro'yxati (`PAYME_ALLOWED_IPS`,
`CLICK_ALLOWED_IPS`, `.env`) — nginx'da emas, ilovada (standalone
o'rnatmada ham ishlashi uchun).

### 1.6 Payme Merchant API metodlari

| Metod | Nima qiladi | Muhim qoida |
|---|---|---|
| `CheckPerformTransaction` | Faktura bor, ochiq, summa ≤ qoldiq? | Ortiqcha to'lov **rad etilmaydi** (ADR-20: ortig'i avans) — faqat faktura bekor qilingan yoki bola arxivda bo'lsa rad |
| `CreateTransaction` | `online_transaction(state=created)` | Bir fakturaga bir vaqtda bitta ochiq tranzaksiya; 12 soatlik taym-aut — `cancelled`, `reason=4` |
| `PerformTransaction` | Pul yoziladi (1.2) | Idempotent: ikkinchi chaqiruv o'sha javobni qaytaradi |
| `CancelTransaction` | `created` → `cancelled`; `performed` → `reverse_payment()` | Qaytarish — qarshi yozuv (invariant 3) |
| `CheckTransaction`, `GetStatement` | O'qish | Tashkilot kontekstida |

Summalar tiyin bilan keladi: `Decimal(amount) / Decimal(100)`.

### 1.7 Click SHOP-API

`Prepare` (action=0) ≈ Check+Create, `Complete` (action=1) ≈ Perform.
`error < 0` bilan kelgan `Complete` — bekor qilish. Qolgani Payme bilan
bir xil servisdan o'tadi: `online_payments/services.py` provayderdan
mustaqil (`perform(txn)`), provayder adapterlari faqat protokolni
tarjima qiladi — xuddi `notifications/providers.py` dagidek.

### 1.8 Ekranlar

- Faktura qatorida "To'lov havolasi" — nusxalash, botga yuborish.
- Sozlamalar → "Onlayn to'lov": Payme/Click kalitlari, "Sinov to'lovi"
  (1 000 so'm) tugmasi.
- To'lovlar jurnali — usul "Payme / Click", tranzaksiya raqami.
- Kassa: "Payme / Click" qopi (ADR-17, allaqachon seed qilinadi).

### 1.9 Testlar (kod bosqichida)

- Protokol testlari: Payme va Click hujjatidagi har bir xato kodi.
- Takroriy webhook → bitta `Payment` (baza cheklovi bilan).
- Perform'dan keyin cancel → balans, kassa va taqsimot qaytadi.
- Begona `org_token` → 404; boshqa tashkilot fakturasi → "topilmadi".
- Ortiqcha summa → avans (ADR-20).

**Standalone:** xuddi shunday ishlaydi — merchant kaliti mijozning o'zi.

---

## 2. Obuna uchun onlayn to'lov

Bu yerda pul **Radix'ga** tushadi — demak alohida, Radix'ning o'z
merchant hisobi (`.env`: `RADIX_PAYME_*`, `RADIX_CLICK_*`).

- Domen alohida: `subscriptions` (invariant 9). `SubscriptionPayment`
  allaqachon bor; onlayn to'lov — yangi `method="online"` va
  `provider_txn_id` ustuni (UNIQUE).
- Webhook yo'li: `/api/v1/public/pay/subscription/{provider}` —
  tenant `SubscriptionInvoice` raqamidan aniqlanadi (platforma
  tekisligidagi metama'lumot jadvali, ADR-10 bilan mos).
- Obuna sahifasi: "Qanday to'lash" blokiga "Payme / Click orqali
  to'lash" tugmasi (bank rekvizitlari — D8 — saqlanadi).
- To'lov kelgach `suspended` → `active` avtomatik (mavjud
  `record_subscription_payment` mantiqi).

**Standalone:** bo'lim butunlay o'chiq (obuna yo'q).

---

## 3. Ota-onalar Telegram boti

Hozirgi bot (ADR-23): `/start <kod>` bilan vasiyni ulaydi va bog'cha
xabarlarini yetkazadi. 6-bosqich uni **ota-onaning shaxsiy kabinetiga**
aylantiradi.

### 3.1 Telefon orqali ulanish

Taklif havolasidan tashqari ikkinchi yo'l: ota-ona botda "Telefon
raqamni ulashish" tugmasini bosadi (Telegram `request_contact` —
raqamni Telegramning o'zi tasdiqlaydi, ota-ona uni yozmaydi).

Muammo: raqam bo'yicha vasiyni qidirish **tenantlar bo'ylab** qidiruv,
webhook esa tenant kontekstisiz. RLS'ni kengaytirmaslik uchun
(ADR-23 dagi tamoyil):

**ADR-27 (taklif):** `guardian_phone_index` — platforma tekisligidagi
tor indeks jadvali: `(phone_hmac CHAR(64), organization_id)`. Vasiy
saqlanganda servis uni yangilaydi. Ochiq raqam YO'Q — faqat
`HMAC-SHA256(PHONE_INDEX_KEY, normalised_phone)`; bu jadvaldan
"kimning raqami qaysi bog'chada" ni o'qib bo'lmaydi. Bot faqat
tashkilot ro'yxatini oladi va keyin har biriga **o'sha tashkilot
kontekstida** murojaat qiladi.

- Bir nechta bog'cha topilsa — ota-ona tanlaydi.
- Mavjud vasiylar uchun indeks `--dry-run` li backfill buyrug'i bilan
  to'ldiriladi (brief, 5-qoida).

### 3.2 Buyruqlar va tugmalar

| Tugma | Javob | Manba |
|---|---|---|
| 💰 Balans | Qarz, avans, keyingi to'lov sanasi | `finance/balance.py` (invariant 13) |
| 🧾 Hisob-fakturalar | Oxirgi 6 ta, holati bilan | `invoices` |
| 💳 To'lash | §1 dagi to'lov havolasi | `online_payment_link` |
| 📄 Kvitansiyalar | To'lovdan keyin avtomatik + so'rov bo'yicha | mavjud kvitansiya (HTML) |
| 🔕 To'xtatish | `/stop` (mavjud) | — |

Bir nechta bola bo'lsa — har tugma avval bolani so'raydi.

### 3.3 Kelmagani haqida xabar

Davomatda bola `absent` deb belgilansa — ota-onaga xabar (sozlama:
`notifications.absence_alert`, sukut **o'chiq**; yuborish oynasi Q9
amal qiladi). ADR-19 bo'yicha bu xabar **pulga tegmaydi**: kredit faqat
tasdiqlangan `absence_claim` dan. Xabar ichida "Kasal — ma'lumotnoma
yuborish" tugmasi `absence_claim` qoralamasini ochadi; tasdiqlash —
bog'cha xodimi.

### 3.4 Xavfsizlik

- Bot har so'rovda chat_id → vasiy → bola zanjirini **tenant
  kontekstida** tekshiradi; uzilgan vasiy (`/stop` yoki arxiv) hech
  narsa olmaydi.
- Xabarlarda boshqa bolaning ma'lumoti yo'q — test: ikki oilali
  vasiy faqat o'z bolalarini ko'radi.
- Webhook: mavjud maxfiy yo'l + `X-Telegram-Bot-Api-Secret-Token`.

**Standalone:** har o'rnatma o'z botini `.env` da oladi.

---

## 4. Oshxona / menyu va ombor

### 4.1 Model

```
dish            -- taom: nom, guruh yoshi, porsiya (g)
dish_ingredient -- dish_id, product_id, quantity_per_portion NUMERIC(10,3)
menu_day        -- sana, branch, holat (draft|approved|served)
menu_item       -- menu_day_id, dish_id, meal ('breakfast'|'lunch'|'snack')
```

Hammasi `organization_id NOT NULL` + RLS.

### 4.2 Ombor bilan bog'lanish

`menu_day` "berildi" (`served`) qilinganda **porsiyalar soni = shu kungi
davomatdagi `present` bolalar** (+ xodimlar porsiyasi, sozlama).
Har ingredient uchun `stock_movement(type=consumption)` yoziladi —
append-only (invariant 3), manba `menu_day`. Xato — qarshi
`adjustment`, tahrir emas.

- Qoldiq yetmasa — xato emas, ogohlantirish: ovqat allaqachon berilgan,
  ombor yozuvi haqiqatni aks ettirishi kerak (manfiy qoldiq — "kam
  qolgan" signali).
- Hisobot: "taom tannarxi" = Σ (ingredient miqdori × o'rtacha kirim
  narxi) / porsiya.

### 4.3 Ekranlar

Haftalik menyu jadvali, taom kartochkasi (ingredientlar), "Bugun
berildi" tugmasi — tasdiqdan oldin porsiya va chiqim ro'yxati preview
(PLAN 1.4 dagi generatsiya preview'i bilan bir xil naqsh).

---

## 5. Shartnoma shablonlari

- `contract_template`: nom, til, matn (o'zgaruvchilar bilan:
  `{{bola.fio}}`, `{{vasiy.fio}}`, `{{tarif.summa}}`, `{{bogcha.nomi}}`,
  `{{bogcha.stir}}` …), versiya.
- `contract`: bola, vasiy, shablon versiyasi, **qiymatlar suratlangan**
  (`rendered_html`, `values JSONB`), holat (`draft|signed|terminated`),
  imzolangan sana.
- Yaratilgan shartnoma **o'zgarmaydi**: tarif keyin o'zgarsa ham
  shartnoma o'z qiymatlari bilan qoladi (faktura bilan bir xil
  tamoyil). O'zgarish — yangi shartnoma yoki qo'shimcha kelishuv.
- Chop etish — HTML + brauzer (D1 qarori), PDF kutubxonasisiz.
- Matn tenantning ma'lumoti — tarjima qilinmaydi (ADR-16).

---

## 6. Mustaqil ro'yxatdan o'tish — 14 kunlik sinov

Bu **mavjud qarorni bekor qiladi**: ochiq `/auth/signup` ataylab
olib tashlangan (docs/04 §5) — sababi tasodifiy tashrif bazada abadiy
qoladigan tenant yaratardi. Qaytarishdan oldin o'sha sababni yopish
kerak.

**ADR-28 (taklif):** *Mustaqil ro'yxatdan o'tish — email tasdiqlangandan
keyingina tenant yaratiladi; tasdiqlanmagan va to'lovga o'tmagan sinov
eksport oynasidan keyin audit bilan o'chiriladi.*

1. **Tenant birinchi bosqichda yaratilmaydi.** Forma `signup_request`
   (platforma tekisligi) yozadi va emailga 24 soatlik havola yuboradi.
   Tasdiqlanmasa — qator 7 kundan keyin o'chiriladi, tenant umuman
   paydo bo'lmaydi.
2. Havola bosilganda — mavjud `register_organization()` (vendor
   konsoli bilan BIR yo'l), parolni ega o'zi qo'yadi (PLAN 5.5 naqshi).
3. Sinov **14 kun** (brief). Hozirgi vendor ochgan sinov 15 kun —
   ikkalasi `subscription_plan.trial_days` dan o'qiladi, kodda emas.
4. Himoya: honeypot (mavjud lead formasida bor), IP bo'yicha tezlik
   chegarasi, bir emailga bitta ochiq so'rov, slug qat'iy tekshiruvi
   (PLAN 5.5).
5. **Konvertatsiya bo'lmagan sinov:** sinov tugadi → `pending_payment`
   (yozish yopiq, o'qish ochiq — invariant 11) → 30 kunlik eksport
   oynasi → `purge_organization` (PLAN 5.10 da tuzatilgan tartib bilan).
   Bu ADR-11 dagi "ma'lumot o'chirilmaydi" bilan ziddiyat emas: u
   **to'lovchi** mijoz haqida; hech qachon to'lamagan sinov tenant —
   alohida holat va uni egasi ADR-28 da tasdiqlashi kerak.
6. Har ro'yxatdan o'tish sotuv konsolida lead sifatida ham ko'rinadi
   (mavjud `Lead`, manba `self_signup`).

**Standalone:** bo'lim o'chiq.

---

## 7. Bajarish tartibi, xavflar, egasining qarorlari

### 7.1 Tartib (har biri alohida branch va hisobot)

| # | Bo'lim | Bog'liqlik | Taxminiy hajm |
|---|---|---|---|
| 6.1 | Payme/Click — ota-ona to'lovi | — | katta |
| 6.2 | Telegram bot — balans, fakturalar, to'lash | 6.1 (to'lash tugmasi) | o'rta |
| 6.3 | Telefon orqali ulanish (ADR-27) | 6.2 | kichik |
| 6.4 | Obuna onlayn to'lovi | 6.1 adapterlari | kichik |
| 6.5 | Shartnoma shablonlari | — | o'rta |
| 6.6 | Oshxona / menyu | — | o'rta |
| 6.7 | Mustaqil ro'yxatdan o'tish (ADR-28) | egasining qarori | o'rta |

Sabab: 6.1 — pul olib keladigan va eng ko'p so'raladigan; 6.2/6.3
uning ustiga quriladi; 6.7 eng oxirida, chunki u mavjud qarorni bekor
qiladi.

### 7.2 Xavflar

| # | Xavf | Yumshatish |
|---|---|---|
| R9 | Takroriy webhook ikki marta pul yozadi | `UNIQUE(provider, provider_txn_id)` + `Payment.idempotency_key` — baza darajasida |
| R10 | Webhook boshqa tenant fakturasini to'laydi | `org_token` → tenant kontekst; faktura shu kontekstda topilmasa — "topilmadi" |
| R11 | Merchant kaliti oshkor bo'ladi | Shifrlash (§1.4), API qaytarmaydi, zaxirada ham shifrlangan |
| R12 | Telefon indeksi kim qayerda ekanini oshkor qiladi | HMAC, ochiq raqam yo'q; faqat bot o'qiydi |
| R13 | Ochiq ro'yxatdan o'tish bazani axlat tenantlar bilan to'ldiradi | Email tasdig'idan oldin tenant yo'q; konvertatsiyasizlar purge |
| R14 | Menyu chiqimi ombor qoldig'ini manfiyga tushiradi | Xato emas, signal; tuzatish — `adjustment` |

### 7.3 Egasining qarori kerak (kod boshlanishidan oldin)

1. **Payme va Click shartnomalari** — har bog'cha o'zi tuzadimi
   (tavsiya — ha, ADR-26), yoki Radix bitta umumiy hisob ochadimi?
2. Provayder komissiyasini kim to'laydi — bog'cha yoki ota-ona
   (summa ustiga qo'shiladimi)?
3. Obuna uchun Radix'ning o'z Payme/Click merchant hisobi.
4. **ADR-28** — ochiq ro'yxatdan o'tishni qaytarish va to'lamagan
   sinovlarni o'chirish siyosati.
5. Ota-onaga "kelmadi" xabari sukut bo'yicha o'chiq qolsinmi.
