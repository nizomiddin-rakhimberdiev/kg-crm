# Katta yangilanish — reja

> **Bu hujjat ishchi reja, `docs/00`–`07` esa haqiqat manbai.** Bu yerda
> nima qilinishi va qaysi tartibda qilinishi yozilgan; qaror o'zgarsa,
> egasi bo'lgan hujjat ham o'sha o'zgarishda yangilanadi (CLAUDE.md 3-qoida).
>
> Bajarilgan ish `PROGRESS.md` da. Yangi sessiya shu ikki fayldan davom etadi.

**Holat:** 0, 1 va 2-bosqichlar bajarildi · 3-bosqich kutilmoqda
**Boshlandi:** 2026-09-30 · **Baza:** `main` @ `dd32207`

---

## 1. Arxitektura xaritasi

### Backend — modulli monolit (Django 5.2 + DRF + Postgres 17 RLS)

Har modul: `models.py` · `services.py` (yozish) · `selectors.py` (o'qish) ·
`serializers.py` · `views.py` · `tests/`. Modullar bir-birining modelini
view'da import qilmaydi — faqat servis/selektor orqali (Invariant 1).

| Modul | Modellar | Nimaga javobgar |
|---|---|---|
| `core` | — | `BaseModel`, `TenantScopedModel`, `BranchScopedModel`, RLS, `organization_context()` / `platform_context()` |
| `accounts` | `User` `Role` `Permission` `RolePermission` `RefreshToken` | JWT, modul×amal RBAC |
| `organizations` / `branches` | `Organization` `Branch` | Tenant ildizi va operatsion doira |
| `children` | `Child` `Guardian` `ChildGuardian` `Group` `Enrollment` | Bola, vasiy, guruh |
| **`finance`** | `TariffPlan` `Discount` `Invoice` `InvoiceLine` `Payment` **`ChildLedgerEntry`** | Pul: hisob-faktura, to'lov, ledger |
| `cash` | `CashAccount` `CashMovement` | Pul QAYERDA (uchinchi ledger, ADR-17) |
| `attendance` | `AttendanceRecord` `Holiday` `AbsenceClaim` | Davomat, bayram, qayta hisob (ADR-19) |
| `hr` / `payroll` | `Position` `Employee` / `PayrollRun` `PayrollItem` `PayrollPayout` `PayoutPart` `EmployeeAdvance` | Xodim va oylik (ADR-18) |
| `inventory` | `Warehouse` `ProductCategory` `Unit` `Product` `Supplier` `StockMovement` | Ombor (ikkinchi ledger) |
| `expenses` | `ExpenseCategory` `Expense` | Chiqim |
| `notifications` | `NotificationTemplate` `Notification` + `providers.py` | SMS/Telegram |
| `reports` | `ReportExport` | Agregatlar, CSV/Excel eksport |
| `intelligence` | `Insight` | Radix AI (deterministik qoidalar, ADR-14) |
| `subscriptions` | `SubscriptionPlan` `Subscription` `UsageSnapshot` `SubscriptionInvoice` `SubscriptionPayment` | Radix'ning o'z hisobi (ADR-11) |
| `platform` | `PlatformUser` `SupportGrant` `Lead` | Vendor konsoli (ADR-10) |
| `settings_app` | `SystemSetting` | JSONB kalit-qiymat sozlamalar |
| `audit` | `AuditLog` | O'zgarmas audit izi |

### Uchta append-only ledger

| Ledger | Savolga javob beradi | Invariant |
|---|---|---|
| `child_ledger_entry` | "Oila qancha qarz?" | balans = Σ debet − Σ kredit |
| `stock_movement` | "Omborda nima bor?" | qoldiq = Σ kirim − Σ chiqim |
| `cash_movement` | "Qaysi qopda qancha pul?" | qoldiq = Σ kirim − Σ chiqim |

Hech birida `UPDATE`/`DELETE` yo'q — tuzatish qarshi yozuv bilan.

### Frontend (React 19 + TS + Vite + TanStack Query)

`src/features/<domen>/{api.ts, pages/, components/}` · server holati faqat
TanStack Query'da · Context'da faqat auth, tashkilot, filial, til, tema.
Brend `tailwind.config.js` + `lib/brand.ts` + `components/brand/Logo.tsx` da (05 §18).

### Fon vazifalari (`config/settings/base.py` `CELERY_BEAT_SCHEDULE`)

| Vaqt | Vazifa |
|---|---|
| 01:00 | `subscriptions.record_daily_peak` |
| 02:00 (oyning 1-kuni) | `finance.generate_monthly_invoices` |
| 03:00 | `finance.mark_overdue_invoices` |
| **03:30** | `intelligence.generate_insights` ← brifing shu yerdan |
| 04:30 | `reports.recompute_balances` |
| **10:00** | `reports.send_debt_reminders` |
| har 5 daq | `notifications.dispatch_queued` |

### Deploy

Docker Compose · Nginx (`deploy/nginx/`: `_shared.conf`, `tls.conf`,
`private-demo.conf`) · Gunicorn · ikki stack: `prod` (`/`) va `private` (`/private`).

---

## 2. Asosiy topilma — nega bitta bola ikki xil qarz ko'rsatadi

Bu 4-bo'limdagi holatlarning **ko'pchiligining bitta ildizi**. Tizimda
"bola qancha qarz?" degan savolga javob beradigan **ikkita mustaqil
hisob** bor:

| Manba | Formula | Qayerda ishlatiladi |
|---|---|---|
| **Ledger** | `Σ debet − Σ kredit` (`finance/selectors.py:debtor_queryset`) | Qarzdorlar, dashboard, bola balansi |
| **Faktura keshi** | `invoice.amount_due − invoice.amount_paid` (`month_board_queryset`) | To'lovlar doskasi, to'lov oynasi, oy yakuni |

`record_payment(invoice=None)` — ya'ni avans — ledger'ga **kredit** yozadi,
lekin hech qaysi fakturaning `amount_paid` iga tegmaydi. Natijada:

```
Ibragimov Robiya
  faktura MAIN-202609-0026   amount_due = 1 500 000   amount_paid = 0  → "To'lanmagan"
  to'lovlar (invoice=NULL)   830 000 + 540 000        → ledger kredit
  ─────────────────────────────────────────────────────────────────────
  To'lovlar doskasi:  1 500 000 − 0        = 1 500 000   ✗
  Qarzdorlar:         1 500 000 − 1 370 000 =   130 000   ✓
```

Ikkala raqam ham "to'g'ri hisoblangan" — faqat ular **boshqa savolga**
javob beryapti. Shuning uchun 1.1 (yagona balans servisi) 1.2 (avans
taqsimoti) dan **oldin** turadi: taqsimot yozuvlari kelganda ikkala
ekran ham ayni bir manbadan o'qishi kerak.

**Ikkinchi ildiz** — `issue_invoice()` bolaning qabul sanasini umuman
ko'rmaydi:

```python
issued   = date(period_year, period_month, 1)          # har doim oyning 1-kuni
due_date = date(period_year, period_month, min(10, …)) # har doim 10-kun
```

30-sentabrda qabul qilingan bola 1-sentabrdan hisoblanadi va fakturasi
yaratilgan kuniyoq 20 kun kechikkan bo'ladi. Q2 (proporsional) va Q3
(muddat) shu joyni almashtiradi.

---

## 3. Bosqichlar

Belgilar: `[ ]` kutilmoqda · `[~]` jarayonda · `[x]` bajarildi

### Bosqich 0 — Tanishuv, reja, qizil testlar `[x]`

- [x] Repo tahlili va arxitektura xaritasi
- [x] `PLAN.md` va `PROGRESS.md`
- [x] 4-bo'limdagi holatlar uchun qizil testlar (`-m big_update`)
- [x] Hozirgi test qamrovi o'lchandi

**Tegilmadi:** hech bir xato tuzatilmadi — bu ataylab.

---

### Bosqich 1 — Moliyaviy to'g'rilik `[x]`

> Eng muhim bosqich. Bu yerdagi xato mijozning pulini noto'g'ri
> ko'rsatadi, ya'ni ishonchni buzadi.

**1.1 Yagona balans servisi** `[x]`
- [x] `finance/balance.py`: `child_balance_detail(child)` → `{charged, allocated, advance, credits, refunds, outstanding, overdue}`
- [x] Doska, to'lov oynasi, qarzdorlar, dashboard, brifing, bola kartasi, hisobot va eksport — hammasi shundan
- [x] Invariant testlar: har bola uchun barcha ekranlarda bitta raqam; tenant yig'indisi = "Jami qarz"
- Fayllar: `apps/finance/{balance.py,selectors.py,views.py}`, `apps/reports/selectors.py`, `apps/intelligence/services.py`, `frontend/src/features/{payments,debtors,dashboard,children}`
- Xavf: **yuqori** — eng ko'p ekranga tegadi. Yumshatish: eski selektorlar o'chirilmaydi, yangi servisga *delegat* qilinadi; invariant test avval yoziladi.

**1.2 Avans taqsimoti (Q1)** `[x]`
- [x] Yangi model `PaymentAllocation` (`payment`, `invoice`, `amount`) — append-only
- [x] `record_payment`: FIFO (eng eski ochiq faktura) → qoldiq avans
- [x] `issue_invoice`: mavjud avansni avtomatik qo'llash
- [x] `reverse_payment`: taqsimotni ham bekor qilish
- [x] To'lov oynasida "To'lanishi kerak / Avans balansi / taqsimot preview" va aniq fakturani tanlash
- [x] `apply_open_credits --tenant --dry-run` — mavjud ma'lumot uchun
- Migratsiya: `finance/00XX_payment_allocation.py` (yangi jadval + backfill **alohida command**, migratsiyada emas)
- Xavf: **yuqori** — `ck_invoice_paid_not_over` cheklovi bilan to'qnashishi mumkin; `select_for_update` tartibi saqlanishi shart.

**1.3 Proporsional birinchi oy va muddat (Q2, Q3)** `[x]`
- [x] `settings_app`: `finance.first_month_mode` (`full`/`prorated`/`next_month`, sukut `prorated`), `finance.payment_day` (sukut 10), `finance.first_invoice_grace_days` (sukut 5)
- [x] `issue_invoice`: ish kunlari bo'yicha proporsiya (`attendance.working_weekdays` + `Holiday`), butun so'mgacha yaxlitlash
- [x] `due_date = max(payment_day, enrolled_on + grace)`
- [x] Faktura qatorida izoh: "Sentabr, 22 ish kunidan 1 kun"
- [x] Qo'lda va avtomatik generatsiya bir xil kod yo'lidan
- Fayllar: `apps/finance/services.py`, `apps/attendance/services_absence.py` (ish kunlari funksiyasi qayta ishlatiladi), `apps/settings_app/services.py`

**1.4 Ommaviy amallarda tasdiq** `[x]`
- [x] `POST /finance/invoices/preview-run` → bolalar soni, jami, o'tkazib yuborilganlar (sababi bilan)
- [x] Frontendda preview → "Tasdiqlash"
- [x] Ro'yxatdagi guruh va tarif o'zgarishi — tasdiq oynasi (Q4: tarif keyingi fakturadan)

**1.5 Mutatsiyadan keyin yangilanish** `[x]`
- [x] `lib/api/queryKeys.ts` da domen darajasidagi invalidatsiya xaritasi
- [x] To'lov, qaytarish, faktura, chiqim, davomat, ombor, oylik — bog'liq so'rovlarni yangilaydi
- Fayllar: `frontend/src/lib/api/queryKeys.ts` + har bir feature'ning mutatsiyalari

**1.6 Brifing va terminologiya** `[x]`
- [x] Brifing jonli servisdan yoki hodisadan keyin qayta hisoblanadi; kartada "holat: HH:MM"
- [x] Terminlar: "Jami qarz" · "Muddati o'tgan qarz (15+ kun)" · "Shu oy qolgan"
- [x] To'lovlar sahifasidagi "Qarzdor" chipi → "Shu oy toʻlanmagan"

**1.7 Kvitansiya** `[x]`
- [x] Raqam, sana, bola, summa, usul, taqsimot, kassir, qolgan qarz/avans
- [x] A4 va 80 mm print, PDF; jurnaldan qayta chop etish
- Eslatma: PDF uchun saqlash abstraksiyasi tayyor (`FileField`), PDF kutubxonasi hali yo'q → **Qaror kerak**

**1.8 To'lovlar jurnali** `[x]`
- [x] Sana oralig'i, usul, bola, kassir filtri; jami; Excel eksport

**1.9 Ombor ↔ chiqim (Q13)** `[x]`
- [x] `StockMovement.expense` (nullable FK) — "Xarid"da katakcha + kassa tanlash (sukut yoqilgan)
- [x] Ikki marta hisoblanmaslik testi
- [x] Miqdor "20 kg" (keraksiz nollarsiz), birlik tarjimasi
- Migratsiya: `inventory/00XX_movement_expense.py`

**1.10 Oylik** `[x]`
- [x] Maftuna nega yo'qligini aniqlash (gipoteza: `build_run` xodimlarni YARATILISH paytida suratga oladi; yakunlangan hisobga keyingi xodim tushmaydi) va tuzatish
- [x] `hired_on` bo'yicha filtr + ishga kirgan oyi proporsional
- [x] Q10 soliqlari: `payroll.income_tax_percent`, `payroll.social_tax_percent` (sukut 0)
- [x] Inputlarda formatlangan raqam

**1.11 Yagona narx moduli** `[x]`
- [x] Platforma konsolidagi `monthlyEstimate` (hardcode `500_000` + `80_000` — ADR-12 gacha bo'lgan narx) olib tashlanadi, backend `pricing.quote()` ishlatiladi
- [x] Testlar: 0, 42, 50, 51, 60, 150 bola
- Fayl: `frontend/src/features/platform/pages/PlatformOrganizationsPage.tsx:41`
- Eslatma: landing kalkulyatori **allaqachon** backend'dan oladi (`/public/pricing`) — u to'g'ri

**1.12 Obuna sahifasi** `[x]`
- [x] "Asosiy narx → Yillik chegirma → Toʻlov" ko'rinishi
- [x] "Hisoblash dalili" inson tilida
- [x] "Qanday toʻlash" banneri (bank rekvizitlari, aloqa)

---

### Bosqich 2 — Bola kartasi, validatsiya, rollar `[x]`

- [x] **2.1** Bola kartasi: tahrirlash, holat, guruh/tarif tasdiq bilan, vasiylar, balans kartochkasi, 7 ta tab
- [x] **2.2** Arxivlash + 24 soatlik xato yozuvni o'chirish (Q6)
- [x] **2.3** Yaratilgach kartaga o'tish, dublikat ogohlantirishi, ixtiyoriy vasiy bloki
- [x] **2.4** Validatsiya (telefon Q7, tug'ilgan sana, summa, yulduzcha, maydon ostidagi xato) + hisobot beruvchi command
- [x] **2.5** To'lgan guruhlar hamma joyda bir xil o'chirilgan
- [x] **2.6** Guruhga tarbiyachi biriktirish + qator darajasidagi ruxsat + davomat tahrirlash chegarasi
- [x] **2.7** Qidiruv: apostrof normalizatsiyasi (Q11), kirill↔lotin
- [x] **2.8** Tizim hisobini xodimga bog'lash

Migratsiyalar: `children/00XX_child_status_change.py` (`status_changed_on`, `status_reason`, `archived_at`), `children/00XX_group_teacher.py`

Xavf: 2.6 dagi qator darajasidagi ruxsat RBAC'ni kengaytiradi — mavjud
modul×amal modelini **buzmasdan** qo'shiladi (yangi tekshiruv qatlami).

---

### Bosqich 3 — Bildirishnomalar va qarzdorlar `[x]`

- [x] **3.1** Eskiz.uz provayderi (token, yuborish, holat, xato) — `providers.py` registriga
- [x] **3.2** Console provayderda sariq "test rejimi" banneri (+ `test_mode` holati, ADR-22)
- [x] **3.3** Yuborish soatlari 08:00–21:00, kuniga 1 eslatma, qayta urinish, SMS soni/xarajat
- [x] **3.4** Shablon muharriri: o'zgaruvchi tugmalari, preview, belgi soni va SMS bo'laklari, uz/ru shablonlar
- [x] **3.5** Qarzdorlar sahifasi: ustunlar, filtrlar, ommaviy eslatma (tasdiq bilan), Excel, jargonni olib tashlash
- [x] **3.6** Yangi lid → Telegram guruh (+ `next_call_at`)
- [x] **3.7** **Telegram — asosiy kanal** (egasining qarori, 2026-10-02): bot, ulash
      havolasi, webhook, kanal bo'yicha provayder, qamrov ko'rsatkichi. SMS adapteri
      joyida qoladi va bitta `.env` qatori bilan yoqiladi.

Env: `ESKIZ_EMAIL`, `ESKIZ_PASSWORD`, `ESKIZ_FROM`, `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_LEADS_CHAT_ID`

Migratsiyalar: `notifications/0003_test_mode_status.py` (faqat `choices`),
`notifications/0004_sms_language.py` (+`language`, unikal cheklov),
`children/0009_sms_language.py` (+`guardian.language`),
`platform/0004_lead_next_call.py` (+`lead.next_call_at`),
`children/0010_guardian_telegram.py` (+`chat_id`, `code`, `linked_at`),
`notifications/0005_notification_kind.py` (+`template_code`),
`notifications/0006_backfill_template_code.py` (mavjud qatorlarga tur)

Buyruqlar: `seed_templates --tenant <slug> [--dry-run]` — mavjud
bog'chalarga yetishmayotgan kanal×til shablonlarini qo'shadi
(migratsiya EMAS: shablon matni mijozning matni);
`set_telegram_webhook --base-url https://… [--dry-run|--info|--delete]`.

Yangi ADR'lar: **ADR-22** — yetkazilmagan xabar "yuborildi" deb
yozilmaydi, yuborish qoidalari sozlamada; **ADR-23** — Telegram asosiy
kanal, SMS bitta `.env` qatori bilan yoqiladigan pullik variant,
ulash kodi tashkilotni o'zida olib yuradi (RLS kengaytirilmaydi).

---

### Bosqich 4 — UI/UX, dizayn, tarjima `[x]`

- [x] **4.1** `lib/format.ts` — yagona uy (Q12) + `DateInput` (dd.mm.yyyy) + apostroflar (Q11)
- [x] **4.2** Ish kunlari katakchalari, har sozlamaning nomi, eksport fayl nomi tilda, CI darvozasi
- [x] **4.3** Jargon almashtirildi (ledger/qoplar/schyot/spravka/zayavka/past_due/registr)
- [x] **4.4** Audit jurnalida UUID o'rniga nomlar + maydon nomlari tarjimada
- [x] **4.5** Yon menyu bo'limlarga ajratildi (Bolalar · Moliya · Xodimlar · Ombor · Tizim)
- [x] **4.6** Bog'cha logotipi (yuklash, sarlavha, login, futer)
- [x] **4.7** Qirqilgan nom, chiqim sanasi, toast, bo'sh holat tugmasi, mobil davomat
- [x] **4.8** A11y: 12px minimum, aria-label, ko'rinadigan fokus, Enter/Esc
- [x] **4.9** Obuna banneri: summa, "Qanday to'lash", kunlik yopish, faqat egasi/direktor

Migratsiya: `organizations/0002_organization_logo.py` (+`logo`)

Yangi qo'riqchi testlar: `lib/i18n/__tests__/apostrophes` (Q11),
`__tests__/a11y` (12px, aria-label, fokus), `config/__tests__/navigation`
(bo'limlar), `lib/__tests__/format` (Q12).

---

### Bosqich 5 — Xavfsizlik, landing, huquqiy, demo `[ ]`

- [x] **5.1** Refresh token → httpOnly cookie, access faqat xotirada, CSRF, yumshoq o'tish
- [x] **5.2** Parolni tiklash (30 daq, rate limit, oshkor qilmaydigan javob)
- [x] **5.3** Login cheklovi (10/15 daq, IP+email, audit)
- [x] **5.4** 2FA: platforma uchun majburiy, tenant egasi uchun ixtiyoriy, zaxira kodlar
- [x] **5.5** Yangi bog'cha: 72 soatlik taklif havolasi, slug validatsiyasi
- [x] **5.6** Nginx: CSP, Permissions-Policy, `/` → 301 `/uz` (ru brauzer → `/ru`), noma'lum yo'l → 404
- [x] **5.7** Landing: bitta shrift, aloqa bloki, demo javobi, mijozlar fikri joyi, 12px, mobil
- [x] **5.8** Huquqiy sahifalar (uz/ru/en) qayta yozish
- [x] **5.9** Zaxira nusxa: `docs/ops/backup.md`, kunlik `pg_dump`, 14 kun (cron o'rnatish — deploy qadami)
- [x] **5.10** Demo tenant seed (`/t/demo`) — boshqa tenantlarga tegmaydi
- [x] **5.11** Test yozuvlarni tozalash command (`--dry-run`, audit izi bilan)
- [x] **5.12** Platforma konsoli: tarjima, grant tarixi, tarif o'zgartirish, faollik

Xavf: **5.1 eng xavfli** — noto'g'ri qilinsa hamma foydalanuvchi chiqib
ketadi. Yumshatish: eski `localStorage` tokeni bir marta cookie'ga
almashtiriladi, keyin o'chiriladi.

---

### Bosqich 6 — FAQAT alohida buyruq bilan `[x]` (dizayn)

- [x] `docs/big-update/phase-6-design.md` — texnik dizayn, **kod yo'q** (2026-10-03; ADR-26…28 taklif, 5 ta egasining qarori)

Implementation started 2026-10-03 on the owner's "6-bosqichni boshla",
branch `big-update/phase-6-code` (based on `big-update/merge-main`).
Notes from here on are in English (owner's request).

Decisions taken under the owner's standing permission (design §7.3):

| # | Question | Decision |
|---|---|---|
| P6-1 | Whose merchant account receives parent payments? | Each kindergarten's own (ADR-26). Radix never holds customer money |
| P6-2 | Who pays the provider commission? | The kindergarten — the parent pays exactly the invoice amount, no surcharge |
| P6-3 | Radix's own merchant account (subscriptions) | `.env` (`RADIX_PAYME_*`, `RADIX_CLICK_*`); empty = button hidden |
| P6-4 | Self-signup and unconverted trials (ADR-28) | Tenant only after e-mail verification; purge of unconverted trials is a `--dry-run` command the owner runs |
| P6-5 | "Your child is absent today" message | Off by default (`notifications.absence_alert`) — confirmed by the owner 2026-10-03; Telegram only |
| P6-6 | Trial length (owner, 2026-10-03) | **15 days** for self-signup too — one trial length |
| P6-7 | Contracts and kitchen (owner, 2026-10-03) | **Frozen**: built and tested, switched off by `FEATURE_CONTRACTS` / `FEATURE_KITCHEN` (default off); no customer needs them yet |

- [x] **6.1** Payme / Click — parent online payment (ADR-26)
- [x] **6.2** Parent bot — balance, invoices, pay button, receipts (+ absence alert, P6-5)
- [x] **6.3** Bot linking by shared phone number (ADR-27)
- [x] **6.4** Subscription online payment
- [x] **6.5** Contract templates — **frozen** (P6-7)
- [x] **6.6** Kitchen / menu → stock consumption — **frozen** (P6-7)
- [x] **6.7** Self-signup with a trial (ADR-28) — 15 days, owner 2026-10-03

---

## 4. Xavflar registri

| # | Xavf | Ehtimol | Ta'sir | Yumshatish |
|---|---|---|---|---|
| R1 | Balans servisi (1.1) mavjud ekranlarni buzadi | O'rta | **Yuqori** | Invariant testlar avval; eski selektor yangi servisga delegat qiladi |
| R2 | Avans taqsimoti (1.2) `ck_invoice_paid_not_over` bilan to'qnashadi | Yuqori | Yuqori | Taqsimot `amount_paid` ni HISOBLAYDI, qo'shmaydi; qizil test avval |
| R3 | Backfill mavjud tenant ma'lumotini buzadi | O'rta | **Juda yuqori** | Faqat `--dry-run` li command; prod nusxasida repetitsiya; ishga tushirishni egasi qiladi |
| R4 | Refresh token ko'chishi (5.1) sessiyalarni yo'qotadi | O'rta | Yuqori | Bir martalik yumshoq migratsiya; rollback rejasi |
| R5 | Migratsiya orqaga qaytmaydi | Past | Yuqori | Har migratsiyada `reverse_code`; toza va seed bazada sinov |
| R6 | RLS yangi jadvalni qamramaydi | O'rta | **Juda yuqori** | `check_rls` har `migrate` dan keyin (hozir 45 jadval) |
| R7 | Tarbiyachi roli (2.6) mavjud RBAC'ni buzadi | Past | Yuqori | Qator darajasi — QO'SHIMCHA qatlam, mavjudini o'zgartirmaydi |
| R8 | Ko'p qiymatli bog'lanish bo'yicha agregat qarzni ko'paytiradi | O'rta | Yuqori | `Subquery` majburiy (`selectors.py` dagi izoh); ko'p fakturali test |

---

## 5. "Qaror kerak" — ochiq savollar

Egasi 2026-10-03 da ruxsat berdi: "o'zing qabul qila oladigan qarorlarni
o'zing qabul qil". Quyidagi jadval — kim va nima qaror qildi.

| # | Savol | Qaror | Kim |
|---|---|---|---|
| D1 | Kvitansiya PDF kutubxonasi | **Kutubxona yo'q** — HTML + brauzer "PDF sifatida saqlash" (A4 va 80 mm allaqachon). WeasyPrint Docker tasviriga tizim kutubxonalarini olib kirardi, foyda esa yo'q | Claude |
| D2/D7 | `apply_open_credits` qaysi tenantlarda | Har bir tenantda, **bittalab**, avval `--dry-run`; ishga tushirish — deploy qadami | Claude (ishga tushirish — egasi) |
| D3 | Eskiz hisobi | Yopildi — Telegram asosiy kanal (ADR-23) | Egasi |
| D4 | Yuridik nom, STIR, manzil, server joylashuvi | `.env` (`LEGAL_*`, `SERVER_LOCATION`) — **qiymatlar egasidan** | Egasi |
| D5 | Telegram lid guruhi chat id | `.env` — egasidan | Egasi |
| D6 | Oylik soliq sukuti 0 ga tushdi | `pin_legacy_payroll_rates` — eski 12 % / 0,1 % ga tayangan tashkilotda ochiq yozadi (sukut dry-run) | Claude |
| D8 | To'lov rekvizitlari | `.env` — egasidan | Egasi |
| D9 | Tarbiyachilarni guruhga biriktirish | Kod emas — bog'chaning o'z sozlamasi (Guruh → tarbiyachi). Biriktirilmaguncha cheklov inert (ADR-21) | Claude |
| D10 | Tarbiyachi davomat oynasi | **1 kun** qoladi (bugun + kecha); sozlama orqali o'zgaradi | Claude |
| D11 | Ikkinchi telefon | `+998947267726` | Egasi |
| D12 | Huquqiy matn raqamlari (12 oy, 30 kun, 3 oy) | Tasdiqlandi | Egasi |
| D13 | Google Fonts | O'z serverimizga ko'chirildi | Egasi |
| D14 | HSTS `preload` | **Qo'shilmaydi** — undan chiqish oylab cho'ziladi, foydasi `max-age` dan ozgina ortiq | Claude |
| D15 | Ildizdagi `/login`, `/reset-password`, `/invite` | 404 emas, SPA — email havolalari va landing'dagi kirish tugmasi shu yerga olib boradi | Claude |

---

## 6. Tayyorlik mezonlari (7-bo'lim)

- [x] Barcha testlar yashil; yangi moliyaviy kodda qamrov ≥90% (o'lchandi: **94 %**)
- [x] Invariant testlar bor va ishlaydi
- [x] uz/ru/en to'liq; yetishmayotgan kalit CI'da ushlanadi
- [x] Migratsiyalar toza va seed bazada ishladi; rollback tekshirildi
- [x] 1-bo'limdagi mavjud funksiyalar buzilmadi
- [x] 375px va 1280px kengliklarda tekshirildi (landing + 16 ilova sahifasi, haqiqiy login bilan)
- [x] `CHANGELOG.md` yangilandi
