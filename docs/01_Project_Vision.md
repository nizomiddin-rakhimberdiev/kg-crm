# 01 — Project Vision & Requirements

| | |
|---|---|
| **Project** | Kindergarten Management System (KG-CRM) |
| **Document** | Project Vision, Scope & Requirements v1.0 |
| **Status** | Baseline — governs all downstream design |
| **Audience** | Product, Backend, Frontend, QA, Stakeholders |
| **Related** | [00_INDEX](./00_INDEX.md) · [02_Software_Architecture](./02_Software_Architecture.md) · [03_Database_Design](./03_Database_Design.md) · [04_Backend_API_Specification](./04_Backend_API_Specification.md) · [05_Frontend_Architecture](./05_Frontend_Architecture.md) · [06_Development_Roadmap](./06_Development_Roadmap.md) |

> This is the **"why" and "what"** of the system. Every architectural and technical decision downstream must trace back to a requirement here. When a requirement changes, this document changes first, then the affected design docs.

---

## 1. Vision Statement

> **A single platform that lets a kindergarten run its entire operation — enrollments, money, staff, kitchen, and communication — from one place, replacing paper ledgers, spreadsheets, and disconnected chat apps.**

The system unifies three enterprise domains:

- **CRM** — the relationship side: children, guardians, enrollment, communication.
- **ERP** — the operations side: payments, debts, payroll, expenses, kitchen & warehouse.
- **LMS** — the future learning side: homework, meal planning, teacher & parent portals.

We deliver an **administrative back-office MVP** first (staff-facing), then grow into parent/teacher-facing capabilities **without re-architecting** (see [06_Development_Roadmap](./06_Development_Roadmap.md)).

The product is delivered as a **hosted multi-tenant SaaS** sold on a per-child subscription — see [§4](#4-business-model--multi-tenant-saas). Every kindergarten (organization) is a tenant on shared infrastructure operated by the vendor.

---

## 2. Problem Statement

Kindergartens today typically operate with:

| Pain point | Current reality | Cost |
|-----------|-----------------|------|
| Fragmented data | Paper registers, Excel files, phone notes | Lost/duplicated records, no single truth |
| Manual billing | Hand-calculated monthly fees | Errors, missed debts, revenue leakage |
| Debt tracking | "Who owes what?" answered from memory | Uncollected payments, disputes |
| Payroll | Manual salary math | Slow, error-prone, no history |
| Inventory | No kitchen/warehouse tracking | Waste, stock-outs, no cost visibility |
| Communication | Ad-hoc calls / group chats | Missed reminders, no delivery record |
| Reporting | Assembled by hand each month | No real-time visibility for the director |

**The system's job** is to make each of these a fast, accurate, auditable, single-source operation.

---

## 3. Goals & Non-Goals

### 3.1 Goals (MVP)
1. One system of record for **children & guardians**.
2. Accurate **monthly billing**, **payment intake**, and **automatic debtor tracking**.
3. Daily **attendance** with history.
4. **Payroll** for staff with per-period runs and payslips.
5. **Kitchen & warehouse** stock tracking (in/out, low-stock alerts).
6. **Expense** tracking with approval and P&L visibility.
7. **Dashboard** and **reports** giving the director real-time operational and financial visibility.
8. **SMS notifications** (payment receipts, debt reminders).
9. **Role-based access** so each staff member sees only what they should.
10. Full **audit trail** for money and administrative actions.
11. **Multi-tenant isolation** — an organization can never read or write another organization's data.
12. **Subscription lifecycle & billing** — trial, conversion, per-child metering, invoicing, suspension (§4).
13. **Self-service onboarding** — an organization can sign up, import its children from Excel/CSV, and be operational inside the trial window without vendor intervention.

> **Goal 13 is not a convenience feature.** A kindergarten only feels value after 50–200 children are in the system. If data entry consumes the trial, the trial fails regardless of product quality. Bulk import is therefore MVP-critical.

### 3.2 Non-Goals (explicitly out of MVP scope)
- Parent-facing or teacher-facing portals (designed for, not built yet).
- Online/card payment gateway for **tuition** (parent payments stay cash/transfer at MVP; subscription payments are a separate flow — §4).
- Medical records, meal planning, homework/LMS features.
- Native mobile app.
- Vendor-side analytics/CRM for managing the customer pipeline (spreadsheet is acceptable at MVP scale).
- Automated recurring card debit for subscriptions — MVP issues invoices; payment is manual (§4.3).

> Multi-branch is **in scope**, not deferred: one subscription covers unlimited branches (§4.1), so the branch selector and cross-branch views ship with the MVP.

> Non-goals are **designed for** at the architecture/data layer (see [02](./02_Software_Architecture.md) §22, [03](./03_Database_Design.md) §6) so they become additive later, never a rewrite.

---

## 4. Business Model — Multi-Tenant SaaS

KG-CRM is **not** delivered as an on-premise install per kindergarten. It is a **single hosted multi-tenant SaaS product**: the vendor operates and pays for all infrastructure, and customers pay a recurring subscription for access.

This is a *product* decision with hard architectural consequences, recorded as **ADR-9/10/11** in [02 §2](./02_Software_Architecture.md).

### 4.1 The tenancy hierarchy

```
Organization  ← the CUSTOMER; the subscription and all billing attach here
  └── Branch  ← a physical kindergarten location
       └── children, invoices, payments, staff, stock, …
```

- **Organization** is the tenancy root and the **billing boundary**. Data must never cross an organization boundary — for any role, including the customer's own owner.
- **Branch** remains the *operational* boundary inside an organization (reporting, staff scope, invoice numbering).
- **One subscription covers unlimited branches.** A customer running five locations manages all of them from one dashboard under one subscription, and pays only for children.

### 4.2 Pricing

Billing is **per enrolled child**, with a base package that acts as a revenue floor.

| Element | Value |
|---------|-------|
| Base package | **400 000 UZS / month**, includes up to **50 children** |
| Minimum billable children | **50** — an organization with fewer children still pays the base |
| Overage | **+50 000 UZS per each additional 10 children** (step, not per-child) |
| Currency | UZS |

Worked examples: 50 children → 400 000 · 80 children → 550 000 · 150 children → 900 000 · 300 children → 1 650 000.

**Why a 10-child step instead of per-child:** customers are legal entities paying by bank transfer against an invoice (schyot-faktura). A bill that changes by a few thousand UZS every month creates accounting friction and disputes. The step keeps the invoice stable until the count crosses a boundary, while preserving the revenue floor.

**Built-in volume discount:** effective per-child price falls from 8 000 (at 50) to ~5 500 (at 300) with no separate enterprise tier.

> **Revised 2026-09-16 (ADR-12, [02 §2](./02_Software_Architecture.md)).** The original figures were 500 000 / +80 000; they are preserved in the `SubscriptionPlan` row that closed on 2026-09-13 and remain the correct historical reference for anything billed before the change. Do not restate the old numbers as current.

### 4.3 Payment terms

| Term | Payments per year | Discount |
|------|:-----------------:|:--------:|
| Monthly | 12 | — |
| Semi-annual | 2 | **15 %** |
| Annual | 1 | **25 %** |

- The discount applies to the **base package**. Prepayment covers the base at the child count committed at purchase.
- **Growth is billed as it happens:** if the child count rises above the prepaid tier mid-term, the overage steps are invoiced monthly from the month they occur, at the same discount rate.
- If the child count falls, the overage stops; the base is never refunded (it is the floor).

### 4.4 Trial

**15-day risk-free trial** — no card, no upfront payment.

- **Two ways to open an account.** Vendor staff create the organization from the platform console ([04 §19](./04_Backend_API_Specification.md)) — the sales-led path, 15-day trial. **Since PLAN 6.7 (ADR-28) a kindergarten can also sign up itself** — the same **15-day** trial (owner's decision, 2026-10-03) — but the tenant is created only after the e-mailed link is opened and a password set; an unconfirmed request leaves no tenant and is removed after 7 days, and one e-mail gets one self-signup trial.
- **The trial clock starts when the account is created**, so an account should be opened when the customer is ready to begin — not weeks earlier.
- If the customer converts, the **first monthly payment is dated from the trial start**, i.e. the paid month absorbs the trial period. This is disclosed **in the offer**, never at the end of the trial.
- If the customer declines, they pay **nothing**.
- Marketing must never describe the trial as "100 % free". The accurate claim is *"15-day trial — pay nothing if it isn't for you."*
- Because customers are legal entities, a bank transfer takes days to clear. A converting organization enters a **`pending_payment` grace state with full access** (7 days) once the invoice is issued — access is never cut off mid-transfer.
- A declining organization keeps **read-only access + data export for 30 days**, then the data is purged. For self-signup trials that never paid, this is `purge_unconverted_trials` (dry run by default; the owner runs it with `--apply`). Vendor-opened and paying organizations are never touched by it.

### 4.5 What is never metered

**Branches and staff user accounts are unlimited.** Charging per user is not merely unattractive — it causes staff to share one login, which destroys the audit trail that money handling depends on (P7). Unlimited users is therefore a **data-integrity requirement**, not a sales concession.

### 4.6 Two billing domains that must never be confused

| Domain | Who bills whom | Module | Documents |
|--------|----------------|--------|-----------|
| **Tuition** | Kindergarten → parent/guardian | `finance` | `tariff_plan`, `invoice`, `payment`, `child_ledger_entry` |
| **Subscription** | Vendor (platform) → kindergarten | `subscriptions` | `subscription_plan`, `subscription_invoice`, `subscription_payment`, `usage_snapshot` |

These share vocabulary ("plan", "invoice", "payment") but are **separate domains with separate tables and separate ledgers**. Naming must always be explicit; `subscriptions` never writes to `finance` tables and vice versa.

### 4.7 Two delivery models (added 2026-09-17 — ADR-13)

The same product is sold two ways. The buyer chooses how it is hosted, not which features they get.

| | **Hosted subscription** | **Standalone licence** |
|---|---|---|
| Where it runs | Vendor infrastructure, `radix-crm.uz` | The **customer's own server** |
| Payment | Monthly, per enrolled child (§4.2) | **One-off, larger** — no recurring fee |
| Trial | 15 days (§4.4) | None — the install is already paid for |
| Subscription / billing screens | Yes | **Absent** (no plan, no invoice, no write gate) |
| Vendor console & support grants | Yes (ADR-10) | Absent — there is no vendor plane on the customer's server |
| Address | `radix-crm.uz/t/<slug>` | The customer's own domain, at its root |
| Upgrades & fixes | Continuous, vendor-managed | Delivered by redeploying the same repo on their server |

**One codebase serves both** (`DEPLOYMENT_MODE`, ADR-13). This is deliberate: a separate single-tenant fork would double the maintenance surface for a solo-founder team and drift apart within weeks. The standalone build is not a reduced product — it is the same system with the commercial machinery (subscription, trial, metering, vendor console) switched off, because the customer has already bought it outright.

> **Isolation does not change between modes.** `organization_id` scoping and RLS are identical in both ([02 §6](./02_Software_Architecture.md), CLAUDE.md invariants 2 and 8). The flag decides what is *sold*, never what is *protected*.

---

## 5. Target Users (Personas & Roles)

The MVP is **staff-facing**. Five customer roles, plus the vendor, on **two separate access planes** ([02 §11](./02_Software_Architecture.md)):

**Organization plane** — the customer's own staff:

| Role | Persona | Primary jobs |
|------|---------|--------------|
| **Org Owner** | Kindergarten owner / director of a group of branches | Manage users, roles, settings, **billing & subscription**; full access across **their own** branches |
| **Director** | Kindergarten head | Full operational & financial oversight of the branch; reports |
| **Manager** | Operations manager | Children, attendance oversight, kitchen/warehouse, expenses |
| **Cashier** | Front-desk / accountant | Payments, invoices, debtor follow-up |
| **Attendance Manager** | Teacher/monitor | Records and manages daily attendance |

**Platform plane** — the vendor (us):

| Role | Persona | Primary jobs |
|------|---------|--------------|
| **Platform Admin** | SaaS operator | Organizations, trials, subscription status, invoices, suspension — **metadata only**, never a customer's children or payments |

> **There is no role that can read across organizations' operational data.** The old "Super Admin" — a role defined as bypassing all scoping — was removed for exactly this reason (ADR-10). Vendor support access to a tenant requires an explicit, time-boxed grant that the customer can see in their own audit log.

**Future personas** (roadmap): Parent, Teacher — they slot into the same data-driven RBAC without code changes, scoped to one organization like every other user.

---

## 6. Scope — Modules

### 6.1 MVP Modules (15)

Modules 1–12 are **customer-facing** (used by kindergarten staff). Modules 13–15 exist because the product is sold as SaaS (§4).

| # | Module | Purpose | Backed by (Django app) |
|---|--------|---------|------------------------|
| 1 | **Dashboard** | Real-time KPIs and overview | `reports` (aggregation view) |
| 2 | **Children** | Child & guardian profiles, groups, enrollment | `children` |
| 3 | **Payments** | Invoices, payment intake, receipts | `finance` |
| 4 | **Debtors** | Who owes money and how much | `finance` (derived view) |
| 5 | **Attendance** | Daily present/absent tracking | `attendance` |
| 6 | **Payroll** | Staff salaries, payroll runs, payslips | `payroll` (+ `hr`) |
| 7 | **Kitchen & Warehouse** | Products, stock in/out, suppliers | `inventory` |
| 8 | **Expenses** | Operational spend with approval | `expenses` |
| 9 | **Reports** | Financial & operational reports, exports | `reports` |
| 10 | **Notifications** | SMS dispatch, templates, delivery log | `notifications` |
| 11 | **Settings** | System configuration, feature flags | `settings_app` |
| 12 | **Users & Roles** | User & role/permission management | `accounts` |
| 13 | **Branches** | Create/manage branches, switch between them, cross-branch views | `branches` |
| 14 | **Billing & Subscription** *(customer view)* | Current plan, billable child count, projected bill, invoices, payment term | `subscriptions` |
| 15 | **Platform Console** *(vendor-only)* | Organizations, trials, subscription status, usage snapshots, suspension | `platform` |

> **Module 14 is a retention feature, not a receipt viewer.** A customer must be able to see their current child count and projected charge *before* the invoice arrives. Surprise invoices are the leading cause of SaaS churn.

### 6.2 Future Modules (roadmap — architecture already supports)

Parent Portal · Teacher Portal · Online Payments · Medical Records · Meal Planning · Homework/LMS · Gallery · AI Assistant · Mobile App · Advanced Analytics · Automated card debit for subscriptions.

Mapping of *how each plugs in* is in [02_Software_Architecture](./02_Software_Architecture.md) §22.

---

## 7. Functional Requirements (high level, per module)

> Detailed API contracts are in [04_Backend_API_Specification](./04_Backend_API_Specification.md). This section states **what** each module must do.

| Module | Key capabilities (MVP) |
|--------|------------------------|
| **Dashboard** | Active children count, month revenue, outstanding debt total, today's attendance %, recent payments, low-stock alerts. |
| **Children** | CRUD child; manage guardians & relationships; assign group & tariff; enrollment lifecycle; search & filter; photo upload. |
| **Payments** | Generate monthly invoices; record payments (cash/card/transfer); partial payments; generate receipts; view child statement. |
| **Debtors** | List children with outstanding balance; overdue flags; send reminders; drill into ledger. |
| **Attendance** | Mark daily status per child/group; check-in/out; absence reasons; monthly attendance view; edit same-day corrections. |
| **Payroll** | Manage employees & positions; create monthly payroll run; per-employee bonus/deduction; finalize & mark paid; payslip. |
| **Kitchen & Warehouse** | Manage products, categories, suppliers, warehouses; record stock in (purchase) and out (consumption/waste); low-stock alerts. |
| **Expenses** | Record expense with category & receipt; approval workflow (pending→approved/rejected→paid). |
| **Reports** | Monthly P&L, revenue, debtors, attendance, payroll, expense reports; export to Excel/PDF. |
| **Notifications** | Editable templates; send SMS on payment & for debt reminders; view delivery status & retries. |
| **Settings** | System-wide config (tariff defaults, reminder cadence, SMS provider), feature flags, branch settings. |
| **Users & Roles** | CRUD users; assign roles; manage role→permission mapping; deactivate users; view audit log. |

---

## 8. Non-Functional Requirements (NFRs)

| Category | Requirement | Where addressed |
|----------|-------------|-----------------|
| **Security** | JWT auth, deny-by-default RBAC, audit logs, rate limiting, TLS, input validation | [02](./02_Software_Architecture.md) §20 |
| **Performance** | List screens < 300 ms server time; indexed queries; heavy work async | [02](./02_Software_Architecture.md) §21, [03](./03_Database_Design.md) §22 |
| **Reliability** | No lost payments; idempotent billing; transactional money/stock ops | [03](./03_Database_Design.md) §25 |
| **Auditability** | Every financial/admin mutation logged (who/what/when) | [03](./03_Database_Design.md) §19 |
| **Scalability** | Add modules & branches without refactor; horizontal API scaling | [02](./02_Software_Architecture.md) §22, [03](./03_Database_Design.md) §26 |
| **Usability** | Clean admin UX; consistent loading/error/empty states; fast forms | [05](./05_Frontend_Architecture.md) |
| **Localization** | UI language-ready (Uzbek/Russian); `timestamptz` UTC storage, branch-timezone display; `UZS` currency default | [03](./03_Database_Design.md) §3, §6 |
| **Maintainability** | Uniform module structure; business logic in service layer; documented contracts | [02](./02_Software_Architecture.md) §5 |
| **Availability** | Single-server MVP; stateless API enables future HA | [02](./02_Software_Architecture.md) §23 |
| **Data integrity** | DB-level constraints; append-only ledgers; soft delete | [03](./03_Database_Design.md) §21 |

---

## 9. Success Criteria (MVP)

The MVP is "done" when a kindergarten can, **entirely in the system**:
1. Enroll a child with guardians, assign a group and tariff.
2. Generate that child's monthly invoice automatically.
3. Take a payment and print/send a receipt (SMS).
4. See the child appear/disappear from the **Debtors** list based on real payment state.
5. Mark daily attendance for a group.
6. Run monthly payroll for staff and produce payslips.
7. Track kitchen stock and get a low-stock alert.
8. Record and approve an expense.
9. Open the Dashboard and see accurate live numbers for all of the above.
10. Do all of this under role-appropriate access, with every money action audit-logged.

**Quality bars:** no data loss, no billing double-charge, reports reconcile to the ledger to the cent, and every endpoint enforces RBAC.

---

## 10. Constraints & Assumptions

| Type | Statement |
|------|-----------|
| Constraint | Deployment target is a single **Linux server** with Docker; no managed cloud services assumed for MVP. Infrastructure is **vendor-operated and self-funded** (§4) — this is a bootstrapped, founder-built product, so infrastructure spend must stay proportional to subscription revenue. |
| Constraint | **Built and operated by one person.** Scope decisions are judged against time-to-first-revenue and personal runway, not against a feature list ([06 §2](./06_Development_Roadmap.md)). |
| Constraint | ⚠️ **Data residency** — the system stores personal data of minors who are citizens of Uzbekistan. Uzbek personal-data legislation imposes localization requirements on such data. **Hosting jurisdiction must be confirmed with legal counsel before the first paying customer**; it constrains the choice of hosting provider, not just the deployment script. |
| Constraint | Notifications MVP channel is **SMS** via a third-party gateway (provider abstracted). |
| Constraint | Currency default **UZS**; timezone default **Asia/Tashkent** (branch-configurable). Subscription prices are **version-dated** — under UZS inflation, existing customers stay on their purchased price while new customers get current pricing. |
| Constraint | Customers are **legal entities** paying by bank transfer against an invoice/act. Subscription billing must support the invoice-and-transfer flow, not card-only. |
| Assumption | Staff have desktop/laptop browser access; mobile browser usable but not the primary target. |
| Assumption | Internet connectivity is generally available (SMS and app are online). |
| Assumption | Most organizations run one branch at launch; the data model and UI support unlimited branches per subscription from day one (§4.1). |
| Assumption | Per-child revenue is **seasonal** — enrollment falls in summer, so subscription revenue falls with it. Annual prepayment terms (§4.3) exist partly to smooth this. |

---

## 11. Glossary

> **Naming discipline:** "plan", "invoice", and "payment" exist in **two unrelated domains** (§4.6). Terms below are marked **[tuition]** (kindergarten → parent) or **[subscription]** (vendor → kindergarten). Never use the bare word where the domain is ambiguous.

| Term | Meaning |
|------|---------|
| **Organization** | The customer — one kindergarten business, possibly with several branches. The **tenancy root** and the billing boundary. All data belongs to exactly one organization. |
| **Branch** | A physical kindergarten location **inside** an organization; the operational scope for staff, reporting, and invoice numbering. Not a tenancy boundary. |
| **Tenant** | Synonym for Organization. Used when discussing isolation and data scoping. |
| **Guardian** | A parent/caregiver linked to a child; the SMS recipient. |
| **Group** | A kindergarten class (e.g. "Sunflowers"). |
| **Enrollment** | A dated membership of a child in a group. |
| **Tariff Plan** *[tuition]* | The recurring fee definition applied to a child. |
| **Invoice** *[tuition]* | A billing document issued to a guardian for a child for one period. |
| **Ledger** *[tuition]* | The append-only record of all charges/payments per child; the source of truth for balances. |
| **Debtor** *[tuition]* | A child whose ledger balance is positive (owes money) — a *derived* state, not a stored table. |
| **Subscription Plan** *[subscription]* | The vendor's pricing definition: base price, included children, overage step, currency, effective dates (§4.2). |
| **Subscription** *[subscription]* | An organization's active commercial agreement: plan, payment term, status, period dates. |
| **Usage Snapshot** *[subscription]* | An immutable per-period record of an organization's billable child count and how it was measured. The evidence behind every subscription invoice. |
| **Subscription Invoice** *[subscription]* | A billing document issued by the vendor to an organization. |
| **Trial** | The 15-day risk-free evaluation period (§4.4). |
| **Payroll Run** | A monthly batch that computes salaries for all employees. |
| **Stock Movement** | An immutable in/out record for a product; source of truth for stock levels. |
| **RBAC** | Role-Based Access Control — permissions granted via roles. |
| **Platform Admin** | Vendor-side staff operating the SaaS. **Not** a customer role and not a row in the customer role matrix ([02 §11](./02_Software_Architecture.md)). |
| **Org Owner** | The customer's own top administrator — full control across all branches **of their own organization only**. |
| **Audit Log** | Immutable record of who did what to which record. |

---

## 12. Document Governance

- This document is **upstream of all others**. A functional/scope change starts here.
- Downstream docs ([02](./02_Software_Architecture.md)–[06](./06_Development_Roadmap.md)) must remain **consistent** with this vision; conflicts are resolved in favor of an explicit decision recorded here or as an ADR in [02](./02_Software_Architecture.md) §2.
- The build sequence that realizes this scope is in [06_Development_Roadmap](./06_Development_Roadmap.md).

*End of Project Vision v1.1 — multi-tenant SaaS business model added (§4); see [00_INDEX](./00_INDEX.md) change log.*
