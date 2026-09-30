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

### O'zgardi
- Ortiqcha to'lov endi rad etilmaydi — ortig'i avansga aylanadi (Q1).
- `payroll.income_tax_rate` va `payroll.pension_rate` sukut qiymati
  0 ga tushdi (Q10). Yakunlangan hisoblar o'zgarmaydi.
- Narxi ko'rsatilgan ombor xaridi chiqim yozuvini yaratadi (Q13).

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
