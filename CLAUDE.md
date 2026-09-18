# CLAUDE.md — Operating Protocol for KG-CRM

This file is loaded automatically every session. It tells Claude (and any developer) **how to work on this project so context is never lost and decisions never contradict each other.**

---

## What this project is

**Kindergarten Management System (KG-CRM)** — a **hosted multi-tenant SaaS** platform combining **CRM + ERP + LMS** for kindergartens. MVP is a staff-facing back-office; the architecture is designed to grow into parent/teacher portals and online payments without rewrites.

**Commercial model** ([01 §4](./docs/01_Project_Vision.md)): each customer is an **organization** with unlimited branches under **one subscription**, priced per enrolled child — base **400 000 UZS/month including 50 children, +50 000 per additional 10** (revised 2026-09-16, ADR-12 — supersedes the original 500 000 / +80 000 launch figures, which stay correct only for invoices billed before 2026-09-14). Payment terms: monthly (0 %), semi-annual (−15 %), annual (−25 %). 15-day risk-free trial; on conversion the first paid month is dated from the trial start, disclosed at signup.

**Two delivery models, one codebase** ([01 §4.7](./docs/01_Project_Vision.md), ADR-13): the hosted subscription above, **or** a one-off **standalone licence** deployed on the customer's own server. `DEPLOYMENT_MODE=standalone` switches off the commercial machinery — no subscription, no trial, no write gate, no billing screens, no vendor console, and the app sits at the install root instead of `/t/<slug>`. **Never fork the repo to build a single-tenant variant**; the flag exists so one fix reaches both. The flag is a commercial boundary only — tenant isolation (invariants 2 and 8) is identical in both modes.

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
| 07 | [docs/07_Radix_Intelligence.md](./docs/07_Radix_Intelligence.md) | touching insights, the nightly engine, or any "Radix AI" claim (ADR-14: deterministic rules + evidence, no LLM in V1) |

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
   **Postgres RLS is the second isolation layer** ([03 §6.3](./docs/03_Database_Design.md)): every tenant table carries a `FORCE`d policy on `organization_id`, and an unset context sees *nothing*. Cross-tenant work must ask for `platform_context()` (or, for login only, `auth_lookup_context()`) by name.
   **Run `python manage.py check_rls` after every `migrate`** — an edited migration does not re-run, so a live database can silently keep the old policies while everything looks fine.
9. **Subscription billing is its own domain with an append-only usage ledger** (ADR-11). Every charge traces to an immutable `usage_snapshot`; `subscriptions` and tuition `finance` never share tables. Watch the naming: "plan", "invoice", and "payment" exist in **both** domains ([01 §4.6](./docs/01_Project_Vision.md)).
10. **Vendor staff live in `platform_user`, never in `accounts.User`** (ADR-10). They see organization *metadata* only; reading operational data needs a time-boxed, reasoned, **customer-visible** `SupportGrant`, and it happens through the normal customer API — there is no privileged second code path. 2FA is mandatory.
11. **Non-payment stops writes, never access.** `suspended` returns `402` on writes while reads, `/billing/*`, and export keep working; data is never deleted or hidden ([03 §20.6](./docs/03_Database_Design.md)). Every new viewset carries `SubscriptionWriteGate` — `test_write_gate_is_everywhere` fails the build otherwise.

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

**Sprints 0–12 delivered — the MVP is feature-complete, plus Radix Intelligence V1 (`payment_delay` end-to-end, [06 Sprint 12](./docs/06_Development_Roadmap.md)).** Backend and frontend are live against a real API: tenancy foundation, auth/RBAC, children & groups, finance (ledger, invoices, payments, debtors), attendance, staff & payroll, inventory & expenses, notifications & settings, reports/dashboard/audit with CSV export, **subscriptions/metering/billing**, and the **platform console + Postgres RLS**. 738 backend tests pass; Celery beat is verified live (the nightly `generate_insights` run refreshed a real row).

Next: the **launch gate** — data-residency/hosting jurisdiction must be confirmed before the first paying customer ([01 §10](./docs/01_Project_Vision.md)). That blocks launch, not the code.

> Known gaps, deliberately deferred: no real SMS gateway (console provider behind the adapter); no PDF documents — invoice/receipt/payslip PDFs all wait on the same storage abstraction, which is now in place (exports are CSV through `FileField`); the materialized views of [03 §25](./docs/03_Database_Design.md) are not built (aggregates are live ORM queries — reasoning recorded there); and the backup/restore drill plus browser-level E2E have not been run. GitHub Actions returns `startup_failure` on every run — the workflow file is valid; the cause looks account-level (private-repo Actions billing).
