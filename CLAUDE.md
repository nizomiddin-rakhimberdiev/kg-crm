# CLAUDE.md — Operating Protocol for KG-CRM

This file is loaded automatically every session. It tells Claude (and any developer) **how to work on this project so context is never lost and decisions never contradict each other.**

---

## What this project is

**Kindergarten Management System (KG-CRM)** — an enterprise SaaS platform combining **CRM + ERP + LMS** for kindergartens. MVP is a staff-facing back-office; the architecture is designed to grow into parent/teacher portals, online payments, and multi-branch without rewrites.

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
2. **`branch_id` on every operational entity.** All queries are branch-scoped; Super Admin is the only cross-branch role.
3. **Money & stock are append-only ledgers.** `child_ledger_entry` and `stock_movement` are immutable truth; balances/stock are derived. Corrections are counter-entries, never `UPDATE`/`DELETE`.
4. **Debtors is a derived view over the ledger**, not a stored table.
5. **RBAC is data-driven, deny-by-default, enforced on the backend.** The frontend only hides what the backend forbids.
6. **API is a versioned product** under `/api/v1/` with one success envelope and one error format ([02 §13](./docs/02_Software_Architecture.md), [04](./docs/04_Backend_API_Specification.md)).
7. **Frontend is feature-based; TanStack Query owns all server state.** Context holds only small global client state (auth, branch, theme). No Redux.
8. **Integrity is enforced in the database** (FKs, CHECKs, unique/partial indexes, insert-only audit) — not just in the app.

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

---

## Current Phase

**Pre-development — architecture & design complete (docs 01–06).** No application code exists yet. Next step is Sprint 0 (project scaffolding) per [06_Development_Roadmap](./docs/06_Development_Roadmap.md).
