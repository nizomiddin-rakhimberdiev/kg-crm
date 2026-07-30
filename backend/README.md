# KG-CRM — Backend

Kindergarten Management System (KG-CRM) uchun **Django + DRF** backendi.

> **Holat:** papka hozircha bo'sh skelet. Django loyihasining o'zi
> [docs/06_Development_Roadmap.md](../docs/06_Development_Roadmap.md) dagi **Sprint 0**
> da yaratiladi. Bu papka shu ish uchun tayyorlab qo'yilgan (struktura + `.gitignore` + `.env.example`).

## Texnologiyalar

Python · Django · Django REST Framework · PostgreSQL · Redis · Celery · JWT · Docker · Nginx · Gunicorn

## Maqsadli tuzilma

To'liq va majburiy tuzilma [docs/02_Software_Architecture.md §5](../docs/02_Software_Architecture.md) da belgilangan:

```
backend/
├── config/          # Loyiha konfiguratsiyasi (biznes app EMAS)
│   └── settings/    # base.py · development.py · production.py · test.py
├── apps/            # BARCHA biznes modullar shu yerda
│                    # core, organizations, subscriptions, platform,
│                    # accounts, branches, children, attendance, finance,
│                    # hr, payroll, inventory, expenses, reports, notifications,
│                    # settings_app, audit
├── api/v1/          # router.py — barcha app router'larini /api/v1/ ostida yig'adi
├── requirements/    # base.txt · development.txt · production.txt
├── manage.py
├── Dockerfile
├── docker-compose.yml
└── pytest.ini
```

`apps/` ichidagi **har bir** app bir xil ichki shaklga ega bo'ladi
(`services.py` — yozish, `selectors.py` — o'qish, `views.py` — faqat yupqa orkestratsiya).
Batafsil: [docs/02_Software_Architecture.md §5](../docs/02_Software_Architecture.md).

### Uchta SaaS app'i nima uchun alohida

| App | Vazifasi |
|-----|----------|
| `organizations` | **Tenancy ildizi** — mijoz (bog'cha biznesi). Bazadagi har bir operatsion qator shu yerga ishora qiladi (ADR-9). |
| `subscriptions` | Tariflar, obunalar, trial, bola sonini o'lchash (`usage_snapshot`), obuna hisob-fakturalari (ADR-11). |
| `platform` | Sotuvchi (biz) tomonidagi konsol — alohida kirish yo'li, majburiy 2FA, faqat **metama'lumot** (ADR-10). |

## Buzilmas qoidalar (invariantlar)

1. Biznes mantiq **faqat** `services.py` da; o'qish `selectors.py` da.
2. Har bir operatsion jadvalda **`organization_id`** (xavfsizlik chegarasi — **hech kim buzib o'tolmaydi**) va `branch_id` (operatsion doira). Tashqi tenant'ga murojaat **`404`** qaytaradi, `403` emas.
3. Pul va ombor — **append-only ledger**; tuzatish faqat qarshi yozuv bilan.
4. RBAC — data-driven, deny-by-default, backend'da majburlanadi. `Super Admin` roli **yo'q**: mijoz tomonida `org_owner`, sotuvchi tomonida alohida plane.
5. API — `/api/v1/` ostida versiyalangan, yagona envelope va xato formati.
6. Obuna to'lovlari — o'zgarmas `usage_snapshot` ga asoslanadi; `subscriptions` va `finance` jadvallari **hech qachon** aralashmaydi.

To'liq ro'yxat: [CLAUDE.md](../CLAUDE.md) → *Locked Invariants*.

## Har bir PR dan oldin ikkita tekshiruv

1. Yangi jadvalda `organization_id NOT NULL` bormi? (Yagona istisno: `permission` va `subscription_plan`.)
2. Yangi endpoint uchun cross-tenant testi bormi — A tashkiloti B ning qatorini o'qiy olmasligi va javob `404` ekani?

Bu uslub masalasi emas. Noto'g'ri hisoblangan balansni keyin to'g'rilash mumkin; bolalar ma'lumotlarining boshqa tenant'ga sizib chiqishini esa — yo'q.

## Ishga tushirish (Sprint 0 dan keyin)

```bash
cp .env.example .env      # qiymatlarni to'ldiring
docker compose up         # web · db · redis · worker · beat
```

## Migratsiyalar haqida

`migrations/` papkalari **git'ga qo'shiladi** — ular sxema tarixining bir qismi
([docs/03_Database_Design.md](../docs/03_Database_Design.md)). `.gitignore` faqat
ular ichidagi `__pycache__` ni chetlab o'tadi.
