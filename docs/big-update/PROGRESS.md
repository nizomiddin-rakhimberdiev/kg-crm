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
