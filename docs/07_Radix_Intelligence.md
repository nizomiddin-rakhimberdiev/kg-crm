# 07 — Radix Intelligence (Radix AI) — V1 Design Specification

**Status:** v3 — reviews 1 and 2 applied (2026-09-17). **Ready for vertical-slice implementation** on founder sign-off · **ADR:** [ADR-14](./02_Software_Architecture.md)

> **Data → Insight → Evidence → Recommendation → Action.**
> Radix AI is not built to show that "there is AI". It is built so the director sees, every morning, the two or three things in the kindergarten that need attention — with the numbers that prove it and a button that takes them there.

---

## 1. Purpose

A CRM stores data and shows reports. Radix Intelligence reads the same data every night, **finds what a director would otherwise miss**, states it as a **fact with evidence**, and attaches **one concrete next action** that deep-links into the existing UI.

What it is **not** (V1):

- Not a chatbot. Not an LLM. No external AI API, no GPU, no model training. Every insight is a deterministic computation over the tenant's own rows.
- Not a prediction engine. V1 states **what has already happened** ("payments are late") — never "will not pay". The language rule is in §7.
- Not a replacement for reports. It is the layer that tells you *which* report to open.

Why deterministic first: there are zero paying customers and therefore zero ground truth. Rules can be explained, tested against the demo dataset, and corrected in one line. A model cannot. And standalone installs ([ADR-13](./02_Software_Architecture.md)) run on the customer's own CPU-only server — the engine must run there unchanged.

---

## 2. V1 scope — exactly three things

| # | Insight | Kind | One-line meaning |
|---|---|---|---|
| I-1 | `payment_delay` | **hard rule** | Invoices past due by more than N days, counted per child |
| I-2 | `attendance_drop` | **pattern** | A group's recent attendance rate fell materially below its own baseline |
| — | **Daily briefing** | shell | The dashboard card that renders open insights + two live checks |

Everything else (expenses, inventory, payroll, revenue trend) is **V2** (§14). Adding a signal is cheap; a false signal is expensive — it costs trust, and trust is the product.

---

## 3. Data sources (all existing, all `organization_id`-scoped)

| Table | Used by | Fields read |
|---|---|---|
| `invoice` | I-1 | `child_id`, `branch_id`, `due_date`, `status`, `amount_due`, `amount_paid`, `period_year/month` |
| `payment` | I-1 (evidence) | `child_id`, `paid_at`, `amount` |
| `child` | I-1 (subject) | `id`, `branch_id`, `group` via active `enrollment` — **no names or phones stored in evidence** (§6) |
| `attendance_record` | I-2 | `group_id`, `branch_id`, `date`, `status` (`present` / `absent` / `excused`) |
| `enrollment` | I-2 | active children per group (denominator) |
| `group` | I-2 | name, `branch_id` |

No new source tables. No materialized views — [03 §25](./03_Database_Design.md) deliberately defers them; the nightly job runs plain selectors and stores its result.

**Source of truth vs. snapshot.** The ledger, invoices and attendance rows are the truth. An insight's `evidence` is a **frozen snapshot** taken at generation time, in the same spirit as `usage_snapshot` (ADR-11). The "Why?" view shows the snapshot; the deep link shows live data. They **may differ** ("24 children were late; 4 have since paid") — this is expected and must be explained in the UI, not hidden.

---

## 4. Trigger rules

Rules are pure functions in `apps/intelligence/rules.py`. They take plain values (no ORM) and return either `None` or an `InsightDraft`. Thresholds live in one place (`apps/intelligence/thresholds.py`) so they can become per-organization settings later without touching the rules.

### I-1 · `payment_delay` (hard rule)

```
for each branch:
  overdue = invoices where status in (issued, partially_paid, overdue)
            and due_date < today - OVERDUE_DAYS
  group by child                          ← subject is the CHILD, see "Why child, not family"
  if count(children) == 0: condition absent
  severity = critical if any(days_overdue >= CRITICAL_DAYS)
             or count(children) >= max(CRITICAL_MIN_SUBJECTS, CRITICAL_SHARE × active_children)
             else warning
```

| Threshold | V1 value | Rationale |
|---|---|---|
| `OVERDUE_DAYS` | **15** | Invoices are due on the 10th ([03 §13](./03_Database_Design.md)); 15 days past due is beyond the informal grace most kindergartens tolerate |
| `CRITICAL_DAYS` | 45 | More than one full billing cycle late |
| `CRITICAL_SHARE` | 10 % of **active children** in the branch | Relative, because a 20-child and a 300-child kindergarten differ. Numerator and denominator are the **same entity** (children) |
| `CRITICAL_MIN_SUBJECTS` | 3 | Floor so a 12-child kindergarten does not go critical on one child |

The rule reads **`due_date`, never `status = overdue`**. `finance.mark_overdue_invoices` runs nightly at 03:00 and normally keeps `status` in sync, but the acceptance dataset (§13.1) shows 7 August invoices still `issued` on a stack where beat is not running — an insight must not depend on another job having run.

**Why child, not family.** There is no `family` entity. `child_guardian` is many-to-many with one `is_primary` per child, and `guardian` is unique by `(branch, phone)` — so siblings *can* share a guardian, but nothing guarantees an operator links them to the same record. Counting "families" would therefore be a guess. V1 counts **children** and says so in every sentence ("24 ta bola bo‘yicha…"). Grouping by primary guardian for display is a V2 refinement, and only as a presentation layer over child-level facts.

### I-2 · `attendance_drop` (pattern)

```
for each group with >= MIN_GROUP_SIZE active children:
  recent   = attendance rate over last RECENT_DAYS working days
  baseline = attendance rate over the BASELINE_DAYS working days before that
  if working days with records in baseline window < MIN_BASELINE_DAYS: skip (learning)
  drop = baseline - recent   (percentage points)
  if drop >= DROP_WARNING: insight
  severity = critical if drop >= DROP_CRITICAL else warning
```

Attendance rate = `present / (present + absent + excused)` on days that have records. Days with no records are **not** counted as absent (the journal may simply not have been filled) — a second live check in the briefing covers that case (§11).

| Threshold | V1 value |
|---|---|
| `RECENT_DAYS` | 7 working days |
| `BASELINE_DAYS` | 30 working days |
| `MIN_BASELINE_DAYS` | 15 working days with records |
| `MIN_GROUP_SIZE` | 5 active children |
| `DROP_WARNING` | 10 percentage points |
| `DROP_CRITICAL` | 20 percentage points |

**Working days** are a single configuration value `WORKING_DAYS = (Mon…Fri)` in `thresholds.py`, used by I-2 *and* by the briefing check (§11). Monday–Friday is the **current default matching `seed_demo` and the attendance UI**, not a product rule: kindergartens with Saturday sessions exist. The constant is the seam where an organization-level setting (`settings_app`) plugs in later without touching the rules.

---

## 5. Baseline and minimum data — two regimes

| Regime | Applies to | Fires when |
|---|---|---|
| **Hard rule** | I-1 | Immediately, whenever the facts exist. A kindergarten live for 12 days with 5 overdue invoices gets the insight on day 12. |
| **Pattern** | I-2 | Only once the baseline window has `MIN_BASELINE_DAYS` of records. Until then the group is silently skipped. |

The dashboard card must say so honestly when *no pattern insight can exist yet*:

> UZ: *Radix davomat naqshlarini o‘rganmoqda — kamida 15 ish kunlik ma’lumot to‘plangach signallar paydo bo‘ladi.*
> RU: *Radix изучает закономерности посещаемости — сигналы появятся после 15 рабочих дней данных.*

This is a per-group condition, so the message appears only when **no** group qualifies.

---

## 6. Evidence ("Why?") — mandatory, structured

An insight without evidence must not be created. `evidence` is a JSON object with a **fixed schema per insight type**, versioned by `evidence_version` so the UI can render old rows after the schema evolves.

### `payment_delay` · evidence v1

```json
{
  "as_of": "2026-09-17",
  "overdue_days_threshold": 15,
  "children_count": 24,
  "active_children": 105,
  "total_overdue": "21758500.00",
  "average_days_overdue": 61,
  "max_days_overdue": 160,
  "children": [
    { "child_id": "…", "group_id": "…", "overdue_amount": "600000.00",  "days_overdue": 160, "invoices": 1 },
    { "child_id": "…", "group_id": "…", "overdue_amount": "1500000.00", "days_overdue": 38,  "invoices": 1 }
  ]
}
```

`children` is capped at 50 rows (ordered by `days_overdue` desc); `children_count` is the true total.

**What the snapshot contains — and what it deliberately does not.** Evidence stores **computed facts** (amounts, days, counts, rates) and **identifiers** (`child_id`, `group_id`). It stores **no names and no phone numbers**. Reasoning:

- The snapshot principle exists to freeze *what triggered the insight* — those are the numbers. A child's name is not a trigger; it is a label, and a label should be current (a corrected spelling must not show the old one for 180 days).
- Data minimization: personal data of children lives in exactly one table under its normal permissions. Copying it into a second, long-lived JSON column would widen the surface for no analytical gain — and this table is also part of every backup and export.
- The "Why?" panel therefore renders **numbers from the snapshot** and **labels from a batched live lookup by id** (one query, same organization, same RLS). A child that no longer exists renders as *"o‘chirilgan bola"* with the snapshot numbers intact. This is the one intentional exception to "evidence-only rendering", and it is documented here so it is not later mistaken for drift.

### `attendance_drop` · evidence v1

```json
{
  "as_of": "2026-09-17",
  "group_id": "…", "active_children": 18,
  "recent": { "days": 7, "rate": 72.4, "present": 91, "absent": 29, "excused": 6 },
  "baseline": { "days": 30, "rate": 86.1 },
  "drop_points": 13.7
}
```

Numbers in the "Why?" panel come **only** from `evidence`; labels (group name, child name) are looked up live by id (see above). What the director sees as *the reason* is exactly what triggered the insight.

---

## 7. Language rule and recommendation

**Facts, not forecasts.** Every title and body describes what the data shows. Banned in V1: *ehtimol / xavf yuqori / to‘lamaydi / вероятно / риск / не заплатит*.

| | ❌ | ✅ |
|---|---|---|
| UZ | Yusupovlar oilasi to‘lamasligi ehtimoli yuqori | 24 ta bola bo‘yicha to‘lov 15 kundan ortiq kechikmoqda |
| RU | Семья Юсуповых, вероятно, не заплатит | По 24 детям оплата задерживается более 15 дней |

Each insight type has exactly **one** recommendation, phrased as a verb the director can act on now:

| Type | UZ | RU |
|---|---|---|
| `payment_delay` | Qarzdorlar ro‘yxatini ko‘rib, eslatma yuborishni ko‘rib chiqing. | Просмотрите список должников и рассмотрите отправку напоминания. |
| `attendance_drop` | Guruh tarbiyachisi bilan pasayish sababini aniqlang. | Уточните причину снижения у воспитателя группы. |

The recommendation is a **content key**, not free text stored per row (§12).

---

## 8. Deep link — every insight lands somewhere real

| Type | Deep link (relative to tenant basename) | Requires |
|---|---|---|
| `payment_delay` | `/debtors?overdue_days=15` | **V1 frontend addition:** `DebtorsPage` reads `overdue_days` from the query string and pre-filters. Today the page has no query params. |
| `attendance_drop` | `/attendance?group=<group_id>&range=7d` | **V1 frontend addition:** `AttendancePage` accepts `group` and `range`. |

The link is stored on the row (`deep_link`) so the mobile card, the briefing and a future notification all agree. It is a *path*, never an absolute URL — the tenant basename (`/t/<slug>` or `/` in standalone) is applied by the router.

---

## 9. Insight lifecycle

### 9.1 Identity: one open row per condition

An insight is identified by its **condition**, not by the day it was computed:

```
condition identity = (organization_id, branch_id, type, subject_type, subject_id)
```

- `payment_delay`: subject is the **branch** (`subject_type = branch`, `subject_id = branch_id` — never `NULL`, see §10) — one row says "in this branch, N children are more than 15 days late".
- `attendance_drop`: subject is the **group** (`subject_type = group`, `subject_id = group_id`).

There is **no `period_key`**. The first draft used the date (I-1) and the ISO week (I-2) as part of the key, which would have produced one row per day for a persisting condition — the exact "same fact five times" this design forbids. Review 1 caught it.

Uniqueness is enforced **only while the insight is open**, with a partial unique index (§10). Closed rows keep their identity but do not block a new one.

### 9.2 State machine

```
            ┌──────────────── user ────────────────┐
            ▼                                       │
  engine ─▶ new ─▶ seen ─▶ resolved                 │
                    │                                │
                    └────▶ dismissed  (suppresses the condition for 7 days)
            ▲                                       │
            │  engine (condition absent) ──▶ auto_resolved
            └───────────── open ────────────────────┘
```

| Status | Open? | Meaning | Set by |
|---|---|---|---|
| `new` | yes | Generated, nobody has opened it | engine |
| `seen` | yes | "Why?" opened at least once | UI, on first expand |
| `resolved` | no | The person says the problem is handled | user, explicit |
| `dismissed` | no | The person saw it and chose not to act **for now** — sets `dismissed_until = now() + 7 days` | user, explicit |
| `auto_resolved` | no | The condition disappeared from the data before anyone acted | engine |

`resolved`, `dismissed` and `auto_resolved` are three **different facts** and are never merged:

- `dismissed / (resolved + dismissed)` — is the rule useful? (> 40 % → review the rule, §13)
- `auto_resolved / all closed` — how often does the situation fix itself before the director reacts?

The dashboard queries `status IN ('new', 'seen')` — and nothing else.

### 9.3 Nightly reconciliation (per condition identity)

| Condition tonight | Open row? | Suppressed?¹ | Action |
|---|---|---|---|
| present | no | no | **create** `new` |
| present | no | **yes** | **nothing** — the director said "not now"; not before the window ends |
| present | yes | — | **refresh** `evidence`, `severity`, `refreshed_at`; `status` unchanged |
| absent | yes | — | **close**: `status = auto_resolved`, `auto_resolved_at = now()` |
| absent | no | **yes** | **end the episode**: set `dismissed_until = now()` on the suppressing row — the condition went away; if it comes back it is news again |
| absent | no | no | nothing |

¹ *Suppressed* = a `dismissed` row exists for this condition identity with `dismissed_until > now()`.

Consequences, spelled out (review 2 asked for exactly these):

- **Day 1** condition → insight → dismissed. **Days 2–7** condition persists → **no new row**. **Day 8+** condition still persists → a **new** row (the director asked for a week, got a week).
- Dismissed on day 1, condition **disappears** on day 3 → the suppression ends that night. Condition **returns** on day 5 → **new row immediately**: a new episode is new information, whatever the calendar says.
- The engine **never reopens** a closed row of any status. History is rows, not state flips.
- `resolved` has **no suppression**. If someone marks a condition resolved and it is still present the next night, a new row is created — the data disagrees with the claim, and the director should know. This is the deliberate asymmetry between "handled" and "not now".

Rows are never deleted by the engine. Retention 180 days via the existing `purge_organization` path only.

## 10. Database schema

Table `insight` — `BranchScopedModel` (so `organization_id` and `branch_id` are inherited, `NOT NULL`, `ON DELETE RESTRICT` from `organization`).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `organization_id`, `branch_id` | FK | inherited |
| `type` | `varchar(40)` | `payment_delay` \| `attendance_drop` |
| `severity` | `varchar(10)` | `warning` \| `critical` |
| `status` | `varchar(14)` | `new` \| `seen` \| `resolved` \| `dismissed` \| `auto_resolved` |
| `subject_type` | `varchar(20)` | `branch` \| `group` |
| `subject_id` | UUID **NOT NULL** | `group_id` for I-2; **`= branch_id`** for branch-level insights (see "Why not NULL") |
| `evidence` | `jsonb` | schema per type, §6 — ids and numbers only |
| `evidence_version` | `smallint` | `1` |
| `recommendation_key` | `varchar(60)` | content key, §12 |
| `deep_link` | `varchar(200)` | path, §8 |
| `generated_at` | timestamptz | first creation |
| `refreshed_at` | timestamptz null | last in-place refresh |
| `seen_at`, `resolved_at`, `dismissed_at`, `auto_resolved_at` | timestamptz null | exactly one of the last three is set on a closed row |
| `dismissed_until` | timestamptz null | suppression window end (§9.3); set with `dismissed_at`; moved to `now()` when the episode ends |
| `acted_by_id` | FK `accounts.User` null | who resolved/dismissed; `NULL` for `auto_resolved` |

**Constraints — verified, not assumed.** The SQL below was generated with Django 5.2.17's schema editor against this project's settings and inspected by hand (2026-09-17):

```sql
CREATE UNIQUE INDEX "uq_insight_open_condition"
  ON "insight" ("branch_id", "type", "subject_type", "subject_id")
  WHERE "status" IN ('new', 'seen');

ALTER TABLE "insight" ADD CONSTRAINT "ck_insight_branch_subject_is_branch"
  CHECK ((("subject_id" = ("branch_id") AND "subject_type" = 'branch') OR "subject_type" = 'group'));
```

plus `CHECK (status IN (...))`, `CHECK (severity IN (...))`, `CHECK` that a closed row has exactly one closing timestamp and an open row has none, `CHECK (dismissed_until IS NULL OR status = 'dismissed')`.

**Why `subject_id` is not NULL.** The first draft used `NULL` for branch-level subjects and proposed `COALESCE` or `NULLS NOT DISTINCT`. Verification found that **`NULLS NOT DISTINCT` requires PostgreSQL 15** — production runs 17, but the developer machines and `scripts/ci-local.sh` run **14**, where Django reports `supports_nulls_distinct_unique_constraints = False` and **silently emits no constraint at all**. Tests would pass locally with no database guarantee. Setting `subject_id = branch_id` for branch-level insights removes NULL from the key entirely; the plain partial unique index works on every Postgres this project runs, and the `CHECK` keeps the convention honest.

Indexes: partial `(organization_id, branch_id, severity) WHERE status IN ('new','seen')` — the dashboard query; `(branch_id, type, generated_at DESC)` — history per condition; `(branch_id, type, subject_type, subject_id, dismissed_until) WHERE status = 'dismissed'` — the suppression lookup.

**Concurrency.** Two generators for the same condition at once (a manual `generate_insights` during the nightly run) race on the unique index; the loser gets `IntegrityError` inside its savepoint and falls back to *refresh* — the same pattern `apps/platform/services_leads.py::create_lead` uses. The constraint is the guarantee; the application only decides what to do when it fires.

**RLS.** `insight` is added to `OPERATIONAL_TABLES` in `apps/core/rls.py`, and the app's first migration applies the policy with `RunPython` exactly as `apps/platform/migrations/0002_lead.py` does. `python manage.py check_rls` must list 39 tables afterwards (38 today). Invariant 8 — non-negotiable.

**Audit.** `resolve`/`dismiss` write to `audit_log` through the existing audit service (`insight.resolve`, `insight.dismiss`). Generation and `auto_resolved` do not (system job; the row is the record).

## 11. Architecture and placement

```
CELERY_BEAT_SCHEDULE["generate-insights"]      03:30 nightly (after mark-overdue 03:00)
        │
        ▼
intelligence.tasks.generate_insights           @reliable_task
        │  platform_context() → list organizations
        │  for org: organization_context(org.id) → for branch:
        ▼
intelligence/selectors.py                      read-only aggregates (ORM), return plain dicts
        ▼
intelligence/rules.py                          pure functions → InsightDraft | None
        ▼
intelligence/services.py                       upsert by dedupe key, refresh/auto-resolve, audit
        ▼
insight table (RLS)
        ▼
GET /api/v1/insights  ·  POST /api/v1/insights/{id}/{seen|resolve|dismiss}
        ▼
Dashboard card "Radix AI" + "Why?" panel        (dashboard.read / dashboard.update)
```

New Django app `apps/intelligence/` following [02 §5](./02_Software_Architecture.md) exactly: `models.py`, `selectors.py`, `services.py`, `rules.py`, `thresholds.py`, `tasks.py`, `views.py`, `serializers.py`, `urls` via `api/v1/router.py` (`router.register("insights", InsightViewSet)`), `tests/`.

- **ViewSet:** `TenantReadOnlyViewSet` + three `@action(detail=True, methods=["post"])` for status changes. Carries `SubscriptionWriteGate` (invariant 11 — `test_write_gate_is_everywhere` enforces it). Permission module: `dashboard` — read for the list, update for status changes. **No new permission codes** in V1.
- **Standalone:** runs identically; the beat schedule is already part of every install.
- **Manual trigger** for demos and tests: `python manage.py generate_insights --slug <org>`.

The **daily briefing** is not stored. It is the dashboard card, rendered from `GET /insights?status=open` plus two **live checks** computed in the same request (cheap, one query each):

| Check | Computation | Renders as |
|---|---|---|
| Attendance completeness today | On a working day (`WORKING_DAYS`): `recorded / expected` where `expected` = children with an active `enrollment` in the branch and `recorded` = those with an `attendance_record` dated today. **Child level is exact** because `attendance_record` carries `UNIQUE (child, attendance_date)` (`uq_attendance_child_date`) and `mark_bulk` writes one row per child via `update_or_create` — one child, one day, one row, guaranteed by the database. | 105/105 → *✓ Bugungi davomat to‘liq kiritilgan* · 98/105 → *⚠ Bugungi davomat 93 % kiritilgan (98/105)* · 0/105 → *⚠ Bugungi davomat hali kiritilmagan* · non-working day or no active enrollment → check hidden |
| Open insights | `count(status IN new, seen)` | *Bugun e’tibor talab qiladigan **3** ta holat bor* / *Bugun e’tibor talab qiladigan holat yo‘q* |

Two earlier drafts of this check were wrong in instructive ways: "any record today → ✓" (green with one group filled) and "groups with a record / groups" (green with one child per group filled). The child-level ratio is the only one the data model actually guarantees.

## 12. Content layer (UZ / RU)

All human-readable text lives in content files, never in Python f-strings:

- Backend: `apps/intelligence/content/{uz,ru}.py` — dicts keyed by `type` and `recommendation_key`, with `{placeholders}` filled from `evidence`. Used only for the notification path (V2) and the management command's console output.
- Frontend: `features/intelligence/content.ts` — same keys, same placeholders, same style as `features/marketing/content.ts`. The dashboard renders from evidence + content; the API returns **keys and evidence, not sentences**, so a wording change never requires regeneration.

Placeholders are typed per insight type (`children_count`, `total_overdue`, `drop_points`…); labels such as `group_name` are resolved live by id (§6). Money is formatted by the existing CRM formatter (`formatUZS`), never by the content layer.

Example, `payment_delay` title:
UZ `{children_count} ta bola bo‘yicha to‘lov {overdue_days_threshold} kundan ortiq kechikmoqda` ·
RU `По {children_count} детям оплата задерживается более {overdue_days_threshold} дней`.

---

## 13. False-positive policy

1. **A rule ships only with a negative test** — a dataset where it must produce nothing. For I-2 that dataset is Bahor bog‘chasi itself (§13.1).
2. **Never absolute thresholds for patterns** — always the subject's own baseline.
3. **Skip, don't guess** — missing data yields no insight, never a "probably" insight.
4. **One row per condition** — refreshed, not repeated (§9). A director must never see the same fact five times.
5. **Dismiss ratio is monitored.** V1 exposes it in the platform console (`platform` app already reads org metadata): `dismissed / (resolved + dismissed)` per type, last 30 days. Above 40 % → the rule is reviewed before any new rule is added.
6. **Wording is downgradeable.** If a threshold turns out noisy, the fix is one constant in `thresholds.py`, not a redeploy of the UI.

### 13.1 Acceptance dataset — Bahor bog‘chasi (`/private`)

105 children, 7 groups, 6 months of ledger and attendance seeded through the real service layer. The numbers below were **measured on the live demo database on 2026-09-17**, not derived from the seed script — the first estimate from reading the script was wrong by a factor of three, which is exactly why the acceptance test must run against data.

| Measured fact | Expected engine behaviour |
|---|---|
| Invoices with `due_date < today − 15` and an open status: **27 invoices across 24 children**; oldest due 2026-04-10 → **160 days**; total outstanding **21 758 500** | I-1 fires **one** insight for the branch: `children_count = 24`, `max_days_overdue = 160`, severity **critical** (160 ≥ 45 *and* 24 ≥ max(3, 10 % × 105 = 11)) |
| Of those, 13 are April–July invoices **partially paid and never topped up** (the seed's "sometimes pays part" behaviour) | They count. A 60 %-paid invoice from April is real debt; the rule must not look only at the last month |
| **7 August invoices still carry `status = issued`** although due 2026-08-10 — the demo stack runs no Celery beat, so `mark_overdue_invoices` never ran | The rule must compute from `due_date`, **never** from `status = overdue`. This dataset proves why (§4). |
| 32 September invoices open, due 2026-09-10 → 7 days | **Excluded** (7 < 15) — asserts the threshold |
| Attendance uniformly ~90 % present in every group, every day | I-2 fires **zero** insights — the negative test |
| Bahor's seed created one guardian per child | `children_count` equals what a "families" count would have shown — the dataset cannot distinguish the two, which is another reason the terminology is *children* (§4) |
| Re-running the job the same day, and again the next day | Row count unchanged; `refreshed_at` advances — asserts condition-level identity (§9.1) |
| Paying all 27 invoices, then re-running | The row becomes `auto_resolved`; the dashboard card no longer shows it — asserts §9.3 |

Unit tests construct the positive I-2 case synthetically (one group's last 7 working days at 60 %, baseline 88 %) and the I-1 boundary (14 / 15 / 16 days).

## 14. Roadmap

| Version | Adds | Precondition |
|---|---|---|
| **V1** | `payment_delay`, `attendance_drop`, daily briefing card, "Why?", deep links, lifecycle, dismiss-ratio metric | — |
| **V2** | `expense_anomaly` (category vs 3-month baseline), `inventory_runout` (consumption rate → days left); insights delivered through the existing `notifications` app (SMS/console provider, opt-in per role) | V1 dismiss ratio < 40 % on ≥ 3 real kindergartens |
| **V3** | Local small LLM (CPU-quantised) that **narrates structured insights only** — it receives the evidence JSON, never the database; output is a monthly briefing paragraph in UZ/RU with every number traceable to evidence | Real customer data; a GPU or an accepted API cost; an Uzbek-quality evaluation set |

Marketing may call all three "Radix AI". The landing page claim for V1 is exactly: *"Radix muhim o‘zgarishlarni sizdan oldin aniqlaydi"* — true on the day V1 ships.

---

## Appendix A — Implementation checklist (for the vertical slice)

1. `apps/intelligence/` app, `insight` model + migration (constraints exactly as §10, RLS `RunPython`), `OPERATIONAL_TABLES` entry, `check_rls` → 39.
2. `thresholds.py` (incl. `WORKING_DAYS`, `DISMISS_SUPPRESSION_DAYS = 7`), `rules.py` (pure) + unit tests incl. boundary values (14/15/16 days; 9.9/10/10.1 points; `CRITICAL_MIN_SUBJECTS` floor).
3. `selectors.py` (I-1 first), `services.py` reconcile (create / refresh / auto-resolve / suppress / end-episode per §9.3), `tasks.py` + beat entry, `generate_insights` command.
4. `InsightViewSet` + serializer + `test_write_gate_is_everywhere` green + cross-tenant `404` test.
5. Frontend: `features/intelligence/` (api, content, `InsightCard`, `WhyPanel` with batched label lookup by id), briefing checks incl. child-level attendance completeness, dashboard placement, `DebtorsPage?overdue_days`.
6. Run against Bahor: assert §13.1. Screenshot the card at 440 px and 1440 px.
7. Docs: [03](./03_Database_Design.md) table list, [04](./04_Backend_API_Specification.md) endpoints, [06](./06_Development_Roadmap.md) sprint entry — in the same change.

## Appendix B — Required tests (names are the contract)

**Rules (pure, no DB)** — `tests/test_rules.py`
- `test_payment_delay_boundary_14_15_16_days`
- `test_payment_delay_severity_critical_by_days` / `_by_share` / `_min_subjects_floor`
- `test_attendance_drop_boundary_9_9_10_0_10_1_points`
- `test_attendance_drop_skips_group_below_min_baseline_days` / `_below_min_group_size`
- `test_attendance_days_without_records_are_not_absent`

**Reconciliation and lifecycle** — `tests/test_services.py`
- `test_same_branch_same_type_cannot_have_two_open_rows` — **asserts `IntegrityError` from the database**, not application logic
- `test_different_branches_each_get_one_open_row`
- `test_rerun_same_day_refreshes_not_duplicates` (row count unchanged, `refreshed_at` advances)
- `test_condition_absent_closes_open_row_as_auto_resolved`
- `test_condition_returns_after_auto_resolved_creates_new_row`
- `test_dismissed_condition_is_suppressed_for_7_days` (days 2–7: no row)
- `test_dismissed_condition_reappears_after_window` (day 8: new row)
- `test_dismissed_then_condition_absent_ends_episode` (`dismissed_until` moved to now)
- `test_dismissed_then_absent_then_present_creates_new_row_inside_window`
- `test_resolved_has_no_suppression`
- `test_engine_never_reopens_closed_rows`
- `test_concurrent_generation_yields_one_row` (two threads, savepoint fallback → refresh)

**Briefing checks** — `tests/test_briefing.py`
- `test_completeness_fully_entered` / `_partially_entered` / `_zero_entered`
- `test_completeness_hidden_on_non_working_day` / `_hidden_without_active_enrollment`

**API** — `tests/test_api.py`
- `test_list_requires_dashboard_read`; `test_status_change_requires_dashboard_update`
- `test_cross_tenant_insight_is_404_not_403`
- `test_seen_is_set_once`; `test_resolve_and_dismiss_write_audit_log`
- `test_write_gate_is_everywhere` stays green (registry includes `insights`)

**Acceptance (Bahor, live data)** — `tests/test_acceptance_bahor.py` (marked `slow`, run via the management command against the demo database)
- every row of §13.1
