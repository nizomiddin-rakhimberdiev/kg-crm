# 07 — Radix Intelligence (Radix AI) — V1 Design Specification

**Status:** Design — approved for implementation after review · **ADR:** [ADR-14](./02_Software_Architecture.md) · **Date:** 2026-09-17

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
| I-1 | `payment_delay` | **hard rule** | Invoices past due by more than N days, grouped by family |
| I-2 | `attendance_drop` | **pattern** | A group's recent attendance rate fell materially below its own baseline |
| — | **Daily briefing** | shell | The dashboard card that renders open insights + two live checks |

Everything else (expenses, inventory, payroll, revenue trend) is **V2** (§14). Adding a signal is cheap; a false signal is expensive — it costs trust, and trust is the product.

---

## 3. Data sources (all existing, all `organization_id`-scoped)

| Table | Used by | Fields read |
|---|---|---|
| `invoice` | I-1 | `child_id`, `branch_id`, `due_date`, `status`, `amount_due`, `amount_paid`, `period_year/month` |
| `payment` | I-1 (evidence) | `child_id`, `paid_at`, `amount` |
| `child`, `child_guardian`, `guardian` | I-1 (evidence: family) | names, primary guardian phone (**never** stored in evidence — see §7) |
| `attendance_record` | I-2 | `group_id`, `branch_id`, `date`, `status` (`present` / `absent` / `excused`) |
| `enrollment` | I-2 | active children per group (denominator) |
| `group` | I-2 | name, `branch_id` |

No new source tables. No materialized views — [03 §25](./03_Database_Design.md) deliberately defers them; the nightly job runs plain selectors and stores its result.

**Source of truth vs. snapshot.** The ledger, invoices and attendance rows are the truth. An insight's `evidence` is a **frozen snapshot** taken at generation time, in the same spirit as `usage_snapshot` (ADR-11). The "Why?" view shows the snapshot; the deep link shows live data. They **may differ** ("7 families were late; 4 have since paid") — this is expected and must be explained in the UI, not hidden.

---

## 4. Trigger rules

Rules are pure functions in `apps/intelligence/rules.py`. They take plain values (no ORM) and return either `None` or an `InsightDraft`. Thresholds live in one place (`apps/intelligence/thresholds.py`) so they can become per-organization settings later without touching the rules.

### I-1 · `payment_delay` (hard rule)

```
for each branch:
  overdue = invoices where status in (issued, partially_paid, overdue)
            and due_date < today - OVERDUE_DAYS
  group by child
  if count(children) == 0: no insight
  severity = critical if any(days_overdue >= CRITICAL_DAYS) or families >= CRITICAL_FAMILIES
             else warning
```

| Threshold | V1 value | Rationale |
|---|---|---|
| `OVERDUE_DAYS` | **15** | Invoices are due on the 10th ([03 §13](./03_Database_Design.md)); 15 days past due is beyond the informal grace most kindergartens tolerate |
| `CRITICAL_DAYS` | 45 | More than one full billing cycle late |
| `CRITICAL_FAMILIES` | 10 % of active children (min 3) | Relative, because a 20-child and a 300-child kindergarten differ |

Note that `finance.mark_overdue_invoices` already runs nightly at 03:00 and sets `status = overdue`; I-1 does **not** depend on it (it recomputes from `due_date`) but runs after it so the two never disagree.

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

Working days: Monday–Friday, matching `seed_demo` and the attendance UI.

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
  "families_count": 24,
  "total_overdue": "21758500.00",
  "average_days_overdue": 61,
  "max_days_overdue": 160,
  "families": [
    { "child_id": "…", "child_name": "Sobirov Zarina", "group_name": "Kamalak",
      "overdue_amount": "600000.00", "days_overdue": 160, "invoices": 1 },
    { "child_id": "…", "child_name": "Yusupov Shohruh", "group_name": "Yulduzcha",
      "overdue_amount": "1500000.00", "days_overdue": 38, "invoices": 1 }
  ]
}
```

`families` is capped at 50 rows (ordered by `days_overdue` desc); `families_count` is the true total. **No phone numbers, no guardian names** in evidence — the deep link leads to the child card where that data lives under its normal permissions.

### `attendance_drop` · evidence v1

```json
{
  "as_of": "2026-09-17",
  "group_id": "…", "group_name": "Kamalak", "active_children": 18,
  "recent": { "days": 7, "rate": 72.4, "present": 91, "absent": 29, "excused": 6 },
  "baseline": { "days": 30, "rate": 86.1 },
  "drop_points": 13.7
}
```

The "Why?" panel renders **only** from `evidence` — never from a live query — so what the director sees is exactly what triggered the insight.

---

## 7. Language rule and recommendation

**Facts, not forecasts.** Every title and body describes what the data shows. Banned in V1: *ehtimol / xavf yuqori / to‘lamaydi / вероятно / риск / не заплатит*.

| | ❌ | ✅ |
|---|---|---|
| UZ | Yusupovlar oilasi to‘lamasligi ehtimoli yuqori | 9 ta oilada to‘lov 15 kundan ortiq kechikmoqda |
| RU | Семья Юсуповых, вероятно, не заплатит | В 9 семьях оплата задерживается более 15 дней |

Each insight type has exactly **one** recommendation, phrased as a verb the director can act on now:

| Type | UZ | RU |
|---|---|---|
| `payment_delay` | Qarzdor oilalarga eslatma yuborishni ko‘rib chiqing. | Рассмотрите отправку напоминания должникам. |
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

```
new ──▶ seen ──▶ resolved
  │                 
  └────▶ dismissed
```

| Status | Meaning | Set by |
|---|---|---|
| `new` | Generated tonight, nobody has opened it | engine |
| `seen` | Opened the "Why?" panel or the card | UI, automatically on first expand |
| `resolved` | "The problem is handled" | user, explicit button |
| `dismissed` | "I saw it, I am not acting on it" | user, explicit button |

`resolved` and `dismissed` are **different facts** and are never merged. Their ratio is the first quality metric of Radix AI: a rule whose insights are mostly dismissed is a bad rule.

**Re-generation.** The nightly job never duplicates: an insight is identified by `(organization_id, branch_id, type, subject_type, subject_id, period_key)`. If an open row exists for that key, its `evidence` and `severity` are **refreshed in place** and `refreshed_at` is set; `status` is untouched. If the condition no longer holds, the open row is set to `auto_resolved_at = now()` (status stays as the user left it — we do not silently close what a person opened). `period_key` is the date for I-1 and `group_id + ISO week` for I-2, so a persisting condition is one row that ages, not thirty rows.

Rows are **append-only in intent**: never deleted by the engine; `updated_at` records refreshes. Retention: 180 days, purged by the existing `purge_organization` path only.

---

## 10. Database schema

Table `insight` — `BranchScopedModel` (so `organization_id` and `branch_id` are inherited, `NOT NULL`, `ON DELETE RESTRICT` from `organization`).

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `organization_id`, `branch_id` | FK | inherited |
| `type` | `varchar(40)` | `payment_delay` \| `attendance_drop` |
| `severity` | `varchar(10)` | `warning` \| `critical` |
| `status` | `varchar(12)` | `new` \| `seen` \| `resolved` \| `dismissed` |
| `subject_type` | `varchar(20)` | `branch` (I-1) \| `group` (I-2) |
| `subject_id` | UUID null | `group_id` for I-2; null for branch-level |
| `period_key` | `varchar(20)` | dedupe key part (§9) |
| `evidence` | `jsonb` | schema per type, §6 |
| `evidence_version` | `smallint` | `1` |
| `recommendation_key` | `varchar(60)` | content key, §12 |
| `deep_link` | `varchar(200)` | path, §8 |
| `generated_at` | timestamptz | first creation |
| `refreshed_at` | timestamptz null | last in-place refresh |
| `seen_at`, `resolved_at`, `dismissed_at`, `auto_resolved_at` | timestamptz null | |
| `acted_by_id` | FK `accounts.User` null | who resolved/dismissed |

Constraints and indexes:

- `UNIQUE (branch_id, type, subject_type, subject_id, period_key)` — dedupe.
- `CHECK (status IN (...))`, `CHECK (severity IN (...))`.
- Partial index `(organization_id, status) WHERE status IN ('new','seen')` — the dashboard query.
- Index `(branch_id, generated_at DESC)`.

**RLS.** `insight` is added to `OPERATIONAL_TABLES` in `apps/core/rls.py`, and the app's first migration applies the policy with `RunPython` exactly as `apps/platform/migrations/0002_lead.py` does. `python manage.py check_rls` must list 39 tables afterwards (38 today). This is invariant 8 — non-negotiable.

**Audit.** `resolve`/`dismiss` write to `audit_log` through the existing audit service (`insight.resolve`, `insight.dismiss`). Generation does not (it is a system job; the row itself is the record).

---

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

| Check | UZ | Condition |
|---|---|---|
| Attendance entered today | ✓ Bugungi davomat kiritilgan / ⚠ Bugungi davomat hali kiritilmagan | any `attendance_record` with `date = today` for the branch (working days only) |
| Open insights count | Bugun e’tibor talab qiladigan **3** ta holat bor | `count(status in new, seen)` |

---

## 12. Content layer (UZ / RU)

All human-readable text lives in content files, never in Python f-strings:

- Backend: `apps/intelligence/content/{uz,ru}.py` — dicts keyed by `type` and `recommendation_key`, with `{placeholders}` filled from `evidence`. Used only for the notification path (V2) and the management command's console output.
- Frontend: `features/intelligence/content.ts` — same keys, same placeholders, same style as `features/marketing/content.ts`. The dashboard renders from evidence + content; the API returns **keys and evidence, not sentences**, so a wording change never requires regeneration.

Placeholders are typed per insight type (`families_count`, `total_overdue`, `group_name`, `drop_points`…). Money is formatted by the existing CRM formatter (`formatUZS`), never by the content layer.

Example, `payment_delay` title:
UZ `{families_count} ta oilada to‘lov {overdue_days_threshold} kundan ortiq kechikmoqda` ·
RU `В {families_count} семьях оплата задерживается более {overdue_days_threshold} дней`.

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
| Invoices with `due_date < today − 15` and an open status: **27 invoices across 24 families**; oldest due 2026-04-10 → **160 days**; total outstanding **21 758 500** | I-1 fires **one** insight per branch: `families_count = 24`, `max_days_overdue = 160`, severity **critical** (160 ≥ 45 *and* 24 ≥ 11 = 10 % of 105) |
| Of those, 13 are April–July invoices **partially paid and never topped up** (the seed's "sometimes pays part" behaviour) | They count. A 60 %-paid invoice from April is real debt; the rule must not look only at the last month |
| **7 August invoices still carry `status = issued`** although due 2026-08-10 — the demo stack runs no Celery beat, so `mark_overdue_invoices` never ran | The rule must compute from `due_date`, **never** from `status = overdue`. This dataset proves why (§4). |
| 32 September invoices open, due 2026-09-10 → 7 days | **Excluded** (7 < 15) — asserts the threshold |
| Attendance uniformly ~90 % present in every group, every day | I-2 fires **zero** insights — the negative test |
| Re-running the job the same day | Row count unchanged; `refreshed_at` set — asserts dedupe |

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

1. `apps/intelligence/` app, `insight` model + migration (RLS `RunPython`), `OPERATIONAL_TABLES` entry, `check_rls` → 39.
2. `thresholds.py`, `rules.py` (pure) + unit tests incl. boundary values (14/15/16 days; 9.9/10/10.1 points).
3. `selectors.py` (I-1 first), `services.py` upsert, `tasks.py` + beat entry, `generate_insights` command.
4. `InsightViewSet` + serializer + `test_write_gate_is_everywhere` green + cross-tenant `404` test.
5. Frontend: `features/intelligence/` (api, content, `InsightCard`, `WhyPanel`), dashboard placement, `DebtorsPage?overdue_days`.
6. Run against Bahor: assert §13.1. Screenshot the card at 440 px and 1440 px.
7. Docs: [03](./03_Database_Design.md) table list, [04](./04_Backend_API_Specification.md) endpoints, [06](./06_Development_Roadmap.md) sprint entry — in the same change.
