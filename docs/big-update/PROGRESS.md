# Katta yangilanish — bajarilgan ish

> Yangi sessiya shu fayldan davom etadi. Reja `PLAN.md` da.
> Har yozuv: **sana · bosqich · nima qilindi · commit · natija.**

---

## 2026-09-30 — Bosqich 0 bajarildi

**Branch:** `big-update/phase-0`

### Qilingan ish

| Band | Natija |
|---|---|
| Repo tahlili | 20 backend modul, 22 frontend feature, 3 append-only ledger, 8 rejalashtirilgan vazifa — xarita `PLAN.md` §1 da |
| Asosiy ildiz topildi | Qarz **ikki xil** hisoblanadi: ledger va faktura keshi. Avans ledger'ga tushadi, fakturaga tushmaydi → doska 1 500 000, Qarzdorlar 130 000 (`PLAN.md` §2) |
| Ikkinchi ildiz topildi | `issue_invoice()` qabul sanasini ko'rmaydi: `issued` doim oyning 1-kuni, `due_date` doim 10-kun → 30.09 da qabul qilingan bola 20 kun kechikkan bo'lib tug'iladi |
| `PLAN.md` | 0–6 bosqichlar, fayllar, 8 ta xavf, 5 ta "Qaror kerak" |
| Qizil testlar | **40 ta**: backend 37 (`-m big_update`, `xfail(strict=True)`), frontend 3 (`it.fails`) |
| Qamrov o'lchandi | Backend 893 test o'tdi, `apps/` qamrovi **90,3 %**; frontend 99 test |
| Ikkita test rad etildi | `strict` rejim ikkita testni XPASS deb ushladi — ular Django obyektiga
ixtiyoriy atribut o'zlashtirib, hech narsani isbotlamasdi. Sxema ustidan
(`Child._meta.get_field`) qayta yozildi. |

### Qizil testlarning holati

Hammasi `@pytest.mark.xfail(strict=True)` bilan: **hozir yiqiladi** (xato
takrorlandi), lekin CI yashil qoladi. Tuzatilgach `XPASS` bo'ladi va
`strict=True` uni **xato** deb belgilaydi — ya'ni marker'ni olib tashlashga
majbur qiladi. Unutib qo'yish mumkin emas.

```
pytest -m big_update -rx        # backend: qaysilari hali qizil
npx vitest run src/features/platform/__tests__/pricing.test.ts   # frontend
```

**Modul kesimida:** finance 10 · children 12 · notifications 7 · payroll 5 ·
inventory 3 · frontend (platforma narxi) 3.

### Baza qamrov (modul kesimida)

| Modul | Qamrov | Modul | Qamrov |
|---|---|---|---|
| inventory | 95,1 % | subscriptions | 84,1 % |
| audit | 95,7 % | expenses | 84,4 % |
| settings_app | 94,0 % | reports | 81,0 % |
| payroll | 93,5 % | notifications | 80,8 % |
| children | 91,9 % | branches | 82,1 % |
| accounts | 90,8 % | **finance** | **85,7 %** |
| cash | 89,7 % | platform | 85,5 % |
| attendance | 88,5 % | core | 59,8 % |
| organizations | 98,6 % | intelligence | 86,3 % |

`core` past ko'rinadi, chunki unga RLS migratsiya yordamchilari kiradi —
ular `migrate` paytida ishlaydi, testda emas.

### Sifat darvozalari (bosqich oxirida)

| Tekshiruv | Natija |
|---|---|
| `pytest` | 893 o'tdi · 37 xfailed · 0 xato |
| `ruff check` / `ruff format` | toza |
| `mypy` | 267 faylda muammo yo'q |
| `makemigrations --check` | o'zgarish yo'q |
| `tsc --noEmit` | toza |
| `eslint` | 0 xato (20 ta ogohlantirish — baseline) |
| `vitest` | 102 o'tdi (99 + 3 yangi qizil) |

### Tegilmagan narsalar

Hech bir xato tuzatilmadi, hech bir migratsiya yozilmadi, production'ga
tegilmadi — 0-bosqich shartiga ko'ra.

### Keyingi qadam

1-bosqich, **1.1 dan boshlanadi** (yagona balans servisi): u 1.2 (avans
taqsimoti) uchun poydevor. Egasining "davom et" signali kutilmoqda.


---

## 2026-10-01 — Bosqich 1 bajarildi (moliyaviy to'g'rilik)

**Branch:** `big-update/phase-1` · commitlar `d7341d0` … `2b48fdd`

### Ikki ildiz sabab yopildi

**① Qarz ikki xil hisoblanardi.** Endi `payment_allocation` qaysi pul
qaysi hisob-fakturani yopganini yozadi, `invoice.amount_paid` esa shu
qatorlar ustidagi kesh. Formula `apps/finance/balance.py` da va faqat
o'sha yerda — doska, qarzdorlar, bola kartasi, bosh sahifa, brifing va
hisobotlar hammasi shundan o'qiydi (ADR-20).

**② `issue_invoice()` qabul sanasini ko'rmasdi.** Endi birinchi oy ish
kunlari bo'yicha proporsional, muddat esa `max(to'lov kuni, qabul + 5
kun)`. `finance.due_day` sozlamasi e'lon qilingan-u, hech qayerda
o'qilmasdi — endi o'qiladi.

### Bandlar

| Band | Holat | Natija |
|---|---|---|
| 1.1 Yagona balans servisi | ✅ | `balance.py`; `balance`/`advance`/`outstanding` alohida nomlangan; invariant testlar |
| 1.2 Avans taqsimoti (Q1) | ✅ | `payment_allocation`, FIFO, auto-apply, qaytarishda bo'shatish, `apply_open_credits` |
| 1.3 Proporsional oy va muddat (Q2,Q3) | ✅ | Ish kunlari, bayramlar, 3 ta sozlama, satr izohi |
| 1.4 Ommaviy amallarda tasdiq | ✅ | `preview-run` + dialog; guruh/tarif uchun `ConfirmDialog` |
| 1.5 Mutatsiyadan keyin yangilanish | ✅ | `lib/api/invalidate.ts` |
| 1.6 Brifing va atamalar | ✅ | `generated_at` + jonli `totals`; "Jami qarz", "Shu oy toʻlanmagan" |
| 1.7 Kvitansiya | ✅ | A4 va 80 mm, taqsimot bilan, qayta chop etish |
| 1.8 To'lovlar jurnali | ✅ | Sana/usul/bola/kassir filtri, sahifasiz yig'indi, eksport bir xil filtrda |
| 1.9 Ombor ↔ chiqim (Q13) | ✅ | `stock_movement.expense`, kassa tanlash, `quantity_text` |
| 1.10 Oylik | ✅ | `missing_employees`, `eligible_employees`, proporsiya, Q10 soliqlari |
| 1.11 Yagona narx moduli | ✅ | `lib/pricing.ts`; backend testi ikkalasini bog'laydi |
| 1.12 Obuna sahifasi | ✅ | Uch qatorli hisob, inson tilidagi dalil, "Qanday toʻlash" |

### Maftuna holati — sabab

`create_run()` xodimlarni hisob YARATILGAN ondagi ro'yxatdan suratga
oladi. Keyin qo'shilgan xodim qoralamaga `recalculate_run()` bilan
tushadi, lekin hisob yakunlangan bo'lsa hech narsa qilib bo'lmaydi —
va, eng yomoni, tushib qolgani hech qayerda ko'rinmaydi. Endi
`missing_employees(run)` buni aytadi.

### Sifat darvozalari

| Tekshiruv | Natija |
|---|---|
| `pytest` | 975 o'tdi · 19 xfailed (2–5 bosqichlar) · 0 xato |
| `ruff` / `ruff format` / `mypy` | toza |
| `makemigrations --check` | o'zgarish yo'q |
| `tsc` / `eslint` / `vitest` / `build` | toza · 111 test |
| `check_rls` | 46 jadval |

### Migratsiya repetitsiyasi

Seed ma'lumotli bazada (30 bola, 4 oy, 120 faktura, 112 to'lov):
- backfill 112 ta taqsimot yaratdi — bog'langan to'lovlar soniga teng;
- 120 fakturaning hammasida kesh ↔ taqsimot mos;
- **jami qarz 13 461 000 — backfilldan oldin ham, keyin ham bir xil**;
- ikkinchi marta ishga tushirish dublikat yaratmadi;
- to'liq orqaga qaytarish va qayta oldinga yurish ishladi, `check_rls` toza.

### Xatti-harakat o'zgarishlari (deployda e'tibor bering)

1. **Ortiqcha to'lov endi rad etilmaydi** — ortig'i avansga aylanadi (Q1).
2. **`payroll.income_tax_rate` va `payroll.pension_rate` sukut qiymati
   12 % va 0.1 % dan 0 ga tushdi** (Q10). Sozlamani ATAYLAB
   o'rnatgan bog'chalarga ta'sir qilmaydi; yakunlangan hisoblar
   suratda saqlanadi. Sozlamaga hech qachon tegmagan bog'cha bor
   bo'lsa, deploydan oldin qiymatni ochiq o'rnatish kerak.
3. **Narxi ko'rsatilgan ombor xaridi endi chiqim yaratadi** (Q13,
   sukut yoqilgan). Eski harakatlarga teginilmaydi.

### Keyingi qadam

2-bosqich: bola kartasi, validatsiya, rollar. Egasining "davom et"
signali kutilmoqda.


---

## 2026-10-01 — Bosqich 2 bajarildi (bola kartasi, validatsiya, rollar)

**Branch:** `big-update/phase-2` · commitlar `0d40899` … `ef9d4e5`

### Bandlar

| Band | Holat | Natija |
|---|---|---|
| 2.1 Bola kartasi | ✅ | Hisob kartochkasi, tahrirlash, holat, vasiylar, 3 ta tab, tibbiy maydonlar |
| 2.2 Arxiv va xato yozuv (Q6) | ✅ | `archived_at`/`archived_by`; `DELETE` = arxiv; `hard-delete` 24 soat oynasida |
| 2.3 Yaratish oqimi | ✅ | Kartaga o'tish, dublikat ogohlantirishi, ixtiyoriy vasiy bloki |
| 2.4 Validatsiya (Q7) | ✅ | `PhoneField` hamma joyda, yosh oralig'i, `report_bad_phones` |
| 2.5 To'lgan guruh | ✅ | `GroupOptions` — uchta select bitta qoidadan |
| 2.6 Tarbiyachi doirasi | ✅ | `children/scope.py` (ADR-21), davomat oynasi |
| 2.7 Qidiruv (Q11) | ✅ | `search_key`: apostrof, kirill↔lotin, `x`↔`h`, telefon |
| 2.8 Hisob ↔ xodim | ✅ | Mavjud `Employee.user` ishlatildi, UI qo'shildi |

### Ikkita qaror, sababi bilan

**Cheklov "ruxsat yo'q" dan emas, FAKTDAN kelib chiqadi.** Qator
darajasidagi doira uch shart bilan yoqiladi va uchinchisi hal
qiluvchi: foydalanuvchi **aynan birorta guruhning tarbiyachisi**
bo'lishi kerak. Aks holda ruxsatlari tor har qanday maxsus rol
(tashqaridan kelgan buxgalter) kutilmaganda hech narsa ko'rmay
qolardi — hech kim bunday qaror qabul qilmagan holda. Ya'ni qatlam
hech kim biriktirilmaguncha umuman ishlamaydi.

**Telefon modelda `CHECK` bilan qo'riqlanmaydi.** Mavjud tenantlarda
allaqachon noto'g'ri raqamlar bor va cheklov ularni saqlashni
to'xtatib qo'yardi — ya'ni bolaning kartasini saqlab bo'lmaydigan
holat. Ular uchun `report_bad_phones` faqat ro'yxat beradi: "12345"
o'rniga nima yozish kerakligini tizim bilmaydi, taxmin qilib yozish
esa SMS'ni butunlay boshqa odamga yuborardi.

### Sifat darvozalari

| Tekshiruv | Natija |
|---|---|
| `pytest` | 1057 o'tdi · 7 xfailed (3-bosqich) · 0 xato |
| `ruff` / `ruff format` / `mypy` | toza |
| `tsc` / `eslint` / `vitest` / `build` | toza · 111 test |
| `check_rls` | 46 jadval |

### Migratsiya repetitsiyasi

Seed ma'lumotli bazada (20 bola, 3 oy): qidiruv kaliti 20/20 bolaga
va 20/20 vasiyga to'ldi; telefon raqamlarining hammasi to'g'ri
formatda; `children 0003` gacha orqaga qaytarish va qayta oldinga
yurish ishladi, `check_rls` toza.

### Xatti-harakat o'zgarishlari (deployda e'tibor bering)

1. **`DELETE /children/{id}` endi ARXIVLAYDI** (ilgari `is_active=False`
   qilardi — natija o'xshash, lekin endi "kim, qachon" ko'rinadi).
2. **Noto'g'ri formatdagi telefon qabul qilinmaydi.** Mavjud
   yozuvlarga tegilmaydi; deploydan keyin `report_bad_phones` ni
   ishga tushirib, ro'yxatni mudiraga bering.
3. **Tarbiyachi davomat oynasi** — sukut 1 kun (bugun va kecha).
   Hech kim guruhga biriktirilmagan bo'lsa, hech narsa o'zgarmaydi.

### Keyingi qadam

3-bosqich: bildirishnomalar va qarzdorlar (Eskiz.uz, yuborish oynasi,
shablonlar, qarzdorlar ekrani). Egasining "davom et" signali
kutilmoqda.

---

## 2026-10-01 — Bosqich 3 bajarildi

**Branch:** `big-update/phase-3` · **Commitlar:** `754a235`, `6a8b145`,
`f1f84a4` (+ shu yozuv)

### Nima tuzatildi

Auditning eng jimgina xatosi bitta jumlada: **jurnal "Yuborildi" deb
turardi, ota-ona esa hech narsa olmagan edi.** Hatto `12345` raqamiga
yuborilgan xabar ham muvaffaqiyatli ko'rinardi. Bu turdagi xato eng
yomoni, chunki u ishonchli ko'rinadi: bog'cha eslatmalar ketayotganiga
ishonib turadi va bir oydan keyin "nega hech kim to'lamadi?" deb
so'raydi.

| Band | Holat | Natija |
|---|---|---|
| 3.1 Eskiz.uz | ✅ | Token keshda (20 kun), `401` da bir marta yangilanadi, xato matni jurnalda; `ESKIZ_FROM` bo'lmasa provayder ishga tushmaydi |
| 3.2 Test rejimi | ✅ | `NotificationStatus.TEST_MODE` + yopilmaydigan sariq banner (Bildirishnomalar va Sozlamalar) |
| 3.3 Qoidalar | ✅ | Yuborish oynasi 08:00–21:00, kuniga 1 eslatma, qayta urinish soni, oylik SMS soni va taxminiy xarajat |
| 3.4 Shablon muharriri | ✅ | O'zgaruvchi tugmalari, jonli belgi/bo'lak hisoblagichi, serverdagi preview, uz/ru shablonlar |
| 3.5 Qarzdorlar | ✅ | Kechikkan kunlar, oxirgi eslatma, guruh/15+/30+/60+/summa filtrlari, saralash, Excel, qator va ommaviy eslatma (tasdiq bilan) |
| 3.6 Telegram | ✅ | Yangi ariza → sotuv chatiga xabar; lead'ga `next_call_at` |

### Uchta qaror, sababi bilan

**"Test rejimi" — muvaffaqiyatning ko'rinishi emas, alohida holat.**
`sent` degan so'z bitta ma'noga ega bo'lishi kerak: shlyuz xabarni
yetkazish uchun qabul qildi. Console provayder hech narsa yetkazmaydi,
shuning uchun uning natijasi `test_mode` — va ekran buni banner bilan
aytadi. Banner yopilmaydi: u eslatma emas, tizim holati.

**Oyna tashqarisidagi xabar yo'qolmaydi, navbatda qoladi.** Tungi SMS
ota-onani uyg'otadi; qarz eslatmasi esa ertalabgacha kutsa hech narsa
yo'qotmaydi. Shuning uchun `dispatch` xabarni o'chirmaydi ham,
yubormaydi ham — `queued` holatida qoldiradi va ertalabki dispatcher
oladi. Vazifa natijasida ular `held` deb sanaladi, `failed` emas:
monitoringda soxta signal bo'lmasligi kerak.

**Buzuq filtr xato beradi, jimgina olib tashlanmaydi.** `group_id`
noto'g'ri bo'lsa `None` qilib tashlash "shu guruhga yuboraman" ni
"hammaga yuboraman" ga aylantirardi — va mudira buni SMS ketgandan
keyin bilardi. Endi bu `422`.

### Sifat darvozalari

| Tekshiruv | Natija |
|---|---|
| `pytest` | **1106 o'tdi** · 0 xfail (3-bosqichning 7 tasi tuzatildi) · 0 xato |
| `ruff` / `ruff format` / `mypy` | toza (274 fayl) |
| `tsc` / `eslint` / `vitest` / `build` | toza · **122 test** |
| `check_rls` | 46 jadval |
| `makemigrations --check` | o'zgarish yo'q |

### Migratsiya repetitsiyasi

Urug'langan nusxada (`kg_crm_qa`: 25 bola, 193 ledger yozuvi, 105
xabar, balans **12 919 000**):

1. uchta yangi migratsiya qo'llandi → raqamlar o'zgarmadi, mavjud
   shablonlar `uz` bo'lib qoldi, vasiylarning tili bo'sh (= bog'cha
   tili);
2. uchalasi **teskari** qaytarildi — toza;
3. qayta oldinga yurildi → o'sha raqamlar, `check_rls` 46 jadval.

`seed_sms_templates --all --dry-run` 3 ta shablon qo'shilishini
ko'rsatdi va **hech narsa yozmadi**; haqiqiy ishga tushirishdan keyin
ikkinchi marta 0 ta qo'shdi (idempotent), tahrirlangan o'zbekcha
matnga tegmadi.

### Deployda e'tibor bering

1. **Jurnalda yangi holat — "Test rejimi".** Eski `sent` qatorlari
   o'zgarmaydi; `NOTIFICATION_PROVIDER=console` turganda yangi
   xabarlar `test_mode` bo'ladi. Bu xato emas, haqiqat.
2. **Eskiz uchun uchta `.env` kaliti kerak** (`ESKIZ_EMAIL`,
   `ESKIZ_PASSWORD`, `ESKIZ_FROM`) va `NOTIFICATION_PROVIDER=eskiz`.
   Uchalasidan biri bo'lmasa provayder ishga tushmaydi — xabar
   `failed` bo'ladi va sababi jurnalda turadi.
3. **Telegram ixtiyoriy**: `TELEGRAM_BOT_TOKEN` va
   `TELEGRAM_LEADS_CHAT_ID` bo'sh bo'lsa ariza baribir saqlanadi.
4. **Ruscha shablonlar avtomatik qo'shilmaydi.** Mavjud bog'chalar
   uchun `seed_sms_templates --tenant <slug>` ni EGASI ishga tushiradi
   (avval `--dry-run`).
5. **Narx ko'rsatilishi uchun** `notifications.sms_price` sozlamasiga
   provayder shartnomasidagi raqamni kiriting; 0 bo'lsa xarajat
   ko'rsatilmaydi.

### Keyingi qadam

4-bosqich: UI/UX, dizayn, tarjima. Egasining "davom et" signali
kutilmoqda.

---

## 2026-10-02 — Bosqich 3.7: Telegram asosiy kanal

**Branch:** `big-update/phase-3` · **Commitlar:** `4a53491`, `94fe86d`
(+ shu yozuv)

### Nega

Egasining qarori: **hozircha SMS provayderi emas, faqat Telegram bot.**
Sababi sof amaliy — SMS har xabar uchun pul turadi, shlyuz
shartnomasini va tasdiqlangan jo'natuvchi nomini talab qiladi;
Telegram bepul va O'zbekistonda deyarli har bir ota-onada bor.

Eskiz adapteri **o'chirilmadi**: u joyida qoladi va bitta `.env`
qatori bilan yoqiladi. Kanal tanlovi tijorat qarori, kod qarori emas —
va 3.1–3.3 da qurilgan adapter aynan shu uchun qurilgan edi.

| Ish | Natija |
|---|---|
| `TelegramProvider` | `chat_id` ga yuboradi, `parse_mode` siz; "bloklangan" va "chat topilmadi" odam tiliga o'giriladi |
| Kanal bo'yicha provayder | Telegram tokendan, SMS `NOTIFICATION_PROVIDER` dan; `is_test_mode(channel)` |
| `resolve_channel` | Telegram ulangan bo'lsa Telegram; SMS faqat HAQIQATAN ulangan bo'lsa |
| Ulash havolasi | `t.me/<bot>?start=<kod>`, bir martalik, bola kartasidan |
| Webhook | maxfiy yo'l + sarlavha, `/start` va `/stop`, har doim `200` |
| `template_code` | kunlik chegara shablon FK'siga tayanmaydi; 105 qator to'ldirildi |
| Qamrov | nechta ota-ona ulangan — bannerda va holat endpointida |
| Narx | faqat SMS; Telegram "bepul" deb turadi |

### Uchta qaror, sababi bilan

**Ulash kodi tashkilotni O'ZIDA olib yuradi.** Bot `/start` ni
tashkilot kontekstisiz oladi, ya'ni vasiyni topish uchun RLS
chegarasidan chiqish kerak bo'lardi. Bu ishlamaydi ham: operatsion
jadvallar uchun platforma rejimida chiqish yo'li ATAYLAB yo'q
(ADR-10). Siyosatni kengaytirish — eng noto'g'ri yechim bo'lardi:
qulaylik uchun eng kuchli izolyatsiya kafolatini almashtirish. Kodga
tashkilot UUID'ini joylash savolni butunlay yo'q qildi — webhook
kodni ochadi, to'g'ri kontekstni o'rnatadi va qidiruv shu chegara
ichida bo'ladi. Soxta kod faqat o'zi ko'rsatgan tashkilotga tegishi
mumkin, va u yerda 64 bitlik tasodifiy qismdan o'tolmaydi.

**Zaxira kanal avtomatik EMAS.** Telegram ulanmagan ota-onaga SMS
yuborish faqat SMS provayderi haqiqatan ulangan bo'lsa ma'noli. Test
rejimidagi SMS'ga "tushib qolish" jurnalda xabar bordek ko'rsatib,
bog'chani ota-onani botga ulash kerakligidan bexabar qoldirardi —
ya'ni ADR-22 tuzatgan xatoning aynan o'zi, boshqa eshikdan.

**Kod bir martalik.** Havola oilaviy guruhga tashlanishi mumkin,
xabarlar ichida esa bolaning ismi va qarz summasi ketadi. Yangi
havola bir bosishda yaratiladi va eskisi darhol ishlamay qoladi.

### Sifat darvozalari

| Tekshiruv | Natija |
|---|---|
| `pytest` | **1137 o'tdi** · 0 xato (45 ta yangi test) |
| `ruff` / `ruff format` / `mypy` | toza (278 fayl) |
| `tsc` / `eslint` / `vitest` / `build` | toza · **128 test** |
| `check_rls` | 46 jadval (yangi jadval yo'q) |
| `makemigrations --check` | o'zgarish yo'q |

### Migratsiya repetitsiyasi

Urug'langan nusxada (25 bola, 105 xabar, balans **12 919 000**):
uchta migratsiya qo'llandi → raqamlar o'zgarmadi, 105 xabarning
hammasiga turi yozildi (93 kvitansiya + 12 eslatma), turi bo'sh
qolgan qator **0**; teskari qaytarildi — toza; qayta oldinga yurildi →
o'sha raqamlar. `seed_templates --all --dry-run`: 6 ta Telegram
shabloni qo'shilishini ko'rsatdi va hech narsa yozmadi.

### Deployda e'tibor bering

1. **`.env` ga to'rt kalit**: `TELEGRAM_BOT_TOKEN`,
   `TELEGRAM_BOT_USERNAME`, `TELEGRAM_WEBHOOK_SECRET` (tasodifiy 32+
   belgi), `TELEGRAM_LEADS_CHAT_ID`. `NOTIFICATION_PROVIDER` ni
   `console` qoldiring — SMS o'chirilgan bo'ladi.
2. **Webhook'ni ro'yxatdan o'tkazing**:
   `python manage.py set_telegram_webhook --base-url https://radix-crm.uz`
   (avval `--dry-run`, keyin `--info` bilan tekshiring).
3. **Shablonlar**: `python manage.py seed_templates --tenant <slug>
   --dry-run`, keyin haqiqiy ishga tushirish. Telegram matnlari
   SMS'dan uzunroq — u yerda belgi bepul.
4. **Ota-onalarni ulash** — bu bir martalik tashkiliy ish: har bir
   bola kartasida "Ulash havolasi" tugmasi bor. Hech kim ulanmaguncha
   bannerda qamrov 0/N bo'lib turadi va bu to'g'ri: xabar hech kimga
   bormaydi.
5. **SMS kerak bo'lsa** — `NOTIFICATION_PROVIDER=eskiz` + uchta
   `ESKIZ_*` kaliti va Sozlamalarda "Asosiy kanal" ni `SMS` ga
   o'tkazish. Kod o'zgarishi kerak emas.

### Keyingi qadam

4-bosqich: UI/UX, dizayn, tarjima. Egasining "davom et" signali
kutilmoqda.

---

## 2026-10-02 — Bosqich 4 bajarildi

**Branch:** `big-update/phase-4` · **Commitlar:** `a19f82c`, `c62abae`,
`a3005f9`, `1c089c1`, `d325d7c`, `799353b`, `88b17c7`, `69ef1b3`,
`5f38a6e`, `5e09d9d` (+ shu yozuv)

### Nima tuzatildi

| Band | Natija |
|---|---|
| 4.1 Formatlash | `lib/format.ts` — yagona uy; guruhlash Q12 bo'yicha; `DateInput` (dd.mm.yyyy); apostroflar Q11 bo'yicha |
| 4.2 Tarjima tozaligi | Ish kunlari katakchalari, 9 nomsiz sozlamaga nom, eksport fayl nomi tilda, CI darvozasi |
| 4.3 Jargon | ledger / qoplar kesimi / schyot-faktura / Spravka / Zayavka / past_due / "TARBIYACHI" |
| 4.4 Audit jurnali | UUID o'rniga nom (bir so'rovda), maydon nomlari tarjimada, "enrollment" → "Guruhga biriktirish" |
| 4.5 Yon menyu | Bolalar · Moliya · Xodimlar · Ombor · Tizim |
| 4.6 Brend | Bog'cha logotipi: yuklash, sarlavha, login, futer |
| 4.7 Tuzatishlar | Qirqilgan nom, chiqim sanasi, toast, bo'sh holat tugmasi, mobil davomat |
| 4.8 A11y | 12px minimum, 34 tugma + 20 maydonga nom, ko'rinadigan fokus, Enter/Esc |
| 4.9 Obuna banneri | Summa, "Qanday to'lash", kunlik yopish, faqat egasi/direktor |

### To'rtta qaror, sababi bilan

**Formatlash bitta uyga yig'ildi.** O'n yettita `money()` nusxasi bir-
biridan farq qilardi: biri `Math.round`, biri yo'q; `lib/utils.ts`
`en-US` vergul bilan formatlardi, sahifalar `uz-UZ` bo'shliq bilan.
Ya'ni bitta summa ikki ekranda ikki xil ko'rinishi mumkin edi. Eski
nomlar (55 import joyi) yangi uyga yo'naltirildi — tegilmadi.

**Guruhlash `Intl` ga qoldirilmadi.** `Intl` ning natijasi brauzer va
Node versiyasiga bog'liq; server bilan ekran farq qilsa, "nusxa olib
tekshirdim, boshqacha" degan shikoyat paydo bo'ladi.

**Apostrof normalizatsiyasi 1200+ satrni qamradi va chegara sharti
bilan qilindi** — faqat harf—apostrof—harf. Shu sababli `'{status}'`
kabi qo'shtirnoq vazifasidagi apostrofga tegilmadi. Uchta takroriy
lug'at kaliti ochildi: ular avval faqat apostrof turi bilan farq
qilardi.

**Landing sahifasining mayda yozuvlari 12px qoidasidan CHETDA.**
Ulardagi 10–11px matn namunaviy ekran TASVIRINING bir qismi
(`ui/Mock.tsx`), o'qiladigan matn emas — kattalashtirish tasvirni
buzadi. Qoida ilovaga tegishli.

### Sifat darvozalari

| Tekshiruv | Natija |
|---|---|
| `pytest` | **1155 o'tdi** · 0 xato |
| `ruff` / `ruff format` / `mypy` | toza (281 fayl) |
| `tsc` / `eslint` / `vitest` / `build` | toza · **183 test** (0-bosqichda 99 edi) |
| `check_rls` | 46 jadval |
| `makemigrations --check` | o'zgarish yo'q |

### Yangi qo'riqchi testlar

Bu to'rtta qoida bir marta tuzatilib qo'riqlanmasa, ertami-kechmi
qaytadi — ular hech qanday funksiyani buzmaydi:

* `lib/i18n/__tests__/apostrophes` — `t()`, lug'at, landing, valyuta;
* `__tests__/a11y` — 12px, `aria-label`, placeholder, fokus;
* `config/__tests__/navigation` — menyu bo'limlarining to'liqligi;
* `lib/__tests__/format` — Q12 (guruhlash, valyuta, sana, bo'sh qiymat).

Backend tomonda: `apps/core/tests/test_i18n.py` ga ikkita apostrof
darvozasi qo'shildi (`gettext` manbalari va `.po` msgid'lari).

### Migratsiya repetitsiyasi

`organizations/0002_organization_logo` urug'langan nusxada qo'llandi,
teskari qaytarildi va qayta qo'llandi: 25 bola, balans 12 919 000 —
o'zgarmadi; `check_rls` 46 jadval.

### Deployda e'tibor bering

1. **Eksport fayl nomlari o'zgardi**: `revenue-20261002-1030.xlsx` →
   `tushum_2026-10-02_10-30.xlsx` (so'rov tilida). Eski fayllar
   o'z nomi bilan qoladi.
2. **Sana maydonlari endi matn** (`dd.mm.yyyy`) — brauzer kalendari
   tugma ortida. Mobil brauzerda ham ishlaydi.
3. **Obuna banneri faqat egasi va direktorga ko'rinadi.** Ilgari
   matn hammaga ko'rinardi.
4. **Logotip ixtiyoriy**: yuklanmasa bosh harf ko'rsatiladi, hech
   qanday bo'sh joy qolmaydi. `media/` papkasiga yozish huquqi kerak
   (u allaqachon bor — foydalanuvchi rasmlari shu yerda).
5. Migratsiyadan keyin `check_rls` — har doimgidek.

### Keyingi qadam

5-bosqich: xavfsizlik, landing, huquqiy sahifalar, demo. Egasining
"davom et" signali kutilmoqda.

---

## 2026-10-02 — Bosqich 5 bajarildi (xavfsizlik, landing, huquqiy, demo)

Branch: `big-update/phase-5`. Barcha 12 band yopildi.

| Band | Natija |
|---|---|
| 5.1 | Refresh token `httpOnly` cookie'da, access faqat xotirada, CSRF (double submit), eski tokenlar bir marta yumshoq o'tadi |
| 5.2 | Parolni tiklash: 30 daqiqa, bir martalik, javob email borligini aytmaydi, barcha sessiyalar yopiladi |
| 5.3 | Kirish cheklovi hisob bo'yicha (10/15 daq, IP + email), blok auditda |
| 5.4 | 2FA (ADR-24): vendor uchun sukut bo'yicha yoqilgan, mijoz uchun ixtiyoriy, 10 ta zaxira kodi; TOTP `core/` ga ko'chdi |
| 5.5 | Vendor parol yozmaydi — 72 soatlik taklif havolasi; slug qat'iy tekshiruvi |
| 5.6 | nginx: CSP, Permissions-Policy, `/` → `/uz` (`ru` → `/ru`), haqiqiy 404; SPA ro'yxati `router.tsx` bilan test orqali qotirilgan |
| 5.7 | Landing: bitta shrift, aloqa bloki, "24 soat" + Telegram, 12px, telefonda 26 590 → 12 924 px |
| 5.8 | Maxfiylik siyosati va shartlar qayta yozildi (uz/ru/en), `{{…}}` rekvizitlar `.env` dan |
| 5.9 | `docs/ops/backup.md`, `install-backup-cron.sh` (dry-run sukut) |
| 5.10 | `seed_demo_tenant` — `/t/demo`, faqat `demo` slug'i |
| 5.11 | `cleanup_test_records` — sukut dry-run, qarshi yozuvlar bilan |
| 5.12 | Konsol: tarjima, ruxsatlar tarixi, reja/davr o'zgartirish, faollik, taxminiy oylik |

### Yo'lda topilgan va tuzatilgan xatolar

* **Offboarding (`purge_organization`) har bir haqiqiy mijozda
  yiqilardi** — `TariffPlan` bolalardan oldin o'chirilardi, `Child.tariff`
  esa `RESTRICT`. Testlar tarifsiz bola bilan ishlagani uchun ko'rmagan.
  Demo tenantni qayta tiklash birinchi bo'lib ushladi.
* `seed_demo` davomati faqat bugungi kunni yozardi — `mark_bulk` o'tgan
  kun uchun sabab talab qiladi, xato esa faqat log'ga tushardi.
* Docker `ARG` e'lon qilinmagan build argumentlarini jimgina tashlardi:
  `VITE_PUBLIC_HOST`, `VITE_LEGAL_ENTITY_NAME` hech qachon yetib
  bormagan; standalone frontend SaaS rejimida yig'ilardi.
* Vendor login serializer'i zaxira kodini (`a1b2-c3d4`) `max_length=6`
  bilan `400` qaytarib rad etardi.

### Sifat darvozalari

| Tekshiruv | Natija |
|---|---|
| `pytest` (tasodifiy tartib) | **1255 o'tdi** · 0 xato (4-bosqichda 1155) |
| `ruff` / `ruff format` / `mypy` | toza (300 fayl) |
| `tsc` / `eslint` / `vitest` / `build` | toza · **211 test** (4-bosqichda 183) · eslint 0 xato, 23 eski ogohlantirish |
| `makemigrations --check` | o'zgarish yo'q |
| `check_rls` | 46 jadval |
| nginx (haqiqiy `nginx:1.27-alpine`) | SaaS HTTP + TLS, standalone; 30+ manzil; Accept-Language |
| Headless Chrome | CSP buzilishi 0; landing 390/768/1024/1280 o'lchandi |

### Migratsiya repetitsiyasi (`kg_crm_qa`)

`accounts.0007`, `audit.0003–0004`, `platform_console.0005` — oldinga →
orqaga → oldinga; 25 bola, balans 12 919 000 o'zgarmadi; `check_rls` 46.
`seed_demo_tenant` → `--reset` (4 869 qator purge) → qayta; mavjud
tashkilot o'zgarmadi.

### Keyingi qadam

6-bosqich faqat "6-bosqichni boshla" buyrug'i bilan (dizayn hujjati).

---

## 2026-10-03 — 5-bosqichdan keyingi ish (egasining ruxsati bilan)

Egasi: "qolgan barcha ishlarni amalga oshir, qarorlarni o'zing qabul
qil". Qarorlar jadvali — `PLAN.md` §5.

**Bajarildi**

* Ikkinchi telefon `+998947267726`; shriftlar o'z serverimizdan
  (`@fontsource`) — CSP tashqi manbasiz, siyosatdan Google bandi olindi.
* D6 — `pin_legacy_payroll_rates` (sukut dry-run).
* **Yakuniy qabul ssenariysi** (brief §6) — to'qqiz qadam API orqali,
  `apps/core/tests/test_acceptance_scenario.py`. U to'rtta haqiqiy
  xatoni topdi, har biri qizil testdan keyin tuzatildi:
  1. bola kartasidan qo'shilgan vasiy telefoni tekshirilmasdi (Q7);
  2. 1-sanadan chiqib ketgan bolaga o'sha oy uchun faktura yozilardi
     (`is_billable_for`: `>=` → `>`);
  3. orqaga sanalgan chiqish guruh a'zoligi bilan 409 berardi;
  4. dashboard keshi hech qachon bekor qilinmasdi — to'lovdan keyin 2
     daqiqa eski qarz; endi ledger/kassa/ombor/davomat yozish
     nuqtalaridan `on_commit` bilan.
  Shu bilan `/ledger/balance?child=<begona>` endi 404 (invariant 2).
* Tungi vazifalar testlari (0 % → 97 % / 89 %).
* 7-bo'lim: moliyaviy kod qamrovi **94 %**; 375 va 1280px — landing va
  16 ta ilova sahifasi haqiqiy login bilan (gorizontal scroll 0, konsol
  xatosi 0); topilgani: grafik o'qi 11px, to'lovlar doskasida kesilgan
  ismlar — tuzatildi, a11y qo'riqchisi `fontSize` propini ham ko'radi.

**Playwright E2E** — qilinmadi (qaror): brauzer tekshiruvi headless
Chrome + CDP bilan bajarildi, bu esa CI'ga yangi og'ir bog'liqlik
(brauzer yuklash) qo'shmaydi. Ssenariyning o'zi backend integratsion
testida.

---

## 2026-10-03 — origin/main merged into the big-update line

From here on, working notes are written in English (owner's request).

Branch `big-update/merge-main` (from `big-update/phase-6`) merges the three
production hotfixes that were only on `main` — ADR-25 delegation rule,
individual child price, staff attendance — so deploying this line no longer
reverts them. **Deploy from `big-update/merge-main`, not from an earlier
phase branch.** Details and conflict resolutions are in the merge commit
`0cc4740`.

- Backend 1319 passed, frontend 220 passed; migration check clean.
- QA rehearsal: forward, reverse merge nodes, reapply — balance unchanged,
  `check_rls` 47 tables.
- On deploy: `children/0004_child_monthly_fee` is already applied in
  production (it shipped with hotfix feb68c0) and will be skipped.
  `attendance/0006_staff_attendance` is skipped too if 11da61a was deployed,
  otherwise it applies now. Either way Django then applies the big-update
  migrations and the merge nodes; run `check_rls` (expect 47).
- Phase-6 ADR proposals renumbered to ADR-26…28 (ADR-25 is main's).

---

## 2026-10-03 — Phase 6 (branch `big-update/phase-6-code`, from `merge-main`)

### 6.1 Payme / Click — parent online payment (ADR-26)

- New app `online_payments`: `merchant_credential` (Fernet-encrypted secret,
  `MERCHANT_SECRET_KEY`), `payment_link` (30 days, token embeds the org),
  `online_transaction` (`UNIQUE (provider, provider_txn_id)`).
- Payme Merchant API (all six methods, 12-hour timeout → reason 4) and Click
  SHOP-API (prepare/complete, MD5 sign). Tenant from the URL, everything in
  `organization_context`; RLS not widened. Perform → `record_payment(method=
  online)` — ledger, allocation, cash movement into the "Payme / Click" pot in
  one transaction; cancel after perform → `reverse_payment`.
- Staff: "Online payment link" in the cashier's payment window (copy / send to
  Telegram); Settings → Online payment (keys, sandbox, callback URL to paste
  into the merchant cabinet). Parent: public `/pay/:token` page (uz/ru/en),
  added to the nginx SPA whitelist.
- Tests: 37 backend (Payme 15, Click 9, endpoints 13 — incl. cross-tenant 404
  for invoice, token and Payme/Click calls) + 3 frontend.
- QA rehearsal: `online_payments.0001` forward → zero → forward, `check_rls`
  **50**.
- Deploy: set `MERCHANT_SECRET_KEY` in `.env` **before** the first kindergarten
  saves keys (production refuses to save without it; never change it later).
  `cryptography` added to requirements → image rebuild.

### 6.2 Parent bot + 6.3 phone linking (ADR-27)

- `contact_index` (new app `parent_bot`): HMAC digests of guardian phones and
  linked chats → organization ids. Metadata RLS policy; the bot's one
  cross-tenant read is under `platform_context()`. Kept current by a
  `post_save` signal on `Guardian`; `/stop` removes the chat rows.
  `rebuild_contact_index` (dry run by default, `--apply`, `--tenant`) rebuilds
  it — **must be run once after deploy** (existing guardians have no rows).
- Bot menu for a linked chat: Balance / Invoices / Pay / Receipts (uz/ru/en,
  matched in any language). Pay = a payment link per child (6.1) as an inline
  button, or "pay at the office" when no merchant is connected. One chat in
  two kindergartens sees both, under their names.
- `/start` without a code offers "share my phone"; only the sender's own
  contact links (`contact.user_id == from.id`); legacy unnormalised phones are
  matched in canonical form.
- Absence alert (P6-5): `notifications.absence_alert`, off by default; only
  today, only on a change to absent, once per child per day; never moves money.
- Tests: 29 (bot 24, absence 5). QA: `parent_bot.0001` forward → zero →
  forward, `check_rls` **51**; rebuild dry run +70 → apply → second dry run +0.

### 6.4 Subscription online payment (P6-3)

- Payme / Click protocol code now takes a `Merchant` (whose keys) and a
  `Ledger` (what is paid) — `online_payments/merchant.py`. Tuition is one
  ledger (unchanged behaviour, all 6.1 tests green), subscriptions the second.
- Radix's merchant from `.env` (`RADIX_PAYME_*`, `RADIX_CLICK_*`); empty = no
  button, bank transfer as before. Callbacks `/public/pay/subscription/{payme,
  click}` (SaaS only) find the tenant by invoice number in the metadata plane.
  Perform → `record_subscription_payment(method="online")` → `suspended` →
  `active`. Refund after payment refused (`-31007`).
- `subscription_online_transaction` (metadata RLS) and the long-documented
  `ck_sub_payment_method` CHECK — `subscriptions.0005`. `check_rls` **52**.
- Billing page: "Pay online" per open invoice; `?paid=1` return re-reads the
  invoices for a minute.
- Tests: 14. QA: `0005` forward → back → forward.
- Deploy: if `migrate` fails on `ck_sub_payment_method`, some row has a method
  outside the four — report it, do not edit it (rule 5).

### 6.5 Contract templates

- New app `contracts`: `contract_template` (closed placeholder list checked
  on save, `version` grows with the text) and `contract` (number
  `SH-<year>-<nnnn>`, values and text frozen at creation; the database
  refuses edits — `trg_contract_frozen`). `check_rls` **54**.
- Deviation from the design note: the frozen text is **plain text**, not
  `rendered_html` — a value typed into a child's card can never become markup
  on a print-out; the browser prints it (D1).
- Permissions reuse `settings.*` (templates) and `children.*` (contracts);
  row scope (ADR-21) applies. `children/selectors.py` added so the contracts
  view never imports children models (invariant 1).
- UI: Settings → contract templates (placeholder buttons insert at the
  cursor); child card → contracts (make, view, print, sign, terminate).
- Tests: backend 17 (incl. cross-tenant 404 for child, template, contract;
  DB refuses a text edit), frontend 2 (print writes text, not markup).

### 6.6 Kitchen / menu → stock consumption

- New app `kitchen`: `dish`, `dish_ingredient` (per portion, product unit),
  `menu_day`, `menu_item`. `check_rls` **58**.
- Serving: portions = present children (register) + staff portions;
  preview first (needed / available / short per product), then one
  `consumption` movement per product, all or nothing. Undo writes
  `adjustment` counter-movements; each serving has its own reference.
- **Deviation (Qaror kerak):** a shortage *refuses* serving instead of letting
  stock go negative as the design note proposed — the inventory module's
  documented rule wins until the owner decides.
- Dish cost per portion at the latest purchase prices.
- `attendance/selectors.py`, `inventory/selectors.py` added (invariant 1).
- UI: Inventory page → "Oshxona" tab (dishes, daily menu, preview, served /
  undo). The Store tab's markup only moved one indentation level.
- Tests: 14 backend (+ sweep factories for the four new endpoints).

### 6.7 Self-signup with a 14-day trial (ADR-28)

- (Trial unified to **15 days** on 2026-10-03 — see "Owner's decisions" below.)
- `POST /public/signup` writes a `platform_signup_request` (token as SHA-256,
  24 h) and a `Lead` (`self_signup`) — no tenant. `POST /public/signup/confirm`
  with a password runs `register_organization(trial_days=14)`. One
  self-signup trial per e-mail; same answer for every address.
- `purge_unconverted_trials` (dry run by default): unconfirmed requests > 7
  days; self-signup tenants cancelled at trial end, never paid, trial ended >
  30 days ago → `purge_organization`. Vendor-opened tenants are never
  candidates (no signup request points at them).
- 01 §4.4 updated (it said "there is no public signup"); copy follows its
  rule — no "free", conversion terms disclosed on the form.
- UI: `/signup`, `/signup/confirm` (SaaS only, nginx whitelist), link on the
  login page. uz/ru/en.
- Tests: 17 backend, 1 frontend.

### Owner's decisions on the phase-6 report (2026-10-03)

1. Kitchen — **frozen**: no customer wants it yet.
2. Trial — **15 days** everywhere; the self-signup's 14-day parameter was
   removed (one trial length, one code path).
3. Unconverted trials — **as built** (confirmed 2026-10-04): 30 days after the
   trial ends the organization is deleted in full, and only when the owner runs
   `purge_unconverted_trials --apply`. ADR-28 is closed.
4. Absence alert stays off; parents are reached by Telegram only.
5. Contracts — **frozen** too.

Implementation: `apps/core/features.py` — `FEATURE_CONTRACTS`,
`FEATURE_KITCHEN` (default off). Off means: endpoints not registered, screens
hidden (the frontend reads `user.features` from `/auth/me`, so one switch
drives both). Tables and migrations stay; the test suite runs with both on so
the code stays ready.

Also on 2026-10-04: the "Toʻlov haqida SMS" setting label became "Toʻlov haqida
xabar" (and the sending-window help lost its "SMS") — the switch has governed
Telegram as well since ADR-23, and the Telegram guide would have had to
contradict the screen.

### Telegram bot guide (2026-10-04)

`docs/guides/telegram-bot.md` — written for kindergarten staff, in Uzbek, from
the shipped screens and bot replies. The owner asked for it to hand to
customers; it is also the first document that describes the bot end to end
(setup, connecting a parent, the four buttons, what the kindergarten sends,
the log, limits).

### Local bot run and a migration finding (2026-10-04)

The owner asked for the terminal work to be done here. Done locally, nothing
touched in production:

* Local `.env` got `MERCHANT_SECRET_KEY` and `CONTACT_INDEX_KEY` (generated;
  `.env` is gitignored). The bot token, username and webhook secret were
  already there.
* `@radix_crm_bot` verified through `getMe`; no webhook is set on the bot, so
  long polling is free. The bot now runs detached against `kg_crm_qa`
  (`backend/.run/telegram-bot.log`, pid in `.run/telegram-bot.pid`).
* Whole chain exercised against the seeded QA data, not fresh test tenants:
  `/start <code>` → the four buttons (real balances, invoices, receipts) →
  `/stop` → phone linking → reconnect. The pay button picked the oldest open
  invoice (FIFO) and produced a link; locally `FRONTEND_URL` is
  `http://localhost:5173`, so the reply falls back to a text link, because
  Telegram refuses a non-https button URL. In production it is a button.

**`finance.0006` now checks the data before adding the constraint.** The local
scratch database has 51 `payment.method = 'transfer'` rows — a value that
never existed in any version of the code (the choices were always `cash`,
`card`, `bank_transfer`, `online`), so they were written by hand at some
point. The constraint failed with nothing but *"check constraint
ck_payment_method_known is violated by some row"*: no table, no value, no
count — and under RLS a plain `SELECT` returns nothing, so there was no thread
to pull during a deploy. The migration now reports the value, the row count
and what to do, and still refuses to rewrite an unknown method on its own
(a money row is not guessed at). Red test first:
`apps/finance/tests/test_method_guard.py`.

**Production risk from this: none that we can see.** Production can only hold
what the code wrote, and `0006` maps `card` → `terminal` itself. The local
rows are scratch data. The guard is there so that if a hand-edited row does
exist somewhere, the deploy says which one instead of stopping blind.

The local `kg_crm` database was left alone (it is stale scratch — finance
migrations stop at 0005 and it holds 27 leaked test organizations).

## 2026-10-05 — deployed to production

The owner asked for the big update to go live. Deployed from
`big-update/phase-6-code`; both stacks (SaaS and `/private`) now run it,
`check_rls` reports **58** tables on each.

Before touching anything: `./scripts/backup.sh`, which takes the dump, restores
it into a scratch database and compares row counts (1122 rows, exact match).
The archive stays on the server — copying it to a laptop was refused, correctly,
because it holds children's and parents' data.

**Migrations.** All applied, including `finance.0009_backfill_allocations` over
real money. Verified afterwards for Oriental Kinderland: `invoice.amount_paid`
summed to 333 600 000, the allocation rows summed to the same, outstanding debt
84 880 000. The backfill moved the link into its own table and changed no
figure, which is what it promised.

**Three faults found and fixed during the deploy, each invisible from a test
run:**

1. `FRONTEND_URL` was never set on the server and defaults to
   `http://localhost:5173`. Every Telegram invite link and payment link would
   have been built correctly and pointed at the deployer's laptop. Production
   now derives it from `PUBLIC_BASE_URL`, and an empty `FRONTEND_URL=` line
   falls back the same way.
2. `requests` was used in five production paths (Telegram, Eskiz, lead alerts,
   two commands) and declared nowhere; locally it arrived through
   `djangorestframework-stubs`. Every message send in production would have
   raised `ModuleNotFoundError`. `apps/core/tests/test_dependencies.py` now
   walks every import in `apps/`, including the ones inside functions — which
   is how this one stayed hidden.
3. `compose.prod.yaml` forwards environment variables by explicit allow-list,
   so every phase-6 key sat in `.env` unseen. The Telegram token read as empty;
   `rebuild_contact_index` quietly used the `SECRET_KEY` fallback and wrote 41
   digests that the real key would never have matched (the rebuild afterwards
   reported `+41 −41`).

**After the deploy.** Contact index built for 41 guardians across 3
organizations (idempotent on a second run). Telegram webhook set and accepted;
a wrong secret answers `404`. Contracts and kitchen answer `404` while live
modules answer `401`, so the feature switch does what it claims. The local
polling bot was stopped first — Telegram refuses polling and a webhook at once.

### "Is multi-tenancy broken?" — no, but the address lied (2026-10-05)

The owner signed into Paddington and Oriental Kinderland in one browser and
found `/t/paddington/attendance` showing Oriental Kinderland in the header and
the group **Quyoshcha** in the picker. Checked against production:

| Organization | Address | Groups |
|---|---|---|
| Oriental Kinderland | `/t/toshkent-qamarniso-kochasi-9/` | Quyoshcha, Yulduzcha, nimadir |
| Paddington | `/t/paddington/` | Angels, Aqua, Genius, Little Dino |

So the screen held **Oriental Kinderland's own** groups, not Paddington's.
Nothing crossed the boundary: the organization comes from the token
(`core/middleware.py` reads `user.organization_id`, never the URL) and RLS
enforces it in the database. The slug is a router basename, nothing more.

What actually happened: one browser holds one refresh cookie, so the second
sign-in replaced the first session. Each tab keeps its own access token in
memory, which is why the mix-up only appears after a reload — then the older
tab restores the newer session while keeping its old URL.

Login already redirected to the session's own address; **session restore did
not**, so the address stayed wrong. Fixed, with a red test first
(`app/providers/__tests__/tenantAddress.test.tsx`). Not a leak, but it invites
a real mistake: marking attendance or taking a payment while believing you are
in the other kindergarten.

Still true by design: two kindergartens cannot be open at once in one browser
profile. A second profile or a private window is the way, and the app now
makes the mismatch impossible to miss instead of showing it silently.

### Platform console 2FA switched off again (2026-10-05)

After the deploy the console started asking for an Authenticator code: ADR-24
made `PLATFORM_2FA_REQUIRED` default to on and production had never set it.
The owner asked for it off, so `.env` now says `False` — **and the variable had
to be added to the compose allow-list**, which is the third time that list has
hidden a setting during this deploy.

Verified: the setting reads `False` in the container, and a sign-in attempt now
answers "credentials wrong" instead of `TOTP_REQUIRED` (tested with a
deliberately wrong password, so the real one was never needed). The login page
needs no change — it only shows the code field after the server asks for one.

Worth remembering: that account has **0 backup codes**. If 2FA is ever turned
back on and the phone is lost, the way in is `create_platform_user --email …
--update --new-2fa` on the server.

## 2026-10-06 — phase 7, first three items

**7.1 — the first month was never prorated.** The backend was right all
along and every organization is set to `prorated`; the add-child form simply
had no enrolment date, so `enrolled_on` stayed empty and `_is_first_period()`
returned False. Production had 21 of 21 Paddington children and 5 of 5 in the
new organization with no date — every one billed a full month regardless of
when they arrived. The form now asks for it (today by default) and says what
it affects; editing keeps whatever the child has and does not demand one, so
an old record is never quietly given today's date.
`backfill_enrollment_dates` (dry run by default) fills in children that have
no invoice yet, from `created_at`; children with an invoice are left alone,
because an issued document is not recomputed backwards.

Tested with the owner's own example: 3 050 000 over 22 working days, a child
arriving 25 September pays for 4 days — **554 545**. His message also carried
a formula, `3050000 − 3050000/22*4`, which is 18 days and contradicts his own
sentence ("should be charged for 4 days"); the sentence matches the
documented policy, so that is what was built. Flagged to him.

**7.2 — expenses are approved on creation.** The same person entered and
approved them, so the pending step checked nothing while keeping the expense
out of the report and the money in the till. The cash movement still happens
on approval (ADR-17); approval now happens with creation.

**7.3 — dashboard.** Transfer, terminal and Payme/Click read as one "Bank
hisobi" card, cash stays its own, and the card lists what was merged. Display
only: `cash_account` keeps four pots so the journal can still say where money
is. This month's income by method now sits on the dashboard too, from
`revenue_report` — the same source Reports uses.

Still open: 7.4 guardians (second phone, editing), 7.5 expense line items,
7.6 dynamic import template, 7.7 absence credit against the current month
plus file attachment.

