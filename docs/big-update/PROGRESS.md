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

### 7.6 + 7.8 — migrating a kindergarten that already has children

The owner's answer to "which next" turned out to be one coherent feature: a
kindergarten moving onto Radix is not adding new children, it is carrying
over the ones it already has.

* `Child.is_existing_client`. It decides two things, both about money: the
  first month is **not** prorated (the child has been attending all month —
  PLAN 7.1's rule would be wrong for them), and the child may arrive with a
  debt. A flag rather than "enrolled_on is in a past month", because a
  kindergarten usually does not know the original date, and "no date" is
  exactly the silent full-month bug 7.1 just fixed.
* `record_opening_debt()` writes an `adjustment` debit through
  `post_ledger_entry`, so Debtors picks it up with no new concept (invariant
  4). It refuses on a child that already has ledger rows, so a second import
  run or a manual repeat cannot double someone's debt.
* The add-child form asks "Yangi mijoz / Mavjud mijoz", defaulting to **new**;
  the import sheet defaults to **existing**. Opposite defaults on purpose —
  the form is for a child joining now, the sheet is for the move.
* The template now carries the kindergarten's own groups and tariffs as
  dropdowns, plus `Mijoz` and `Qarzdorlik` (starting at 0). Excel caps a list
  formula at 255 characters, so a long group list falls back to plain text —
  import still matches by name, you just lose the dropdown. Tested.

Tests: 12 for template and import, 6 for proration and opening debt,
including "a payment closes it like any other debt".

### 7.4 — guardians: a second phone, and a way to edit one

Families usually carry two numbers and one of them is often off. The second
is optional and appears only behind a "+ Ikkinchi raqam" button, so no empty
input sits in the form waiting to be ignored.

It is not decoration: the contact index stores both numbers and
`link_by_phone` matches either, so a parent who shares the other SIM with the
bot is still found (ADR-27). Without that the field would exist and do
nothing. It stays non-unique — the main phone is still who the guardian is.

Editing turned out to exist in the API the whole time; there was simply no
screen for it. So "vasiy qo'shish yaxshi ishlamayapti" was really "a changed
number means detaching and re-adding", which threw away the Telegram link and
the history. The dialog warns when the main number changes, because that is
the bot's key.

### 7.5 — expenses are made of lines

"Bozorlik — 600 000" does not say what was bought. An expense is now rows:
*kartoshka, 50 kg, 3 000 → 150 000*, with "Yana qo'shish" for the next one
and a running total underneath.

`expense_item` is a tenant table with the usual guards (`check_rls` 58 → 59).
`line_total` is stored rather than recomputed, so rounding cannot differ
between the screen and the report, and `Expense.amount` is the sum of the
lines — which is what leaves the till (ADR-17). **A client-supplied amount is
ignored when lines are present**: if we trusted it, the figure on screen and
the money in the journal would drift apart one day and nobody would notice.
Lines are optional, so the old single-amount path and old records still work.

Tested with the owner's own example, including that the till loses exactly
the sum of the lines.


### 7.7 — the credit comes off this month, and the certificate stays with it

Until now an approved absence claim always waited for the **next** invoice.
For a family that had not paid yet that was backwards: they owed 2 200 000,
five days were credited, and the bill in their hand still said 2 200 000
while a minus line sat somewhere in next month.

Approval now looks at the invoice of the month the absence started in:

- **unpaid, and the credit fits in what is outstanding** → it comes off that
  invoice at once (a negative line, a lower `amount_due`, a `discount` CREDIT
  ledger entry, status `applied`);
- **already paid, or no invoice yet, or the credit is bigger than what is
  left** → nothing moves; the claim stays `approved` and the next invoice
  swallows it whole, exactly as before.

Two decisions worth writing down. **The invoice document is edited** — which
D3 normally forbids — and that is right here precisely because the parent has
not paid: the paper and the system have to show the same number. **The ledger
is not edited**: the debit was posted in full at issue, so the correction is
a separate CREDIT entry (invariant 3). And a credit larger than the
outstanding amount is **not split** across two invoices — splitting the money
would mean splitting the claim, and whatever did not fit would quietly cease
to exist.

The certificate or application itself can now be attached (`document_file`):
in the create form, or later with a paperclip on a pending row — the paper
usually arrives after the phone call. PDF or photo, 10 MB. Only while
`pending`: after a decision, the document behind the money is fixed, or the
approver would be signing off on one certificate while the folder held
another.

The file is never served from `/media/`. A static URL knows neither the
session nor the tenant, and this one is a child's medical record, so it goes
through `GET /absence-claims/{id}/document/download` — tenant-scoped, and a
`404` for anyone else. The stored name is a UUID: "spravka.pdf" is what
everyone calls it, so the real names would both collide and let one family
guess another's path.

Tests: the unpaid month, the paid month, a credit that does not fit, a month
with no invoice yet, attaching at creation and afterwards, a rejected `.exe`,
and another organization getting `404` on both the upload and the download.

## Bosqich 8 — the landing page

### What was actually wrong

Two separate problems, and only one of them was visible in the code.

**The page was a year behind the product.** It never mentioned the 15-day
trial — even though self-signup has been live since phase 6 and the page's
only call to action was "book a demo". It never mentioned the Telegram parent
bot, which is the main parent channel (ADR-23) and the first thing a
kindergarten asks about. Nor online payment, the absence credit, expense
lines, where the money sits, Radix Intelligence, the Excel import, or the
three UI languages. It also never said the thing a cautious buyer most wants
to hear: an unpaid month stops writing, not reading, and nothing is ever
deleted.

**And below 1024 px the layout was running the desktop's scroll story.**
`useStaticScene()` gave the plain layout only under 640 px, so a phone held
sideways (844 × 390) and every tablet still got pinned, scroll-jacked scenes
— in a window far too short for them. Measured with headless Chrome against
the live site: 25 800 px of page at 768 px wide, with the product panel cut
in half in each scene.

### What changed

The breakpoint rule is now one line and it asks about the **window**, not the
device: pinned scenes need `min-width: 1024px` **and** `min-height: 700px`.
Everything else gets the static layout, which already existed for
`prefers-reduced-motion` and was already tested. That deleted the entire
tablet "compact pinned" branch from seven sections.

On the phone the navigation now carries one real call to action instead of a
language switcher that took half the bar; the language moved into the menu,
where it is a full-width row. The dark-section flip re-arms on DOM changes:
sections swap their whole tree when the viewport class changes, so the old
one-shot `IntersectionObserver` was watching detached nodes and the bar
stayed white over a dark section.

Three panel bugs that made the product look unfinished on a phone: the window
header drew a grey rounded rectangle that read as a loading skeleton (it now
names the screen), the "one system" panel was a fixed 720 px inside a 350 px
column and squeezed its tiles to 11 px wide, and the dashboard showed five KPI
tiles in three columns where a number ran wider than its tile.

### The sideways scroll nobody had noticed

The Russian page scrolled 35 px sideways — on the live site, before any of
this. The cause was a grid child without `min-w-0`: the default
`min-width: auto` let the longest Russian label inside the role panel set the
column width, and the whole document grew with it. Uzbek fitted, so it never
showed up in testing. Now `uz`, `ru` and `en` are all at zero at 360 px and
390 px.

### Content

New sections: **parents** (bot, online payment into the kindergarten's own
merchant account, linking by invitation, SMS as the paid option), **Radix AI**
(a rule and its evidence — the card shows the "Why?" list, because that is
what the product actually renders), and **extras** — eight plain cards for the
things that need naming, not a mock. The FAQ was rewritten into eleven
answers, including the trial, migrating existing children, what suspension
does, and the standalone licence. Pricing shows all three terms the business
sells; the six-month one needed `/public/pricing` to return it, because the
page is not allowed to carry its own formula (ADR-12).

The first call to action is now the trial, with the demo form beside it. That
is a reversible content decision, taken under standing permission: the trial
exists, it costs nobody a meeting, and the kindergartens that want to be
walked through it still have the form.

### Numbers (headless Chrome, before → after)

| Viewport | Height | Sideways | Clipped | < 12 px |
|---|---|---|---|---|
| 390 × 844 uz | 12 932 → 15 956 | 0 → 0 | 1 → 1 | 0 |
| 390 × 844 ru | 13 108 → 16 358 | **35 → 0** | — | 0 |
| 844 × 390 | 25 772 → **16 287** | 0 | 8 → 3 | 0 |
| 768 × 1024 | 25 806 → **16 491** | 0 | 14 → 4 | 0 |

The phone page is longer because it now says three things it did not say
before; every screen of it is content, not scroll distance.

### Gates

Frontend: 251 tests (landing 21, was 14), tsc clean, eslint 0 errors,
prettier clean, prerender 9 pages with the FAQ JSON-LD intact. Backend: the
platform and subscriptions suites (232 tests), including two new ones for the
six-month quote and the trial length.

### 8.8 — the device sweep and the copy edit

The owner looked at the new page and said two things: there were plenty of
defects, and the spelling was off in several places. Both were right.

**The worst find was the mobile menu.** It opened 48 px tall — a white strip
under the bar with one and a half links in it. The cause is a CSS rule that is
easy to miss: an element with `backdrop-filter` becomes the containing block
for its `position: fixed` descendants. The menu was a child of the blurred
header, so `top-[60px] bottom-0` resolved against the 60 px bar instead of the
screen. Moving the panel out of `<header>` fixed it; a test now asserts it
stays out.

**Contrast was the widest problem.** Grey 12 px text (`slate-400` on white)
measures 2.62 : 1 where AA asks for 4.5 — and that colour carried every hint,
every chart label, every date and the "sample data" note. On light surfaces it
is now `slate-500` (4.96) or `slate-600` where the surface is tinted; dark
sections keep `slate-400`, which is 5.09 against `ildiz-900`. Two more: the
debt pill (`orik-700` on a tinted card, 4.25) and the inactive FAQ number
(1.66 — it was barely visible at all).

**Tap targets.** Module chips were 32 px, the price slider's hit area was the
8 px track itself, footer contact links 23 px, the legal page's "back" link
20 px, the language buttons 26 px. All are 44 px now, and the slider has a
24 px thumb on a 44 px rail.

**Two things the audit could not see** but a screenshot could: the login page
offered the 15-day trial *and*, four lines below, "contact us to open an
account" — the second line predates ADR-28 and is now gone; and the signup
page drew a logo at 32 px, below the brandbook's 34 px threshold, so it
silently dropped the wordmark and the page opened with a bare mark.

**Copy.** `Yog‘` was written with U+2018 instead of the Uzbek ʻ — invisible on
screen, a different string to every lookup. "400 000 soʻm / oy dan" is not
Uzbek; it is now "Oyiga 400 000 soʻmdan". "Havolaning bosilishi roziligining
yozuvi" was unreadable. "Spravka" became "shifokor maʼlumotnomasi", "ledger"
and "леджер" became "pul harakatlari jurnali" and "журнал операций" — the
reader is a kindergarten director, not a developer. English straight quotes
became curly ones, and "Move in from Excel" became "Import from Excel". About
thirty edits in all, across the three languages.

### Final numbers (headless Chrome, after)

| Page | Sideways scroll | < 12 px | Contrast failures | Clipped |
|---|---|---|---|---|
| `/uz`, `/ru`, `/en` (320–1920) | 0 | 0 | 0 | 1–2 (sr-only / 8 px in a mock row) |
| `/signup`, `/login` | 0 | 0 | 0 | 0 |
| legal, 404 | 0 | 0 | 0 | 0 |

Frontend: 254 tests, tsc clean, eslint 0 errors, prettier clean.

## Bosqich 9 — mijozning uchta soʻrovi

### 9.1 Ish grafigi: bezak emas, pulning maxraji

Soʻrov "to'liq, soatlik, haftada 2-3 marta keladigan" deb keldi. Shunday
roʻyxatni ochib qoʻyish oson, lekin u hech narsa qilmasdi. Pul nuqtai
nazaridan "yarim stavka" va "haftada uch kun" — bitta narsa: oylik maosh
va u qaysi kunlarga tegishli. Soatbay esa haqiqatan boshqacha: summa
maoshdan emas, kelgan kunlardan chiqadi. Shuning uchun ikki rejim
(`monthly`, `hourly`) va ish kunlari roʻyxati (`work_days`, boʻsh boʻlsa
filial kalendari).

Eng muhim tuzatish koʻrinmaydigan joyda edi: ishga kirgan oyning
proporsiyasi. Ilgari maxraj filialning ish kunlari edi, yaʼni haftada uch
kun keladigan tarbiyachi 14-oktabrda ishga kirsa 13/22 olardi — ishlagan
kunlarining ulushidan kam. Endi maxraj uning OʻZ kunlari: 8/13. Grafigi
boʻsh xodim uchun ikkalasi bir xil, yaʼni eski xatti-harakat oʻzgarmadi.

Soatbayda: tabeldagi kelgan kunlar × kunlik soat × soat narxi. Tabel
umuman yuritilmasa — grafik boʻyicha. Nolga tushirish "texnik jihatdan
toʻgʻri" boʻlardi, lekin bu sabab koʻrsatilmagan nol: tabelni hech kim
toʻldirmaydigan bogʻchada har bir soatbay xodim oyligini ololmay qolardi.

**Hisob bogʻlash teskari tomonga.** Xodim formasidagi "Tizim hisobi"
tanlagichi hali mavjud boʻlmagan hisobni tanlashni soʻrardi — ish tartibi
teskari edi. Endi bogʻlash foydalanuvchi formasida: xodim tanlanadi, va
boʻsh tanlov bogʻlanishni uzadi (eski qator jimgina qolib ketsa, tarbiyachi
hamon birovning guruhini koʻrardi). `Employee.user` oʻzgarmadi — faqat uni
kim toʻldirishi oʻzgardi.

### 9.2 Qarzdorlik tarixi: qaysi oyning qarzi qolgan?

Egasining savoli aniq edi: sentabrda 15 boladan 28 mln qolgan, oktabrda
24 mln yopilgan, 4 mln qolgan, ustiga oktabrning oʻz qarzi. Qarzdorlar
roʻyxati bunga javob bera olmaydi: u BUGUNGI qoldiqni koʻrsatadi va u
qaysi oydan qolganini bilmaydi.

Javob allaqachon bazada edi — `payment_allocation` qaysi pul qaysi
hisob-fakturani yopganini yozadi (ADR-20). Yangi hisobot shundan
oʻqiydi: oktabrda kelgan pul sentabr fakturasini yopgan boʻlsa, u
sentabr qatorida koʻrinadi. Qatorni ochganda — bola, hisoblangan,
toʻlangan, qoldiq va har bir toʻlov: sana, usul, summa.

Ikki tafsilot bilan: `invoice.amount_paid` keshi emas, taqsimot jadvali
oʻqiladi (kesh siljisa hisobot haqiqatdan ajralardi), va sana MAHALLIY
vaqtda koʻrsatiladi — Toshkentda soat 00:30 da qabul qilingan toʻlov UTC
da kechagi kun boʻlib chiqardi va kassadagi chek bilan mos kelmasdi.

### 9.3 Shartnomalar muzlatmadan chiqarildi

Kod 6.5 da yozilgan va sinalgan edi, faqat `FEATURE_CONTRACTS` oʻchiq
turardi (P6-7: "hech bir mijoz soʻramayapti"). Endi soʻralyapti.

Mijozning haqiqiy shartnomasi (Oriental Kinderland, 2026) namunaviy matn
sifatida kiritildi: nomlar, summalar va sanalar oʻrnida `{{...}}`
maydonlar. Yaʼni bogʻcha hujjatni "yuklamaydi" — tayyor matndan boshlaydi
va oʻziga moslashtiradi. Matn **kodda**, bazada emas: u mijoz maʼlumoti
emas, balki boshlangʻich nuqta; saqlagan tashkilot oʻz nusxasini oladi.

Shablon uchun yangi maydonlar kerak boʻldi — direktor, bank rekvizitlari,
toʻlov kuni, bir kunlik ovqat puli, toʻlovsiz kunlar, saqlash soati.
Ularning hammasi **sozlama** (`contracts.*`): bogʻchaga xos va yilda bir
marta oʻzgaradi. Nomaʼlum maydon shablon saqlanganda rad etiladi, yaʼni
matndagi xato bir yildan keyin chop etishda emas, oʻsha payt chiqadi.

`child.contract_number` — qogʻozdagi raqam, tizim tuzadigan
shartnomaning raqamidan (`SH-2026-0001`) ALOHIDA. Ikkisini bitta ustunga
tiqish ulardan birini yolgʻon qilardi.

## Bosqich 10 — UI/UX auditi (375 px)

Audit taxmin bilan emas, oʻlchov bilan qilindi: headless Chrome demo stendga
kiradi, har bir sahifani 375 px da ochadi va yon scroll, 12 px dan kichik
matn, WCAG kontrasti, barmoq nishoni, kesilgan matn va nomsiz
boshqaruvlarni sanaydi.

**Ikkita muammo hamma yerda edi.** 12 px kulrang matn oq fonda 2.62:1 —
guruh nomlari, izohlar, sanalar, hatto summalar. Va boshqaruvlar 34–38 px:
tablar, filtr chiplari, select'lar, inputlar. Ikkalasi ham bitta ekranning
xatosi emas, shuning uchun bitta ekranda tuzatilmadi: rang 55 faylda
koʻtarildi, balandlik esa `index.css` dagi bitta qoidaga aylandi. 59 ta
komponentga qoʻlda `min-h-11` yozish xuddi shu natijani berardi — va
oltmishinchisida unutilardi.

**Toʻlovda bitta nol.** "1500000" oʻrniga "15000000" terish oson. Taqsimot
koʻrinishida u "avansga 13 500 000" boʻlib chiqardi, lekin hech narsa
soʻramasdi — ota-ona ketgach, buni faqat keyingi oy balans tushunarsiz
boʻlganda sezilardi. Endi qarzdan 50 000 soʻmdan ortiq har qanday summa
tasdiqlash soʻraydi. Mayda ortiqcha (chaqa) soʻramaydi: har safar savol
beradigan qoʻriqchi oʻqilmay qoʻyiladi.

**Davomatda yoʻqolgan mehnat.** Qoralama faqat xotirada: "Saqlash"gacha
serverda hech narsa yoʻq. Tarbiyachi 25 ta bolani belgilab guruhni
almashtirsa yoki ilovani yopsa — hammasi yoʻq. Endi ikkala yoʻl ham
soʻraydi. Telefonda esa saqlash tugmasi roʻyxat tagida qolib ketardi, shuning
uchun u yopishqoq panelga chiqdi va nechta bola belgilanganini aytadi.

**Diagramma matni.** Eng yomon kontrast grafiklarda edi: oʻq yorliqlari
Recharts'ning standart kulrangida, legenda esa QATOR rangida — "Chiqim"
2.19:1. Yaʼni ustun nimani anglatishini aytadigan matn ekrandagi eng
oʻqilmaydigan narsa edi. Yangi `CHART.label` tokeni (tosh-600, 6.97:1)
ikkalasini ham oladi; rangni esa legendaning nuqtasi koʻrsatadi.

**Qarzdorlar jadvali telefonda jadval boʻlib qolgandi.** Sakkizta ustun
375 px ga sigʻmaydi — ular siqiladi, va siqilganda eng ichkariga tushadigan
narsa aynan qoʻngʻiroq qilish qarorini beradigan ikki raqam boʻladi:
qancha va necha kun. Telefonda endi jadval emas, kartochkalar: summa va
kun yuqorida, tugmalar pastda. Filtrlar yigʻildi, lekin **yopiq filtr
tugmada sanaladi** — aks holda kecha qoʻyilgan filtr bugun roʻyxatni
jimgina kesib, mudira "qarzdor qolmabdi" deb oʻylardi.

**Bola kartasida ikki amal eng yiroqda edi.** Toʻlov tugmasi balans
kartasining ichida, telefon raqami esa guruh va tarifdan keyin — ikkalasi
ham varaqlab yetiladigan joyda, holbuki mudira kartani aynan shu ikki ish
uchun ochadi. Ular sarlavha ostiga chiqdi. Jonli tekshiruvda chiqqan
yondosh xato: balans kartasidagi eski tugma joyida qolib, bitta ekranda
bir xil ikkita yashil "Toʻlov qabul qilish" turdi — eskisi oʻchirildi,
chunki ikkita bir xil asosiy tugma har doim "qaysi biri?" degan savol
tugʻdiradi.

**Ota-ona toʻlov sahifasida ishonch.** Havola Telegramdan ochiladi, ota-ona
tizimga kirmagan, va uning birinchi savoli pul haqida emas: "bu haqiqatan
bizning bogʻchamizmi?". `Radix` logotipi bu savolga javob bermaydi —
bogʻchaning oʻziniki beradi, shuning uchun `/pay/<token>` javobi endi
`logo_url` va `contact_phone` qaytaradi. Ikkinchi joy — provayderdan
qaytish: sahifa callback'ni kutib qayta oʻqiydi, lekin kutish cheksiz
boʻlmasligi kerak edi. 20 ta soʻrovdan keyin u "tekshirilmoqda" deb jim
qolmaydi, balki pul yechilgan boʻlsa nima boʻlishini aytadi va bogʻchaga
qoʻngʻiroq tugmasini koʻrsatadi.

**Boshqaruv panelida bitta raqam — bitta ekran.** 375 px auditi toza
chiqqandi: yon scroll yoʻq, kontrast joyida, nishonlar 44 px. Lekin oʻlchov
javob bermaydigan savol bor edi — *nechta raqam birga koʻrinadi?* KPI
kartochkasi 330 px balandlikda, ikonka tepada, raqam ostida: toʻrtta raqam
uchun toʻrt ekran. Holbuki bu raqamlar aynan birga oʻqiladi — "qarz 58 mln"
"tushum 0" bilan yonma-yon turganda savol tugʻiladi, alohida turganda esa
yoʻq. Telefonda kartochka yotiq qatorga aylandi, `sm:` dan yuqorida hech
narsa oʻzgarmadi.

**Oʻn bitta `toLocaleString` PLAN 4.1 dan keyin ham qolib ketgandi.** Ularni
hech narsa koʻrsatmadi, chunki ekranda sana "xato" emas — shunchaki
BOSHQACHA: dashboardda `2026-09-17 17:20`, qolgan hamma joyda
`17.09.2026, 17:20`. Yomoni — `uz-UZ` qatʼiy yozilgan, yaʼni ruscha yoki
inglizcha ishlayotgan foydalanuvchi ham oʻzbekcha sana olardi. Q12 qoidasi
("formatlashning yagona uyi") endi `src/__tests__/format.test.ts` da:
`lib/format.ts` dan tashqarida yalangʻoch `toLocale*` yoki `new Intl.*`
boʻlsa, build yiqiladi. `formatDateTime` ga soniyalar varianti qoʻshildi
(audit izi uchun kerak) va `formatTime` ajratildi.

**Xodim formasida eng muhim maydon eng pastda edi.** Tartib shunday
boʻlgandi: familiya, ism, telefon, sana, maosh, rasmiy maosh, butun ish
grafigi bloki (hafta kunlari toʻri bilan), tizim hisobi, filial — va
faqat SHUNDAN keyin "Lavozim". Yaʼni oshpaz qoʻshayotgan mudira uning kim
ekanini aytish uchun formaning oxirigacha tushardi. Sabab texnik: maydonlar
massivdan `map` bilan chizilardi, shuning uchun har bir yangi maydon
oxiriga qoʻshilardi va TARTIB hech kimning qarori emas edi. Endi maydon
chizuvchi alohida funksiya, tartib esa JSX da koʻrinadi va savollar
ketma-ketligiga mos: kim → nima qiladi → qachondan → qancha → qanday
grafikda. Grafik bloki yigʻildi (oylik maosh + bogʻchaning kalendari —
xodimlarning aksariyati), "Saqlash" esa modalning pastiga yopishdi.

**Oylikda eng muhim ustun ekrandan tashqarida edi.** Hisoblash jadvalida
oltita ustun: xodim, baza, bonus, avans, ushlab qolish, sof. 375 px da
ulardan uchtasi koʻrinadi — va uchinchisi bonus kiritish maydoni. Yaʼni
telefonda ochilgan oylik sahifasida xodimga QANCHA TOʻLANISHI yoʻq edi,
holbuki mudira sahifani aynan shuning uchun ochadi. Telefonda endi
kartochka: ism va sof summa bitta qatorda, ostida qolgan toʻrt raqam
bitta satrda, tahrirlash esa ikkita yorliqli maydonda.

**"2026-09" — bu kod, oy emas.** Oylik roʻyxati, hisob-fakturalar, qarz
tarixi, billing va bola kartasi davrni `YYYY-MM` koʻrinishida chizardi,
har biri oʻz qoʻli bilan (`String(month).padStart(2, '0')`). Endi
`format.ts` da `monthLabel(year, month)` bor. Ruscha uchun alohida roʻyxat
kerak boʻldi: sana ichida "14 сентября", yolgʻiz turganda esa "Сентябрь
2026" — bitta roʻyxat ikkisiga yaramaydi. `DebtByPeriod` dagi oy nomlari
va `shortDate` nusxalari oʻchirildi — ular aynan Q12 ogohlantirgan
"shaxsiy nusxa" edi va ruschada qaratqich kelishigini koʻrsatardi.

**Chiqimlar sahifasida summa koʻrinmasdi.** Jadvalda olti ustun bor; 375 px
da sana uch qatorga boʻlinib ketardi ("2026-\n09-\n20") va summa oʻng
chekkadan chiqib ketardi. Yaʼni chiqimlar sahifasida — bitta raqam uchun
mavjud sahifada — aynan oʻsha raqam kesilgan edi. Telefonda endi kartochka,
sana esa `formatDate` orqali. Tasdiqlash/rad etish ilgari ikkita 32 px
ikonka edi; telefonda ular yozuvli va 44 px, chunki noto'g'ri bosilgan
"rad etish" ni qaytarish uchun qayta yozuvdan boshqa yoʻl yoʻq.
Kategoriyalar bloki formadan pastga koʻchdi — u sozlama, chiqim esa
kundalik ish.

**Boʻsh oyda hisobot "maʼlumot bor" deb koʻrsatardi.** Server oyning har
bir kuni uchun qator qaytaradi, shuning uchun `rows.length === 0` hech
qachon rost boʻlmaydi: hech narsa boʻlmagan oyda ham 31 ta nol qator
keladi. Natijada diagramma 0–4 shkalasini chizardi (soxta shkala — unda
"4" nimani anglatishini hech kim ayta olmaydi) va jadval telefonda ikki
ming piksel boʻsh qator berardi. Endi tekshiruv — davrda harakat
boʻlganmi.

**Xato holati oʻnta sahifadan sakkiztasida yoʻq edi.** Boʻsh holatlar
yaxshi ishlangan (`EmptyState`: nima yoʻq, nega normal, keyingi qadam),
lekin soʻrov YIQILGANDA nima koʻrinishini hech kim yozmagandi. Sabab
oddiy: "boʻsh roʻyxat" sharti `data && items.length === 0` koʻrinishida
yozilgan, xatoda esa `data` umuman boʻlmaydi — shart ishlamaydi va
sahifada sarlavhadan keyin hech narsa qolmaydi. Bu ekranni odam
"maʼlumotim yoʻqoldi" deb oʻqiydi, holbuki server shunchaki javob
bermagan. `QueryError` uch narsani aytadi — nima boʻldi, maʼlumot
yoʻqolmagani, va qayta urinish tugmasi.

**`aria-modal` — vaʼda, fokus esa — amal.** Telefon menyusi va modalda
`role="dialog"`, `aria-modal="true"`, Escape va body scroll qulfi bor
edi; yaʼni ekranni oʻquvchiga "orqadagi narsa yoʻq" deb aytilardi.
Klaviatura esa buni bilmaydi: Tab orqadagi tugmalarga oʻtib ketardi va
dialog yopilgach fokus sahifa boshiga tushardi — uni ochgan tugma
yoʻqolardi. `useFocusTrap` uchta ishni qiladi: ochilganda fokus panelga
kiradi, Tab panel ichida aylanadi, yopilganda ochgan elementga qaytadi.
Qoida `a11y.test.ts` da: `aria-modal` yozilgan fayl `useFocusTrap` ni
chaqirishi shart — aks holda uchinchi dialogda u unutilardi.

## Bosqich 11 — qopda yoʻq pul chiqib ketdi

**−6 752 500.** Mudira 12 mln lik oylikni "toʻlangan" deb belgiladi va
boshqaruv panelidagi qoldiq manfiyga tushdi. Birinchi qarashda bu
"tekshiruv yoʻq" degan nosozlik, lekin ildiz uchta edi va ularni alohida
tuzatib boʻlmasdi.

**Qop soʻralmasdi.** Backend allaqachon har bir toʻlov qatori uchun
`cash_account_id` ni qabul qilardi — frontend esa `mark-paid` ni BOʻSH
tana bilan yuborardi. Shunda server oʻz taklifini qoʻllaydi: rasmiy qism
bankka, naqd qism kassaga. Yaʼni imkoniyat bor edi, lekin ekran undan
foydalanmasdi va foydalanuvchi pul qayerdan ketganini bilmasdi. Avansda
esa imkoniyatning oʻzi ham yoʻq edi: `record_advance()` hamisha naqd
kassani olardi va `employee_advance` da qop ustuni umuman yoʻq edi.

**Qoldiq tekshirilmasdi.** `post_movement()` chiqimni shunchaki yozardi.
Manfiy qoldiq esa bogʻcha haqida hech narsa aytmaydi: pul fizik ravishda
manfiy boʻlmaydi. U faqat bitta narsani bildiradi — **yozuv
yetishmayapti**.

**Va yetishmayotgan yozuvni kiritib boʻlmasdi.** Mana shu uchinchisi eng
muhimi. `MovementSource` da `opening` ham, `manual` ham bor edi, lekin
ularni yozadigan **birorta ham kod yoʻq** edi: na servis, na endpoint, na
ekran. Yaʼni tizimga yil oʻrtasida kelgan bogʻchaning seyfidagi 20 mln
hech qayerda yoʻq, har bir qop noldan boshlanadi va birinchi chiqimdayoq
qoldiq minusga tushadi. Shu sababli faqat "toʻsish" notoʻgʻri javob
boʻlardi: mijoz birinchi kundayoq chiqim yoza olmay qolardi.

Shuning uchun uchalasi bitta oʻzgarishda: qoʻriqchi + tasdiqlash +
boshlangʻich qoldiq. Qoʻriqchining xabari aniq raqam beradi — «Naqd
kassa» da 6 000 000 soʻm bor, 12 000 000 soʻm chiqmoqda — 6 000 000 soʻm
yetishmaydi — chunki "amalni bajarib boʻlmadi" degan xabar foydalanuvchini
hech qayerga olib bormaydi.

**Testlar nimani koʻrsatdi.** Qoʻriqchi qoʻshilgach 29 ta test yiqildi va
ularning koʻpi boʻsh kassadan oylik toʻlardi — yaʼni ular eski xatti-
harakatni yozib qoʻygan edi. Ikkitasi esa to'g'ridan-to'g'ri MANFIY
qoldiqni tasdiqlardi (`assert balances["bank"] == Decimal("-2637000.00")`).
Testlar haqiqiy bogʻchaga oʻxshatildi: avval pul tushadi, keyin chiqadi.

**Tozalash buyrugʻi.** Mijoz hammasini oʻzi boshidan kiritmoqchi.
`reset_organization_data` ishchi maʼlumotni oʻchiradi, lekin KIRISHNI
emas — eng muhim testi ham shu: tozalashdan keyin mijoz oʻsha parol bilan
kirib, boʻsh tizimni koʻra oladimi. Tashkilot, filial, foydalanuvchilar,
rollar, obuna, roʻyxatdan oʻtishda ochilgan kassa qoplari, xabar
shablonlari, sozlamalar va shartnoma shabloni joyida qoladi.

**Jonli bazada tozalash yiqildi — va bu yaxshi boʻldi.** `--apply`
`RestrictedError` bilan toʻxtadi: `absence_claim.applied_invoice`
hisob-fakturaga `RESTRICT` bilan bogʻlangan, `PURGE_ORDER` da esa daʼvo
hisob-fakturadan KEYIN turardi. Izoh oʻrnida yozilgan edi — «daʼvo bolaga
ham, hisob-fakturaga ham bogʻlangan, u ikkalasidan ham OLDIN oʻchadi» —
lekin qator oʻsha izohning ostida emas, pastroqda turardi. Buni hech
narsa koʻrsatmadi, chunki testlarda hech qachon QOʻLLANGAN daʼvo
boʻlmagan: tasdiqlangani bor, hisob-fakturaga tushgani yoʻq. Nosozlik
vendor tomonidagi `purge_organization()` ga ham tegishli edi — yaʼni
tashkilotni butunlay oʻchirish ham birinchi shunday daʼvoda yiqilardi.
Oʻchirish `transaction.atomic` ichida boʻlgani uchun mijozning maʼlumoti
zarar koʻrmadi: yetti bola ham joyida qoldi.

## Ishga tushirish oldidan: tenant chegarasi va jim xatolar auditi

**Tenant chegarasi — teshik topilmadi, lekin qoʻriqchida koʻr nuqta bor edi.**
Butun backend koʻrildi: router (sweep oʻzi yangi viewsetni avtomatik
qamraydi va oʻz istisnolar roʻyxatini ham qoʻriqlaydi), routerdan
tashqaridagi endpointlar, barcha Celery vazifalari (hammasi
`platform_context()` da roʻyxat olib, keyin har bir tenant uchun
`organization_context()` ochadi), `all_objects`/`unscoped()`
chaqiruvlarining bari (faqat vendor kodi va management buyruqlarida),
va `organization_id` qabul qiladigan har bir selector (ishlatmagani
yoʻq). `TenantManager` **fail-closed**: kontekst yoʻq boʻlsa so'rov
umuman ishlamaydi.

Koʻr nuqta esa RLS roʻyxatining toʻliqligini tekshiradigan testda edi:
u modellarni `TenantScopedModel` boʻyicha topardi, yaʼni **oʻsha
bazadan meros olmagan model uning koʻziga tushmasdi**. `audit_log`
aynan shunday — unda `organization_id` bor, lekin u append-only
boʻlgani uchun boshqa bazadan keladi, va RLS roʻyxatiga faqat kimdir
ESLAGANI uchun kirgan. Yangi test modelning nasl-nasabiga emas,
jadvaldagi USTUNGA qaraydi. Isbot: `audit_log` ni roʻyxatdan vaqtincha
olib tashlaganda eski test oʻtdi, yangisi qizardi.

**Chiqimni tasdiqlash yarim qolishi mumkin edi.** `approve_expense()`
ikki yozuv qiladi — hujjat `approved` ga oʻtadi va pul kassadan
chiqadi — lekin `@transaction.atomic` siz edi. `ATOMIC_REQUESTS` ham
yoqilmagan, yaʼni soʻrov avtomatik tranzaksiyaga oʻralmaydi. Ilgari bu
deyarli zararsiz edi, chunki `post_movement()` amalda hech qachon xato
koʻtarmasdi. **ADR-29 dan keyin u muntazam koʻtaradi** — qopda pul
yetmasa — va oʻshanda chiqim "tasdiqlangan" boʻlib hisobotga va oylik
yigʻindiga kirib, kassadan esa chiqmay qolardi. Yaʼni kecha qoʻshilgan
qoʻriqchi eski nuqsonni xavfliga aylantirgan. Test buni koʻrsatdi:
boʻsh kassada tasdiqlash xato berdi, lekin hujjat `approved` boʻlib
saqlanib qoldi.

**Hisob-kitob vazifalari faqat muvaffaqiyatni sanardi.**
`record_daily_peak` har bir obuna uchun eng yuqori bolalar sonini
yozadi; oʻz hujjatida "oʻtkazib yuborilgan kun qaytarib boʻlmaydi"
deyilgan. Shunga qaramay u yiqilgan obunalarni yutib yuborardi va
`{"measured": 3}` qaytarardi — beshta obunadan ikkitasi yiqilgan
boʻlsa ham. Buni oʻqigan odam "uchta obuna bor ekan" deb tushunardi,
xato esa muvaffaqiyatli kechaning log'ida qolardi. Endi javobda
`failed` bor va yigʻindi alohida `logger.error` bilan yoziladi.
`close_periods_and_invoice` ham shunday.

**Tunlik tekshiruvlar bitta tenantda toʻxtab qolardi.**
`recompute_balances` (balans keshini ledger bilan solishtiradi) va
`send_debt_reminders` tashkilotlar boʻylab himoyasiz siklda aylanardi:
ikkinchisida chiqqan xato uchinchisidan oxirigacha boʻlganlarni oʻsha
kechadan mahrum qilardi. Qayta urinish ham yordam bermaydi — xato
takrorlansa roʻyxatning quyruq qismi **hech qachon** tekshirilmaydi,
va buni hech kim sezmaydi, chunki tekshiruvning oʻzi jim.

**Tiklash mashqini oʻtkazib boʻlmasdi.** `restore.sh` bazaning nomini
`.env` dan olardi, uni oʻchirib qayta yaratardi — yaʼni "tiklashni bir
marta sinab koʻramiz" degan qaror **productionni oʻchirish** degani
edi. Shuning uchun hujjatdagi mashq (§8) maxsus qayta qurilgan stendda,
maxsus yaratilgan maʼlumot bilan oʻtkazilgan va hech qachon haqiqiy
zaxira bilan takrorlanmagan. Oʻtkazib boʻlmaydigan mashq — reja emas,
va haqiqiy fayl bilan sinalmagan zaxira — taxmin.

`--into` rejimi qoʻshildi: alohida bazaga tiklaydi, ilovani toʻxtatmaydi,
media'ga tegmaydi (u bitta volume'da — almashtirish jonli rasmlarni
oʻchirardi) va tasdiq soʻramaydi, yaʼni uni cron'dan ham oʻtkazsa
boʻladi. `check_rls` oʻsha vaqtinchalik bazaga qarshi ishlaydi.

**Mashq nimani koʻrsatdi.** Haqiqiy shifrlangan zaxira (9-oktabr, 06:30)
alohida bazaga tiklandi, production esa ishlashda davom etdi: RLS 59 ta
jadvalda kuchga kirdi. Qator sonlarini `backup.sh --verify` allaqachon
har safar solishtirardi — hech qachon tekshirilmagani esa **ilova**
tiklangan bazadan oʻsha haqiqatni oʻqiydimi degan savol edi. Shuning
uchun har bir tashkilotning qarzi `finance/balance.py`, kassasi esa
`cash/selectors.py` orqali ikkala bazada qayta hisoblandi. Zaxiradan
beri oʻzgarmagan bogʻchada — 42 bola, 84 880 000 qarz, 219 320 000
kassa — barcha raqamlar **aynan mos** chiqdi. Qolgan ikkitasidagi farq
mashqning jonli holatni oʻqiyotganini tasdiqladi: `paddington` da
zaxiradan keyin 15 ta bola qoʻshilgan (§7 dagi RPO — nazariy emas,
haqiqiy), `orientalkinderland` esa zaxiradan keyin tozalangan, yaʼni
oʻchirilgan maʼlumot zaxirada turibdi va tiklanishi mumkin.

## Ishga tushirish oldidan: sozlamalar, baza va miqyos

**Django'ning oʻz deploy auditi toza.** `manage.py check --deploy`
productionda bitta ham muammo topmadi (yagona oʻchirilgan tekshiruv —
`auth.E003`, ya'ni email global emas, tashkilot ichida unikal; bu
koʻp-tenantli tizimda toʻgʻri). Sozlamalar roʻyxat boʻyicha toʻliq:
`DEBUG=False`, `ALLOWED_HOSTS` env'dan, HSTS bir yil + subdomenlar +
preload, cookie'lar `Secure`, `X-Frame-Options: DENY`,
`SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`. `SECRET_KEY`
yoʻq boʻlsa yoki 32 baytdan qisqa boʻlsa server **boot'da toʻxtaydi** —
yoʻriqnomadagidan qatʼiyroq. Kirish 20/min, roʻyxatdan oʻtish 5/soat
bilan cheklangan.

**Aytilgan, lekin qoʻyilmagan kafolat.** `document_download` izohida
"fayl `/media/` havolasi orqali emas, SHU endpoint orqali beriladi"
deb yozilgan edi — sabab ham toʻgʻri koʻrsatilgan: statik media URL'i
na kirishni, na tashkilot chegarasini biladi. Lekin nginx `/media/` ni
baribir ochiq berardi, yaʼni tibbiy maʼlumotnoma uchun ruxsat
tekshiruvi bezak edi. Fayl nomi UUID boʻlgani uchun tashqaridan topish
amalda mumkin emas, lekin bitta havolaning tarqashi (tarix, chat,
skrinshot) yetarli boʻlardi. Endi `^/media/[^/]+/absence/` → `404`
(`deny` emas: 403 faylning BOR ekanini aytib qoʻyardi), ikkala
konfigda ham, va qoida testda.

**Indekslar — teshik yoʻq.** RLS siyosati har bir soʻrovga
`organization_id = …` qoʻshadi, yaʼni u indekslanmagan jadvalda har bir
soʻrov seq scan boʻlardi. Jonli bazada tekshirildi: `organization_id`
bor **57 ta jadvalning hammasida** u indeksning birinchi ustuni.

**300 bolalik oʻlchov va bitta N+1.** Jonli bazada hozir 82 ta bola
bor — yaʼni miqyos muammosini u yerda koʻrib boʻlmaydi. 300 bolali
bogʻcha yasab oʻlchandi va **bolalar roʻyxati 50 qatorlik sahifa uchun
58 ta soʻrov** qilardi: serializer `tariff.name` ni oʻqiydi, queryset
esa `select_related("tariff")` qilmagan edi — har bir bola uchun
bittadan `tariff_plan` soʻrovi. Tuzatildi: **58 → 8 soʻrov**, 75 → 28
ms. Qolganlari toza edi (qarzdorlar 7, toʻlovlar doskasi 6, tushum
hisoboti 9, dashboard 38 — oxirgisi koʻp, lekin bolalar sonidan
qatʼi nazar oʻzgarmaydi).

Qarzdorlar roʻyxati soʻrov soni boʻyicha toza, lekin vaqt boʻyicha eng
sekini: 489 ms. Sabab — har bir qator uchun toʻrtta bogʻliq ichki
soʻrov (`balance.with_balance`), indekslar esa joyida. Bu docs/03 §25
da allaqachon yozilgan yoʻl: agar sekinlashsa — materiallashgan
koʻrinish. Endi oʻlchov testda, yaʼni regressiya koʻrinadi.

**Oʻzgartirilmagan, savol sifatida qoldirilgani:** parol minimal
uzunligi — Django sukuti, 8 belgi. Yoʻriqnoma 12 ni tavsiya qiladi,
lekin ADR-24 xodimlar qulayligi haqida ataylab qaror qabul qilgan
(bogʻcha xodimlari telefon almashadi, majburiy ogʻirlik butun
jamoani bitta qurilmaga surardi). Bu biznes qarori — egasiniki.

**Eng jiddiy topilma: moliyaviy eksportlar ochiq edi.** `/media/` yoʻli
nginx tomonidan autentifikatsiyasiz beriladi, va uning ostida ikkita
narsa yotardi: bolaning tibbiy maʼlumotnomasi va **qarzdorlar roʻyxati
eksportlari**. Ikkalasining ham ilovada ruxsat tekshiradigan endpointi
bor va ikkalasining ham izohida aynan shunday yozilgan — "fayl
`/media/` havolasi orqali emas, SHU endpoint orqali beriladi", sababi
ham toʻgʻri koʻrsatilgan: statik media URL'i na kirishni, na tashkilot
chegarasini biladi. nginx esa ularni baribir berardi.

Maʼlumotnomalar uchun fayl nomi UUID, yaʼni tashqaridan topish amalda
mumkin emas — xavf bitta havolaning tarqashida edi. Eksportlar esa
battarroq: ularning nomi UUID EMAS, `debtors-20260923-1001.csv`
koʻrinishida — sana va daqiqa, yaʼni sanab chiqsa boʻladi. Productionda
tekshirildi: eksport URL'i hech qanday tokensiz **200** qaytardi.

Tuzatish taqiq roʻyxati emas, **ruxsat roʻyxati** boʻldi. Ommaviy
boʻlishi kerak boʻlgan narsa ikkitagina — `{org}/brand/` (logotip) va
`{org}/avatars/` (foydalanuvchi rasmi), chunki brauzer ularni `<img>`
sifatida tokensiz oladi. Qolgan hamma narsa 404. Shunda keyingi
`upload_to` yoʻli **sukut boʻyicha yopiq** boʻladi; taqiq roʻyxatida esa
uni eslab qoʻshish kerak boʻlardi — va aynan shu ikki marta unutilgan.

Jonli tekshiruv: logotip 200, eksport 404, maʼlumotnoma 404, demo
stendda ham 404.

**Celery: bitta davr uchun ikkinchi hisob yozilishi mumkin edi.**
Sozlamalar roʻyxati toza — `ACKS_LATE`, `REJECT_ON_WORKER_LOST`,
`PREFETCH_MULTIPLIER=1`, yumshoq/qattiq vaqt chegarasi,
`visibility_timeout` vaqt chegarasidan katta, vaqt zonasi
`Asia/Tashkent`, qayta urinish esa faqat **oʻtkinchi** xatolarda
(`BusinessRuleViolation` ataylab roʻyxatda yoʻq: "tarif belgilanmagan"
besh marta urinishdan toʻgʻrilanmaydi).

Lekin aynan `ACKS_LATE` har bir vazifadan **ikki marta ishlashga
chidashni** talab qiladi, va `close_periods_and_invoice` chidamasdi.
Uning ichida uch qadam bor: oʻlchovni yop → hisob yoz → davrni surish.
Ular bitta tranzaksiyada emas edi. Ishchi hisob yozilgandan KEYIN,
davr surilishidan OLDIN yiqilsa (deploy, OOM, broker uzilishi) vazifa
qayta yetkaziladi, `current_period_end` hali oʻtmishda boʻladi,
yuqoridagi qoʻriqchi oʻtkazib yuboradi — va mijoz **ikkinchi marta**
hisob oladi.

Bazada ham tutqich yoʻq edi: tuition `invoice` da
`uq_invoice_child_period` bor, obuna hisob-fakturasida esa hech narsa —
`issue_invoice` shartsiz `create()` qilardi. Ikkalasi ham tuzatildi:
uch qadam bitta tranzaksiyada, va `uq_sub_invoice_period` (bekor
qilingani chetda — xato hisobni bekor qilib, toʻgʻrisini yozish yoʻli
ochiq qolsin). Productionda dublikat yoʻqligi migratsiyadan oldin
tekshirildi.

Xabarlar uzatish allaqachon idempotent va buni oʻz hujjatida aytadi:
faqat `queued` va urinishlari tugamagan `failed` olinadi, yuborilgani
`sent` boʻlib roʻyxatdan chiqadi.

**Hujjat va kod ajralib qolgan joylar.** Loyihaning 3-qoidasi —
"hujjat va kod BIRGA oʻzgaradi" — bugun ikki marta buzilgan edi.
Tizimli tekshiruv (har bir model jadvali `docs/03` da uchraydimi)
toʻrtta boʻshliq koʻrsatdi, ularning ikkitasi bugungi ish emas:

* `expense_item` — chiqim qatorlari (PLAN 7.5), umuman yozilmagan;
* `report_export` — eksport ishlari jadvali;
* `platform_user`, `support_grant` — vendor tekisligi. Ularda
  `organization_id` bor, lekin RLS yoʻq — va bu **qaror** boʻlishi
  kerak, keyin kimdir topadigan **unutish** emas, shuning uchun
  sxema hujjatiga §19a boʻlib yozildi.

Shu bilan birga bugun qoʻshilganlari ham yozildi:
`employee_advance.cash_account_id`, `uq_sub_invoice_period` va
`POST /cash-accounts/{id}/adjust` (`docs/04`).

Migratsiyalar tekshiruvi topilmasiz: oʻnta maʼlumot migratsiyasining
hammasida teskari funksiya bor, yaʼni qaytarib boʻladi.

**Obuna darvozasining koʻr nuqtasi.** `test_write_gate_is_everywhere`
cross-tenant sweep bilan bir xil falsafada yozilgan — qoidani odam
yodida saqlashiga tayanmaslik. Lekin u **faqat `router.registry`** ni
koʻrardi, yaʼni oddiy `APIView` undan butunlay chetda qolardi: yangi
yozuv endpointi qoʻshilsa, u toʻlamagan mijozga ham ishlayverardi va
hech bir test qizarmasdi. Bu bugungi uchinchi bir xil shakldagi
topilma (RLS roʻyxati, sweep, darvoza — uchalasi ham qoidani faqat
bitta roʻyxat ichida qoʻriqlardi).

Tekshirib chiqilganda routerdan tashqarida **27 ta** yozuv endpointi
topildi va ularning hech birida darvoza yoʻq edi — lekin hammasi ham
asosli: invariant 11 aytadi, toʻxtatilgan obuna YOZISHNI toʻxtatadi,
KIRISHNI emas. Toʻlamagan mijoz tizimga kira olishi, parolini tiklay
olishi va hisobini toʻlay olishi shart. Eng muhimi — **toʻlov
webhook'lari**: ularni darvozaga qoʻyish toʻxtatilgan mijozning
toʻlovini rad etardi, yaʼni darvoza oʻzini oʻzi yopib qoʻyardi.

Har biriga sabab yozilib, test kengaytirildi: endi yangi `APIView`
muallifi ikki narsadan birini tanlashi kerak — yo darvoza, yo sabab.
Isbot: mavjud darvozani vaqtincha olib tashlaganda test qizardi.

**Servis qatlami — topilma yoʻq.** 8 ta view boshqa ilovaning modelini
import qiladi, lekin hammasi bir xil shaklda: soʻrovdagi ID ni qatorga
aylantirish (`Model.objects.filter(pk=…).first()`), tenant menejeri esa
begona qatorni "topilmadi" qiladi. Bu — `TenantPrimaryKeyRelatedField`
ning boshqa koʻrinishi, biznes mantiqi emas. 1-invariant modul B ning
qoidalarini modul A da takrorlamaslik uchun bor; bu yerda bunday narsa
yoʻq.

**Frontend koʻrigi: kalitlar toza, bitta memo nuqsoni.** TanStack Query
kalitlarining hammasi tashkilot bilan qamralgan — qamralmaganlari
platforma konsoli (bitta vendor), ommaviy narx sahifasi va shartnoma
oʻrinbosarlari roʻyxati, oxirgisi esa haqiqatan global konstanta
(`sorted(services.PLACEHOLDERS)`), yaʼni `staleTime: Infinity` toʻgʻri.
Hook qoidalari (`rules-of-hooks`, `exhaustive-deps`) yoqilgan va butun
frontendda **bitta** ogohlantirish bor edi: davomat sahifasida
`rows = query.data?.rows ?? []` har renderda yangi massiv yasardi,
yaʼni quyidagi `useMemo` keshdan hech qachon foydalanmay, guruhdagi
har bir bola boʻylab har bosishda qayta aylanardi. Bu sahifa har kuni
ertalab ishlatiladi — memo qoʻshildi, ogohlantirish nolga tushdi.

**Oʻlik kod.** `knip` uchta chaqirilmaydigan faylni koʻrsatdi va
hammasi tasdiqlandi: `RecordPaymentModal` (289 qator) va
`InvoicePaymentsModal` (211) — ularning oʻrnini `TakePaymentModal`
egallagan; `components/ui/form.tsx` (84) — shadcn'ning React Hook Form
oʻramasi. Oʻchirildi, 584 qator. Lugʻatda qolgan 13 ta yetim kalitni
`catalog.test.ts` oʻzi ushladi — aynan shuning uchun u bor.

`scripts/og.mjs` oʻlik emas: u qoʻlda ishga tushiriladigan vosita
(brend oʻzgarganda ulashish rasmlarini qayta chizadi), knip esa buni
koʻra olmaydi.

**Egasiga savol: hujjatdagi forma strategiyasi.** `docs/05` sakkiz
joyda "React Hook Form + Zod — har bir create/edit formasida" deb
yozilgan (F3, §Forms). Kod esa ularni **hech qachon import qilmagan**:
formalar qoʻlda, `useState` bilan yozilgan, va bu oʻn ikki sprint
davomida shunday. `react-hook-form`, `zod` va `@hookform/resolvers`
package.json da turibdi, lekin hech qayerda ishlatilmaydi.

Paketlarni oʻchirib yubormadim — bu hujjatdagi arxitektura qarorini
jimgina hal qilib qoʻyardi, u esa egasiniki. Ikki yoʻl bor: yo yangi
formalar uchun RHF+Zod qabul qilinadi (paketlar qoladi), yo hujjat
haqiqatga moslanadi (paketlar ketadi). Ishlayotgan formalarni qayta
yozish uchun sabab yoʻq.

## Brauzerdagi E2E — va u topgan ikkita nosozlik

Unit testlar komponentni, backend testlari endpointni tekshiradi.
Oʻrtadagi narsani — token haqiqatan olinadimi, forma haqiqatan
yuboriladimi, javob ekranda haqiqatan koʻrinadimi — hech kim
tekshirmasdi. Playwright qoʻshilgan kundayoq ikkita nosozlik chiqdi.

**Birinchisi: bola formasida native `input[type=date]`.** Playwright
sanani `dd.mm.yyyy` koʻrinishida kirita olmadi, chunki maydon
brauzerning oʻziniki edi. 05 §17.1 buni nomma-nom taqiqlaydi va
sababini ham aytadi — brauzer `mm/dd/yyyy` koʻrsatadi va bogʻcha
xodimi uni teskari oʻqiydi. Qoida hujjatda bor edi va ilovadagi eng
koʻp ishlatiladigan formada buzilgan edi. Ikkala joy (bola formasi va
xodimlar tabeli) tuzatildi, qoida `a11y.test.ts` ga qoʻshildi.

**Ikkinchisi, jiddiyroq: sahifani qayta yuklash tizimdan chiqarardi.**
`page.reload()` dan keyin test `/private/login` da edi. Sabab:
`radix_refresh` cookie'ning yoʻli `/api/v1/auth` deb qotirilgan.
Brauzer cookie'ni faqat uning yoʻli ostidagi soʻrovlarga yuboradi, va
standalone nusxada API `/private/api/v1/auth` da — yaʼni cookie
**umuman yuborilmasdi**, access token esa faqat xotirada (04 §5). Har
bir F5 — qaytadan parol. Havolani yangi tabda ochish ham shunday.

SaaS zarar koʻrmagan, shuning uchun uni hech kim sezmagan: u yerda API
haqiqatan ildizda va qotirilgan yoʻl tasodifan toʻgʻri. Lekin ADR-13
standalone'ni **sotiladigan** ikkinchi model deb belgilaydi. Yoʻl endi
`PUBLIC_BASE_URL` dan olinadi (Django prefiksni oʻzi bilmaydi — nginx
uni soʻrovdan olib tashlaydi), chiqishda esa eski yoʻldagi nusxa ham
oʻchiriladi.

**Toʻplam haqida.** Besh stsenariy: kirish (notoʻgʻri parol va
autentifikatsiyasiz kirish bilan), bola qoʻshish, toʻlov qabul qilish,
davomat, qarzdorlar. Ikki qurilmada — desktop va 375 px (PLAN 10.3
auditlari aynan shu enda oʻtkazilgan). Ikki xossa atrofida qurilgan:

* **yozadi**, shuning uchun `/private` demo stendiga qarshi ishlaydi —
  hech qachon mijozникiga;
* **oʻzidan keyin tozalaydi**: bola arxivlanadi, toʻlov mahsulotning
  oʻz qarshi-yozuv yoʻli bilan qaytariladi — yaʼni eng qimmat yoʻl ham
  sinaladi va demo ifloslanmaydi.

Uch dars yozib qoʻyildi, chunki uchalasiga ham ketma-ket tushildi:
`baseURL` oxirida `/` boʻlmasa `goto('login')` jimgina BOSHQA stendga
uradi; bu ilovada koʻp ekran ikki marta chizilgan (telefon kartochkasi
va `sm:` jadval), shuning uchun `.first()` koʻpincha YASHIRINganini
tanlaydi — `firstVisible` yordamchisi shundan; va stendning holatiga
tayangan test bir marta ishlaydi — davomat testi endi oʻz shartini oʻzi
yaratadi.

## CI: nuqson workflow faylida emas

Bugun qoʻshilgan qoʻriqchi testlar (RLS roʻyxati, obuna darvozasi,
`DateInput`, formatlash uyi, fokus tutqichi) faqat **haqiqatan ishga
tushsa** maʼnoga ega. Shuning uchun CI tekshirildi — va u hech qachon
ishlamagan: **66 tadan 66 tasi** `startup_failure`, reponing birinchi
kunidan (2026-08-03) 2026-10-02 gacha, birorta muvaffaqiyat yoʻq.

Bu daqiqalar tugashi emas: tugaganda avval muvaffaqiyatli ishga
tushishlar boʻlardi. Fayl ham emas — tekshirildi:

* ikkala workflow ham toʻgʻri YAML (GitHub ishga tushirgan aynan
  oʻsha revizia ham);
* `actions/checkout@v4`, `setup-node@v4`, `setup-python@v5` — uchalasi
  mavjud va arxivlanmagan;
* repo'da Actions yoqilgan (`allowed_actions: all`);
* BOM, CRLF yoki TAB yoʻq;
* hech qanday ish (job) yaratilmagan va izoh (annotation) yozilmagan —
  yaʼni nosozlik birinchi qadamdan OLDIN.

Qolgani hisob darajasida — sarf chegarasi yoki Actions daqiqalari.
Uni tasdiqlash uchun ikki yoʻl bor va ikkalasi ham egasining qarorini
talab qiladi: billing uchun `user` ruxsatini kengaytirish, yoki sinov
uchun kichik workflow yuborish.

**Alohida va muhimroq topilma: tarmoq hech qachon yuborilmagan.**
`origin/main` 2026-10-02 dagi `11da61a` da turibdi, `big-update/
phase-6-code` esa remote'da umuman yoʻq — **137 ta commit** faqat shu
kompyuterda va serverdagi rsync nusxasida (unda git tarixi yoʻq,
chunki deploy `.git` ni chiqarib tashlaydi). Yaʼni CI'ning tuzalishi
ham oʻz-oʻzidan hech narsa bermasdi: tekshiradigan kod u yerga
chiqmagan.

Yuborish — texnik emas, biznes qarori: repo'da hamkorning tarmoqlari
bor (`abzal`, `abzal2`), kelishuv esa hali imzolanmagan. Shuning uchun
men yubormadim.

## Beshta ochiq qaror — yopildi

**1. Yuborish: YOʻQ, zaxira: HA.** Repo'da ikki nafar hamkorda push
huquqi bor (`abzal4-wq`, `isa704480`), kelishuv esa imzolanmagan.
137 commitni koʻrinadigan qilish muhandislik emas, tijorat qarori —
shuning uchun yubormadim. Xavf esa (bitta nusxa) tashqariga
chiqmasdan yopildi: `~/kg-crm-backups/` da toʻliq `git bundle`,
tekshirildi — undan klon qilinganda 209 commit tarixi bilan
`72ee32f` tiklanadi.

**2. CI billing: tasdiqlab boʻlmadi.** `gh auth refresh -s user`
brauzer orqali tasdiqlashni talab qiladi, yaʼni avtomatik bajarib
boʻlmaydi. Diagnoz hujjatda: nuqson fayl emas, hisob darajasida.
Tarmoq yuborilgan kuni CI oʻzi javob beradi.

**3. Eski eksportlar: oʻchiriladigan boʻldi.** `purge_old_exports`
buyrugʻi yozildi (sukut 30 kun, dry-run). Buyruq birinchi variantda
`platform_context()` ichida yozilgan edi va **"tozalaydigan narsa
yoʻq"** deb chiqardi: `report_export` — operatsion jadval, platforma
uchun chiqishi yoʻq (ADR-10), yaʼni u yerda boʻsh koʻrinadi. Jim
muvaffaqiyat eng yomon turi — endi buyruq har bir tashkilotga oʻz
kontekstida kiradi.

**4. Parol: 8 → 12.** Tizim bolalarning shaxsiy maʼlumotini va pulni
saqlaydi; OWASP ASVS shunday ilova uchun 12 ni talab qiladi. Kirish
20/min bilan cheklangan, yaʼni asosiy xavf zaif yoki boshqa saytdan
oʻgʻirlangan parol — unga qarshi aynan UZUNLIK ishlaydi.
**Murakkablik qoidasi qoʻshilmadi**: aynan u xodimni parolni qogʻozga
yozishga majbur qiladi, uzunlik esa qilmaydi
("bahorbogchasi2026" oson eslanadi). ADR-24 bogʻcha xodimlari haqida
shu mulohazani yuritadi va bu unga zid emas. Mavjud parollar
tegilmaydi.

Shu yerda uchta raqam yashirin yashab yurgani ham chiqdi: backend 8,
profil sahifasi 10, qolgan **uchta** parol oʻrnatish ekranida esa
umuman tekshiruv yoʻq — odam parol yozadi, tugmani bosadi va
serverdan tushunarsiz xato oladi. Raqam endi `lib/password.ts` da,
toʻrtala ekranda koʻrsatiladi, va test uni `base.py` dagi
`min_length` bilan solishtiradi — ajralib keta olmaydi.

**5. Forma strategiyasi: hujjat kodga moslandi.** `docs/02` va
`docs/05` oʻn ikki joyda "React Hook Form + Zod — har bir create/edit
formasida" deb yozilgan edi; kod esa ularni hech qachon import
qilmagan. Ishlayotgan formalarni hujjatga moslash uchun qayta yozish —
foydasi yoʻq churn. Shuning uchun §12 haqiqatni va uning SABABINI
yozadi: validatsiya baribir backendda (CHECK, servis qoidasi), Zod
sxemasi esa oʻsha qoidaning IKKINCHI nusxasi boʻlardi — bu loyiha
ikki nusxaning ajralib ketishi uchun allaqachon ikki marta toʻlagan
(balans formulasi va oʻn yettita shaxsiy `money()`).

Buning evaziga §12 uchta shart qoʻyadi: server xatosi maydonga
tushsin; foydalanuvchi **oldindan** bilishi kerak boʻlgan qoida
ekranda yozilsin (parol uzunligi — ishlab koʻrilgan namuna); va
sanalar faqat `DateInput`. Uchalasi ham testda. `react-hook-form`,
`zod`, `@hookform/resolvers` package.json dan olib tashlandi.

**Va tozalashning oʻzi diskda iz qoldirgani.** Productionda quruq
tekshiruv **0 ta** eskirgan eksport koʻrsatdi, diskda esa toʻrtta
fayl va bazada uchta qator bor edi — yaʼni bittasi **yetim**. Sabab:
Django `queryset.delete()` `FileField` blobini oʻchirmaydi.
`reset_organization_data` ishlaganda qatorlar ketgan, qarzdorlar
CSV'si esa diskda qolgan. "Toza varaq" diskda toza emas edi.

Ikkalasi tuzatildi: tozalash buyrugʻi endi qatordan OLDIN fayllarni
oʻchiradi, `purge_old_exports` esa `exports/` ichidagi birorta qator
ishora qilmaydigan fayllarni ham supuradi — bunday fayl hech kim
yuklab ololmaydigan, lekin diskda turgan maʼlumot.

**Bir marta tozalash yetmaydi.** Eksportlar serverdan oʻchirildi
(uchta eskirgan yozuv va bitta yetim fayl; eski URL endi 404 va fayl
ham yoʻq). Lekin sabab oʻz joyida qolardi: ularni hech narsa
oʻchirmaydi, yaʼni ertaga yana yigʻila boshlaydi. Shuning uchun mantiq
servisga koʻchirildi (`reports.services.purge_old_exports`), buyruq va
tunlik Celery vazifasi **bitta** mantiqdan oʻqiydi — ikkisi ikki xil
narsa qilsa, qaysi biri toʻgʻri ekanini keyin hech kim ayta olmasdi —
va vazifa beat jadvaliga yozildi (har kuni 04:30). Jadvalning oʻzi
ham testda: yozilmagan vazifa — yozilmagan vazifa.
