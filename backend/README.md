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
│                    # core, accounts, branches, children, attendance, finance,
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

## Buzilmas qoidalar (invariantlar)

1. Biznes mantiq **faqat** `services.py` da; o'qish `selectors.py` da.
2. Har bir operatsion jadvalda `branch_id` — barcha so'rovlar branch bo'yicha cheklanadi.
3. Pul va ombor — **append-only ledger**; tuzatish faqat qarshi yozuv bilan.
4. RBAC — data-driven, deny-by-default, backend'da majburlanadi.
5. API — `/api/v1/` ostida versiyalangan, yagona envelope va xato formati.

To'liq ro'yxat: [CLAUDE.md](../CLAUDE.md) → *Locked Invariants*.

## Ishga tushirish (Sprint 0 dan keyin)

```bash
cp .env.example .env      # qiymatlarni to'ldiring
docker compose up         # web · db · redis · worker · beat
```

## Migratsiyalar haqida

`migrations/` papkalari **git'ga qo'shiladi** — ular sxema tarixining bir qismi
([docs/03_Database_Design.md](../docs/03_Database_Design.md)). `.gitignore` faqat
ular ichidagi `__pycache__` ni chetlab o'tadi.
