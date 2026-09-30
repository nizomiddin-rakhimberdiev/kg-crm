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
