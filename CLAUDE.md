# CLAUDE.md — Operating Protocol for KG-CRM

This file is loaded automatically every session. It tells Claude (and any developer) **how to work on this project so context is never lost and decisions never contradict each other.**

---

## What this project is

**Kindergarten Management System (KG-CRM)** — a **hosted multi-tenant SaaS** platform combining **CRM + ERP + LMS** for kindergartens. MVP is a staff-facing back-office; the architecture is designed to grow into parent/teacher portals and online payments without rewrites.

**Commercial model** ([01 §4](./docs/01_Project_Vision.md)): each customer is an **organization** with unlimited branches under **one subscription**, priced per enrolled child — base 500 000 UZS/month including 50 children, +80 000 per additional 10. Payment terms: monthly (0 %), semi-annual (−15 %), annual (−25 %). 15-day risk-free trial; on conversion the first paid month is dated from the trial start, disclosed at signup.

---

## THE GOLDEN RULE

> **The `docs/` folder is the single source of truth. Read it before you design, answer, or write code. Keep it consistent when decisions change.**

On large projects, the two things that kill quality are (1) **lost context** and (2) **contradictory decisions** accumulating over time. This doc set exists to prevent both. Do not re-derive or re-decide something the docs already settle — follow the docs.

---

## Canonical Documents (read in this order)

| # | File | Read before you… |
|---|------|------------------|
| 00 | [docs/00_INDEX.md](./docs/00_INDEX.md) | anything (it's the map) |
| 01 | [docs/01_Project_Vision.md](./docs/01_Project_Vision.md) | discussing scope, goals, or requirements |
| 02 | [docs/02_Software_Architecture.md](./docs/02_Software_Architecture.md) | touching structure, apps, security, infra |
| 03 | [docs/03_Database_Design.md](./docs/03_Database_Design.md) | writing models, migrations, or queries |
| 04 | [docs/04_Backend_API_Specification.md](./docs/04_Backend_API_Specification.md) | building or consuming any endpoint |
| 05 | [docs/05_Frontend_Architecture.md](./docs/05_Frontend_Architecture.md) | building any React feature |
| 06 | [docs/06_Development_Roadmap.md](./docs/06_Development_Roadmap.md) | planning a sprint or picking up work |

---

## Working Protocol

1. **Consult first.** Before proposing or implementing anything, read the relevant doc(s) above. Base your work on them explicitly.
2. **Don't contradict locked invariants** (below) without an explicit new ADR added to [02 §2](./docs/02_Software_Architecture.md).
3. **Docs and code change together.** If work changes a documented decision, update the owning doc in the *same* change. Never leave a doc disagreeing with the code.
4. **Upstream wins.** If two docs conflict, the lower-numbered (upstream) doc is authoritative; fix the downstream one.
5. **Follow the module/feature templates.** Every Django app and every React feature uses the uniform structure defined in [02 §5](./docs/02_Software_Architecture.md) and [05](./docs/05_Frontend_Architecture.md). Consistency is a feature.
6. **Ask when a real decision is genuinely undecided** — don't silently invent scope. Otherwise, follow the docs and act.

---

## Locked Invariants (the load-bearing decisions)

Never violate these without a superseding ADR:

1. **Modular monolith + service layer.** Business logic lives in `services.py`; reads in `selectors.py`. Modules communicate via services/selectors/events — **never by importing another app's models into a view**.
2. **`organization_id` on every operational entity — the tenant boundary nothing bypasses** (ADR-9). `organization` is the tenancy root and billing boundary; `branch_id` is the operational scope inside it. Org Owner reads across their own branches; **no role reads across organizations.** Cross-tenant access returns `404`, never `403`.
3. **Money & stock are append-only ledgers.** `child_ledger_entry` and `stock_movement` are immutable truth; balances/stock are derived. Corrections are counter-entries, never `UPDATE`/`DELETE`.
4. **Debtors is a derived view over the ledger**, not a stored table.
5. **RBAC is data-driven, deny-by-default, enforced on the backend.** The frontend only hides what the backend forbids. **Vendor (platform) staff are a separate access plane** with no implicit tenant data access (ADR-10) — there is no `Super Admin`.
6. **API is a versioned product** under `/api/v1/` with one success envelope and one error format ([02 §13](./docs/02_Software_Architecture.md), [04](./docs/04_Backend_API_Specification.md)).
7. **Frontend is feature-based; TanStack Query owns all server state.** Context holds only small global client state (auth, organization, branch, theme). No Redux.
8. **Integrity is enforced in the database** (FKs, CHECKs, unique/partial indexes, insert-only audit, `ON DELETE RESTRICT` on every path from `organization`) — not just in the app.
9. **Subscription billing is its own domain with an append-only usage ledger** (ADR-11). Every charge traces to an immutable `usage_snapshot`; `subscriptions` and tuition `finance` never share tables. Watch the naming: "plan", "invoice", and "payment" exist in **both** domains ([01 §4.6](./docs/01_Project_Vision.md)).

---

## Tech Stack (quick reference)

**Backend:** Python · Django · Django REST Framework · PostgreSQL · Redis · Celery · JWT · Docker · Nginx · Gunicorn
**Frontend:** React · TypeScript · Vite · Tailwind · Shadcn/UI · TanStack Query · React Hook Form · Zod · React Router · Axios · Recharts · Framer Motion
**Deploy:** Docker · GitHub · Linux server

---

## Coding Standards (pointers)

- Naming, folder structure, and conventions: [02 §5, §24](./docs/02_Software_Architecture.md) (backend), [05](./docs/05_Frontend_Architecture.md) (frontend).
- Database naming, types, and constraints: [03 §2–§5](./docs/03_Database_Design.md).
- API conventions (versioning, pagination, filtering, envelope, errors): [02 §13](./docs/02_Software_Architecture.md) and [04](./docs/04_Backend_API_Specification.md).
- Build order and Definition of Done: [06](./docs/06_Development_Roadmap.md).

### Two checks before every backend PR

1. **Does every new table carry `organization_id NOT NULL`?** The only exceptions are `permission` and `subscription_plan` ([03 §6.2](./docs/03_Database_Design.md)).
2. **Does every new endpoint have a cross-tenant test** proving org A cannot reach org B's row, and that the response is `404` not `403`?

These are not style preferences. A cross-tenant leak of children's records is unrecoverable in a way that a wrong balance is not.

---

## Repository Layout

```
kg-crm/
├── docs/        # single source of truth (00–06)
├── backend/     # Django + DRF (Sprint 0)
├── frontend/    # React + TS + Vite SPA
└── CLAUDE.md
```

Each stack has its own `.gitignore`; the root one covers only OS/editor/`.env`.

---

## Current Phase

**Sprints 0–9 delivered.** Backend and frontend are live against a real API: tenancy foundation, auth/RBAC, children & groups, finance (ledger, invoices, payments, debtors), attendance, staff & payroll, inventory & expenses, notifications & settings, and reports/dashboard/audit with CSV export. 404 backend tests pass, and Celery has now been verified against a live Redis broker.

Next: **Sprint 10 — Subscriptions, Metering & Billing**, then Sprint 11 (Platform Console + Postgres RLS) per [06_Development_Roadmap](./docs/06_Development_Roadmap.md).

> Known gaps, deliberately deferred: no real SMS gateway (console provider behind the adapter); no PDF receipts/payslips — exports are CSV, but they now go through the `FileField` storage abstraction the PDFs were waiting for; the materialized views of [03 §25](./docs/03_Database_Design.md) are not built (aggregates are live ORM queries — reasoning recorded there); and the backup/restore drill plus browser-level E2E have not been run. GitHub Actions returns `startup_failure` on every run — the workflow file is valid; the cause looks account-level (private-repo Actions billing).
