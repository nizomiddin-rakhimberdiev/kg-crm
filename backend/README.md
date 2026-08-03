# KG-CRM — Backend

Kindergarten Management System (KG-CRM) uchun **Django + DRF** backendi.

> **Holat: Sprint 0 bajarildi.** Django loyihasi, tenancy poydevori,
> `organization`/`user` modellari, konvert, health check, Docker va CI tayyor.
> Keyingi qadam — Sprint 1 (auth, rollar, filiallar).

## Texnologiyalar

Python 3.13 · Django 5.2 LTS · Django REST Framework · PostgreSQL 17 · Redis · Celery · Docker · Nginx · Gunicorn

> Django **6.0 emas, 5.2 LTS** ataylab: LTS uzoq muddat xavfsizlik yangilanishlarini
> oladi va majburiy versiya migratsiyalarini talab qilmaydi — solo loyihada bu
> eng so'nggi versiyadan qimmatroq ([docs/06 §2](../docs/06_Development_Roadmap.md)).

## Ishga tushirish

**Docker bilan (tavsiya):**

```bash
cp .env.example .env
docker compose up --build
docker compose exec web python manage.py migrate
```

**Docker'siz (lokal Postgres bilan):**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements/development.txt
cp .env.example .env          # POSTGRES_HOST=localhost qiling
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Tekshirish:

```bash
curl http://127.0.0.1:8000/api/v1/health
# {"success":true,"data":{"status":"ok","checks":{"database":"ok"}},...}
```

## Testlar va sifat darvozalari

```bash
.venv/bin/python -m pytest              # barcha testlar
.venv/bin/python -m pytest -m tenancy   # faqat tenant izolyatsiyasi
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy apps api config
```

Xuddi shu qadamlar CI da ham ishlaydi ([.github/workflows/backend.yml](../.github/workflows/backend.yml)).
Solo loyihada CI yagona reviewer — shuning uchun u maslahat emas, darvoza.

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

## Tenancy qanday ishlaydi (amalda)

Tashkilot **hech qachon mijozdan** olinmaydi — `TenantMiddleware` uni
autentifikatsiya qilingan foydalanuvchidan oladi va `ContextVar` ga qo'yadi.
`TenantManager` esa uni default queryset'da qo'llaydi:

```python
Child.objects.all()          # → avtomatik WHERE organization_id = <joriy>
Child.objects.all()          # kontekstsiz → TenantScopeMissing (fail-closed)
Child.objects.unscoped()     # ataylab filtrsiz — grep bilan topiladi
```

Uch qatlamli himoya:

| Qatlam | Nima qiladi |
|--------|-------------|
| `TenantManager` | Default queryset'da filtr — view yozuvchi uni unuta olmaydi |
| DB trigger | `organization_id` ni UPDATE qilishni bloklaydi (shell/skript ham) |
| Postgres RLS | Sprint 11 da qo'shiladi — ikkinchi mustaqil qatlam |

## Har bir PR dan oldin ikkita tekshiruv

1. Yangi jadvalda `organization_id NOT NULL` bormi? (Yagona istisno: `permission` va `subscription_plan`.)
2. Yangi endpoint uchun cross-tenant testi bormi — A tashkiloti B ning qatorini o'qiy olmasligi va javob `404` ekani?

Bu uslub masalasi emas. Noto'g'ri hisoblangan balansni keyin to'g'rilash mumkin; bolalar ma'lumotlarining boshqa tenant'ga sizib chiqishini esa — yo'q.

Yangi tenant-scoped jadval qo'shganda migratsiyada trigger'ni ham ulang:

```python
from apps.core.db import attach_tenant_guards

operations = [
    migrations.CreateModel(name="Child", ...),
    *attach_tenant_guards("child"),
]
```

## Ishga tushirish (Sprint 0 dan keyin)

```bash
cp .env.example .env      # qiymatlarni to'ldiring
docker compose up         # web · db · redis · worker · beat
```

## Migratsiyalar haqida

`migrations/` papkalari **git'ga qo'shiladi** — ular sxema tarixining bir qismi
([docs/03_Database_Design.md](../docs/03_Database_Design.md)). `.gitignore` faqat
ular ichidagi `__pycache__` ni chetlab o'tadi.
