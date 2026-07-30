# KG-CRM — Bog'cha boshqaruv tizimi

Bog'chalar uchun **CRM + ERP + LMS** ni birlashtirgan **multi-tenant SaaS** platforma.
MVP — xodimlar uchun back-office; arxitektura parent/teacher portallari va onlayn
to'lovlarga **qayta yozmasdan** o'sadigan qilib loyihalangan.

**Biznes modeli** ([docs/01 §4](./docs/01_Project_Vision.md)): har bir mijoz — **tashkilot**,
bitta obuna ostida **cheksiz filial**. Narx bola soniga qarab: baza 500 000 so'm/oy
(50 bolagacha), undan yuqorisi har 10 bola uchun +80 000. To'lov: oylik (0%),
yarim yillik (−15%), yillik (−25%). 15 kunlik risksiz sinov.

## Repozitoriy tuzilishi

```
kg-crm/
├── docs/        # YAGONA HAQIQAT MANBAI — arxitektura, DB, API, roadmap
├── backend/     # Django + DRF API (Sprint 0 da yaratiladi)
├── frontend/    # React + TypeScript + Vite SPA
└── CLAUDE.md    # Loyihada ishlash protokoli
```

Har bir stack o'zining `.gitignore` fayliga ega; ildizdagi `.gitignore` faqat
umumiy narsalarni (OS, editor, `.env`) qamrab oladi.

## Hujjatlar (shu tartibda o'qing)

| # | Fayl | Nima haqida |
|---|------|-------------|
| 00 | [docs/00_INDEX.md](./docs/00_INDEX.md) | Xarita |
| 01 | [docs/01_Project_Vision.md](./docs/01_Project_Vision.md) | Maqsad, doira, talablar |
| 02 | [docs/02_Software_Architecture.md](./docs/02_Software_Architecture.md) | Arxitektura, modullar, xavfsizlik |
| 03 | [docs/03_Database_Design.md](./docs/03_Database_Design.md) | Ma'lumotlar bazasi dizayni |
| 04 | [docs/04_Backend_API_Specification.md](./docs/04_Backend_API_Specification.md) | API spetsifikatsiyasi |
| 05 | [docs/05_Frontend_Architecture.md](./docs/05_Frontend_Architecture.md) | Frontend arxitekturasi |
| 06 | [docs/06_Development_Roadmap.md](./docs/06_Development_Roadmap.md) | Sprintlar va yo'l xaritasi |

> **Oltin qoida:** `docs/` — yagona haqiqat manbai. Kod va hujjatlar birga o'zgaradi.

## Texnologiyalar

**Backend:** Python · Django · DRF · PostgreSQL · Redis · Celery · JWT · Docker · Nginx · Gunicorn
**Frontend:** React · TypeScript · Vite · Tailwind · Shadcn/UI · TanStack Query · React Hook Form · Zod · React Router · Axios · Recharts · Framer Motion

## Ishga tushirish

**Frontend** (hozir ishlaydi, mock ma'lumotlar bilan):

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

**Backend** — [backend/README.md](./backend/README.md) ga qarang (Sprint 0 kutilmoqda).

## Joriy bosqich

Arxitektura va dizayn (01–06 hujjatlar) yakunlangan. Frontend UI skeleti tayyor.
Keyingi qadam — **Sprint 0: backend scaffolding**
([roadmap](./docs/06_Development_Roadmap.md)).
