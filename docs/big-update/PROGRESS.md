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
