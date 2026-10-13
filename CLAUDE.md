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
7. **Look for a skill before starting work in a domain this repo does not already settle.** See *Installed Skills* below.

---

## Installed Skills

Skills live in `.claude/skills/` and are **committed**, so a fresh clone has them. They are installed per project, not globally (`npx skills add <owner/repo@skill> -y`, no `-g`), and `skills-lock.json` records the source and content hash of each one.

| Skill | Use it before… |
|---|---|
| `find-skills` | starting work in a domain neither `docs/` nor an installed skill already covers — it searches and installs from <https://skills.sh/> |
| `ui-ux-pro-max` | any visual or interaction work (it carries its own KG-CRM override header) |
| `ecc` | the reviews and workflows under `.claude/ecc/agents/` and `.claude/ecc/skills/` |

**A skill is input, never an override.** Where a skill disagrees with `docs/` or the invariants above, the project wins — the same rule that is written into `ui-ux-pro-max`'s own header and that was set for `ecc`. A skill that suggests a blue palette, a local `money()` or an ASCII apostrophe is simply wrong *here*, and the guard tests will say so.

**Do not search before routine work.** A search costs a network round trip and returns general advice, while `docs/` already settles this project's money, tenancy, i18n and brand questions more precisely than any general skill can. Search when the task is genuinely outside what this repo has decided — a new tool, an unfamiliar platform, a domain with no entry in `docs/00_INDEX.md`.

**Before installing anything, check it.** Install count (prefer 1 000+), source reputation (`vercel-labs`, `anthropics` and the like), and then **read the `SKILL.md` before following it** — an installed skill is instructions this project will act on, and it arrives from outside this repository.

---

## Locked Invariants (the load-bearing decisions)

Never violate these without a superseding ADR:

1. **Modular monolith + service layer.** Business logic lives in `services.py`; reads in `selectors.py`. Modules communicate via services/selectors/events — **never by importing another app's models into a view**.
2. **`organization_id` on every operational entity — the tenant boundary nothing bypasses** (ADR-9). `organization` is the tenancy root and billing boundary; `branch_id` is the operational scope inside it. Org Owner reads across their own branches; **no role reads across organizations.** Cross-tenant access returns `404`, never `403`.
3. **Money & stock are append-only ledgers.** `child_ledger_entry` and `stock_movement` are immutable truth; balances/stock are derived. Corrections are counter-entries, never `UPDATE`/`DELETE`.
4. **Debtors is a derived view over the ledger**, not a stored table.
5. **RBAC is data-driven, deny-by-default, enforced on the backend.** The frontend only hides what the backend forbids. **Vendor (platform) staff are a separate access plane** with no implicit tenant data access (ADR-10) — there is no `Super Admin`. **Nobody hands out more than they hold** (ADR-25): a non-owner assigns, edits and manages only roles and accounts whose permissions are a subset of their own — never the Owner role, never themselves — and a role's `code` never changes after creation.
6. **API is a versioned product** under `/api/v1/` with one success envelope and one error format ([02 §13](./docs/02_Software_Architecture.md), [04](./docs/04_Backend_API_Specification.md)).
7. **Frontend is feature-based; TanStack Query owns all server state.** Context holds only small global client state (auth, organization, branch, theme). No Redux.
8. **Integrity is enforced in the database** (FKs, CHECKs, unique/partial indexes, insert-only audit, `ON DELETE RESTRICT` on every path from `organization`) — not just in the app.
   **Postgres RLS is the second isolation layer** ([03 §6.3](./docs/03_Database_Design.md)): every tenant table carries a `FORCE`d policy on `organization_id`, and an unset context sees *nothing*. Cross-tenant work must ask for `platform_context()` (or, for login only, `auth_lookup_context()`) by name.
   **Run `python manage.py check_rls` after every `migrate`** — an edited migration does not re-run, so a live database can silently keep the old policies while everything looks fine.
9. **Subscription billing is its own domain with an append-only usage ledger** (ADR-11). Every charge traces to an immutable `usage_snapshot`; `subscriptions` and tuition `finance` never share tables. Watch the naming: "plan", "invoice", and "payment" exist in **both** domains ([01 §4.6](./docs/01_Project_Vision.md)).
10. **Vendor staff live in `platform_user`, never in `accounts.User`** (ADR-10). They see organization *metadata* only; reading operational data needs a time-boxed, reasoned, **customer-visible** `SupportGrant`, and it happens through the normal customer API — there is no privileged second code path. 2FA is a deployment switch — `PLATFORM_2FA_REQUIRED`, **on by default** (ADR-24, superseding ADR-15's off): the console holds the customer list and the support grants, which makes it the one account worth attacking, and **single-use backup codes** removed the lock-out risk that justified leaving it off. Customer-side 2FA is **optional and self-service** (`/auth/2fa/*`, own account only) — never mandatory, because kindergarten staff share and swap phones and a forced code would push a team onto one handset, which is how an audit trail stops answering "who did this". The TOTP algorithm lives in `apps/core/totp.py` for both planes; each plane keeps its secret in its own table.
11. **Non-payment stops writes, never access.** `suspended` returns `402` on writes while reads, `/billing/*`, and export keep working; data is never deleted or hidden ([03 §20.6](./docs/03_Database_Design.md)). Every new viewset carries `SubscriptionWriteGate` — `test_write_gate_is_everywhere` fails the build otherwise.

12. **Money has a location** (ADR-17). `cash_account` names the pots a kindergarten actually holds and **`cash_movement` is the third append-only ledger**, beside `child_ledger_entry` and `stock_movement`. A balance is always `Σ in − Σ out`, never stored; a correction is a counter-movement. Every money event — payment, reversal, expense, payroll payout, advance, transfer — writes its movement **inside the same transaction as the document that caused it**.
13. **Money is tied to a document by an explicit allocation** (ADR-20). `payment_allocation` says which money settled which invoice; `invoice.amount_paid` is a cache over it. The balance formula lives in **one file** — `apps/finance/balance.py` — and every screen reads it, because two formulas drifted apart once and showed the same child two different debts. Allocation is FIFO by due date; whatever stays unallocated **is** the advance. Overpayment is never an error.
14. **Row-level scope is a second layer, and it is inert until someone is made a group's teacher** (ADR-21). Module×action RBAC stays exactly as it is; `children/scope.py` adds "whose children?" on top, derived from `group.teacher → employee ← user`. Never restrict on the absence of a permission alone — a narrow custom role would silently go blind.
15. **Telegram is the primary parent channel; SMS is the paid option behind the same adapter** (ADR-23). The address is a `chat_id` we cannot issue — it exists only once the parent starts the bot, so the invite link **is** the consent record and "not connected" is an ordinary state the screen must show. The invite code embeds the organization because the webhook has no tenant context, and **widening RLS for it was the wrong answer**: operational tables have no platform-mode exit (ADR-10) and that narrowness is the guarantee. Fallback to SMS happens only when that gateway is genuinely connected — never into test mode. Telegram messages are free and are never priced.
16. **A message that was not delivered is never logged as sent** (ADR-22). `test_mode` is its own status, an unusable number is `failed` **with a reason** before any provider call, and a message outside the sending window stays `queued` — nothing is dropped. The window (08:00–21:00), the daily reminder cap (1) and the retry count are **settings**, not constants, and SMS cost is counted per **part** (160 Latin / 70 Cyrillic) with the maths mirrored in `segments.py` and `sms.ts`. A provider that cannot deliver must say so.
17. **A pot never pays out what it does not hold** (ADR-29). An `out` movement larger than the account's balance is refused with the pot, its balance and the shortfall named; `allow_negative=True` records it anyway and every screen turns that into a checkbox the user ticks after reading the warning. Corrections — the counter-movement of a reversal — always pass it, because the original money has already moved. A negative pot never states a fact about a kindergarten; it states that a record is missing, which is why `cash.adjust_balance()` exists: an `opening` or `manual` movement with a **mandatory reason**, so a kindergarten joining mid-year can enter what is already in the safe. **Every money-out document carries its pot** — payment, expense, payroll payout, advance, transfer — because "where did the money go?" has to have an answer.

18. **A fee credit comes from a document, never from the attendance grid** (ADR-19). Only an approved `absence_claim` moves money; reading `attendance_record.status` would let an overslept morning cut the kindergarten's revenue. The day rate is `invoice.amount_due ÷ working days in that month`, and the database — not the service — forbids two claims covering the same day.

---

## Tech Stack (quick reference)

**Backend:** Python · Django · Django REST Framework · PostgreSQL · Redis · Celery · JWT · Docker · Nginx · Gunicorn
**Frontend:** React · TypeScript · Vite · Tailwind · Shadcn/UI · TanStack Query · React Router · Axios · Recharts · Framer Motion
**Deploy:** Docker · GitHub · Linux server

---

## Coding Standards (pointers)

- Naming, folder structure, and conventions: [02 §5, §24](./docs/02_Software_Architecture.md) (backend), [05](./docs/05_Frontend_Architecture.md) (frontend).
- Database naming, types, and constraints: [03 §2–§5](./docs/03_Database_Design.md).
- API conventions (versioning, pagination, filtering, envelope, errors): [02 §13](./docs/02_Software_Architecture.md) and [04](./docs/04_Backend_API_Specification.md).
- Build order and Definition of Done: [06](./docs/06_Development_Roadmap.md).
- **Brand is a token layer, not a per-screen choice ([05 §18](./docs/05_Frontend_Architecture.md)).** Colours, fonts, radius and the logo come from `frontend/tailwind.config.js`, `src/lib/brand.ts` and `src/components/brand/Logo.tsx` — never a literal in a component. The Radix Brendbuk **forbids blue and purple** (every competing CRM is blue), so those Tailwind scales are re-pointed at the brand ramps and `src/__tests__/brand.test.ts` fails the build on a stray `-sky-500` class or `#rrggbb`.
- **Formatting has one home** ([05 §17.1](./docs/05_Frontend_Architecture.md)): `frontend/src/lib/format.ts` owns money, numbers, quantities and dates — never a local `money()` or a bare `Intl.NumberFormat` in a component, and never a native `input[type=date]` (use `components/ui/DateInput`, `dd.mm.yyyy`). Seventeen private copies had already drifted apart once.
- **Uzbek apostrophes are U+02BB (ʻ) and U+02BC (ʼ)**, never ASCII `'` — in `t()` sources, catalog keys, `gettext` and `.po` msgids (Q11). The difference is invisible on screen and makes it a *different string*, so the lookup misses silently. Tests on both stacks fail the build; user data is never rewritten, and SMS goes the other way (`sms_safe`).
- **The refresh token never touches JavaScript** ([04 §5](./docs/04_Backend_API_Specification.md)): it lives in an `httpOnly`, `Secure`, `SameSite=Strict` cookie scoped to `/api/v1/auth`, and the access token lives only in memory. `/auth/refresh` takes an empty body and, when the cookie is used, an `X-CSRFToken` header matching the readable `radix_csrf` cookie. A body token is accepted only as the one-time migration path for old sessions.
- **Accessibility floor** ([05 §17.2](./docs/05_Frontend_Architecture.md)): no text under 12px, `aria-label` on every icon button, a label (not a placeholder) on every field, a visible `:focus-visible` ring. `src/__tests__/a11y.test.ts` guards all four.
- **Three languages (uz/ru/en), ADR-16:** UI text is Uzbek in the source, wrapped in `t('…')` ([05 §17](./docs/05_Frontend_Architecture.md)); backend messages go through `gettext` with `.po` files in `backend/locale/`. Both sides have a catalog-completeness test — add the `ru`/`en` lines it asks for. DRF and Django ship no Uzbek for **their own** messages ("This field may not be blank."), so those live hand-maintained in `backend/vendor_i18n/locale/uz/` — never run `makemessages` for `uz`. The public site has its own content layer (`features/landing/content.ts`, all three locales); the platform console stays Uzbek.

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

> Known gaps, deliberately deferred: SMS is wired (Eskiz adapter) but **off by the owner's decision** — the parent channel is the Telegram bot (ADR-23), and SMS turns on with one `.env` line; no PDF documents — invoice/receipt/payslip PDFs all wait on the same storage abstraction, which is now in place (exports are `.xlsx` through `FileField`; old `.csv` files stay downloadable); the materialized views of [03 §25](./docs/03_Database_Design.md) are not built (aggregates are live ORM queries — reasoning recorded there); browser-level E2E now exists (`frontend/e2e/`, Playwright, five scenarios on desktop and 375px, run with `npm run e2e` against the `/private` demo stand — it writes, so never against a customer's); the backup/restore drill has been run too ( — against the real encrypted production backup, restored into a scratch database while production kept serving, [docs/ops/backup.md §9](./docs/ops/backup.md)). GitHub Actions returns `startup_failure` on **every** run — 66 of 66 since the repo's first day (2026-08-03 → 2026-10-02), not one success. Narrowed on 2026-10-11 and it is **not the workflow file**: both files parse as valid YAML (including the exact revision GitHub ran), all three actions referenced exist and are unarchived, the repo has Actions enabled with `allowed_actions: all`, and the files carry no BOM, CRLF or tabs. No job is ever created and no annotation is written, so it fails before any job starts. **Proved account-level on 2026-10-12, and narrowed to private repositories.** The probe workflow (one `echo`, no services, no matrix) failed the same way, but it shared the directory with the real workflows, so it isolated nothing on its own. The account-wide survey did: across all of this account's repositories, **every public one runs Actions normally** (`pages build and deployment` succeeds; `tripsfactory`'s Deploy reaches its job and fails there, which is an ordinary failure), while **every private one has never started a single run** — `kg-crm` 71/71, `smmumirzoq` and `lor-crm` likewise, three different repositories with three different workflow files. A `workflow_dispatch` on `backend.yml` is accepted by the API, produces a run correctly attributed to `.github/workflows/backend.yml`, and then completes in 0s with zero jobs and **no `Invalid workflow file` annotation** — GitHub never reports a parse problem, because there is none. The block is the account's entitlement to run Actions on **private** repositories. **Root cause found the same day, in Billing → *Budgets and alerts*:** the account carries five budgets — Codespaces, Packages, **Actions**, Git LFS and AI credits — each set to **$0 with "Stop usage: Yes", all sitting at 100 %**. Actions on a private repository is a metered product, so a $0 stop-usage budget halts every run before a job is created; Actions on a public repository is free and therefore untouched, which is exactly the split the survey measured. Billing → *Payment information* explains why the budgets exist: **"Invalid payment method – authorization hold failed"** and no payment method on file. The fix is to delete the **Actions** budget (the page itself states "If no budget is set, usage for that product is unlimited"), which should let GitHub Free's 2 000 included private-repo minutes flow again; a card is only needed for metered overage beyond them, and a local card will usually fail the authorization hold. Deleting that budget and removing the failed billing information did **not** unblock it — a `workflow_dispatch` still died in 0 s afterwards — so the remaining step is GitHub Support, with the public/private split as the evidence. In the meantime the gate is local and real: `scripts/ci-local.sh fast` runs in ~35 s and is installed as the **`pre-push` hook** ([06 §9](./docs/06_Development_Roadmap.md)), so the guard tests do run on every push, with `-m tenancy` added automatically when the target is `main`. `big-update/phase-6-code` was pushed on 2026-10-12 (141 commits) and `main` is still at `11da61a` — the two have not been merged.
