# Backup and Restore

Operational document. Companion to [`deployment.md`](./deployment.md).

> A backup that has never been restored is not a backup. Everything below was executed end-to-end before it was written; §7 records what the rehearsal measured.

---

## 1. Why this is not a one-liner

`pg_dump` against this database has one non-obvious failure mode, and it is the dangerous kind — silent.

Every tenant table carries `FORCE ROW LEVEL SECURITY`. Under `FORCE`, **even the table owner** is subject to the policy, and the policy matches on a session variable that a dump job never sets. So an ordinary `pg_dump` sees zero rows, exits `0`, and writes a structurally valid file containing nothing but schema. You would keep 90 days of those and discover it on the one day it matters.

The `kg_crm_backup` role exists for exactly this: it holds `BYPASSRLS` and read-only rights (`deploy/postgres/01-roles.sh`). `scripts/backup.sh` uses it, and then refuses to trust it — see §2.

Two further things live outside the database and would be missed by a database-only backup:

- **Media files** — children's photos and profile pictures, in the `media_files` volume.
- **`.env`** — the secrets. Without `DJANGO_SECRET_KEY` every existing session and token is void; without the database passwords the restored database is unreachable. It is not in git, by design. **Keep a copy somewhere safe, separately from the backups.**

---

## 2. Taking a backup

```bash
./scripts/backup.sh
```

Five steps, and the third is the one that matters:

1. Count rows in the live database (`organization`, `user`, `child`, `invoice`, `payment`, `child_ledger_entry`) and write them to a manifest. Abort if the total is zero.
2. `pg_dump -Fc` as `kg_crm_backup`; abort if the file is implausibly small.
3. **Restore the dump into a throwaway database and compare the counts to the manifest.** Any mismatch fails the backup. This is what turns "a file was produced" into "the data is in the file".
4. Encrypt both artefacts with AES-256 if `BACKUP_PASSPHRASE` is set.
5. Delete backups older than `BACKUP_RETAIN_DAYS` (default 14).

`--no-verify` skips step 3. It exists for a very large database where the verification cost is real; using it routinely gives back exactly the failure mode this script was written to prevent.

Each run produces three files:

```
backups/kg-crm-20260914-183000.dump.enc          # database
backups/kg-crm-20260914-183000-media.tar.gz.enc  # photos
backups/kg-crm-20260914-183000.manifest          # row counts at backup time
```

The manifest is deliberately left unencrypted — it contains counts, no personal data, and it lets you confirm after a restore that you got back what you had.

---

## 3. Automating it

Nightly, on the server, via the host's crontab:

```cron
30 2 * * *  cd /srv/kg-crm && ./scripts/backup.sh >> /var/log/kg-crm-backup.log 2>&1
```

02:30 sits between the nightly Celery jobs (invoice generation runs at 02:00, overdue marking at 03:00 — [`02 §18`](./02_Software_Architecture.md)), so a backup never captures a half-finished billing run.

**Check the log.** A cron job that has been failing for three weeks looks exactly like one that has been working, until you look. The script exits non-zero on every failure, so wire it to whatever will actually reach you.

---

## 4. Getting it off the server

A backup on the same disk as the database protects you from `DROP TABLE`, not from a dead server. Copy it elsewhere — the files are already encrypted, so the destination does not have to be trusted:

```bash
rclone copy ./backups remote:kg-crm-backups --include 'kg-crm-*'
# or
rsync -az ./backups/ backup-host:/srv/kg-crm-backups/
```

Add it to the same cron line, after the backup command, so the two never drift apart.

---

## 5. Restoring

```bash
./scripts/restore.sh backups/kg-crm-20260914-183000.dump.enc
```

The media archive is found automatically from the matching filename; pass it explicitly as a second argument if it lives elsewhere.

The script asks you to type the database name to confirm — not `y`, the name — because this destroys whatever is currently there. Then it:

1. decrypts,
2. stops `web`, `worker` and `beat` (restoring under live writes produces a mixture of both states, which is worse than either),
3. drops and recreates the database, runs `pg_restore`,
4. **re-grants** privileges to `kg_crm_app` and `kg_crm_backup`,
5. **re-applies RLS** and verifies it,
6. restores media,
7. brings the stack back and waits for health.

Steps 4 and 5 are not cosmetic. The dump is taken with `--no-owner --no-privileges`, so grants are absent; and RLS policies are created by a migration, not held in the dump. A restore that stopped at step 3 would come back **with tenant isolation switched off** — every kindergarten's data visible to every other — while the application appeared to work normally. That is the single most dangerous moment in this whole document, which is why the script refuses to start the application if `check_rls` does not pass.

---

## 6. After a restore, check by hand

Automation confirms the rows arrived. It does not confirm the system is usable. Take five minutes:

- [ ] `GET /api/v1/health` → `"status": "ok"`
- [ ] Sign in as a kindergarten owner
- [ ] Children list shows the expected number
- [ ] Debtors list loads and balances look right
- [ ] Record a test payment, then reverse it
- [ ] Sign in to the vendor console; organizations list is complete
- [ ] `docker compose -f compose.prod.yaml logs worker` — Celery connected
- [ ] Cross-tenant spot check: a second organization's data is **not** visible

---

## 7. RPO and RTO

Measured on the rehearsal described in §8, not estimated.

| | Value | Where it comes from |
|---|---|---|
| **RPO** (maximum data loss) | **24 hours** | Backups are nightly. A failure at 02:29 loses everything since the previous 02:30. |
| **RTO** — database lost, server alive | **~1 minute** | Measured: `restore.sh` took **15 seconds** end-to-end (decrypt → drop → `pg_restore` → re-grant → re-apply RLS → media → health). Allow a few minutes to find the file and read the confirmation prompt. |
| **RTO** — whole server lost | **1–2 hours** | Provision a host, install Docker, clone, restore `.env`, `deploy.sh`, then `restore.sh`. Dominated by provisioning, not by this software. |

Backup duration was **6 seconds**, including the verify step that restores the dump into a throwaway database.

Both figures come from a 1,040-row dataset (64 children, 256 invoices, 230 payments, 486 ledger entries) on a laptop. They will grow roughly linearly with the ledger, which is the table that only ever gets longer. Re-measure once a real customer has a year of history; if restore approaches the tens of minutes, that is the signal to move to WAL archiving.

**To improve RPO**, the next step is Postgres WAL archiving (continuous, minutes instead of hours). It is worth doing once paying customers rely on the system; it is not worth doing before that, because the operational complexity would be carried for months with nothing behind it.

---

## 8. The rehearsal

Performed on 2026-09-14 against the full production stack, on a database deliberately rebuilt from scratch.

1. Fresh deploy on empty volumes.
2. Real data created through the API: a vendor account, a kindergarten, an owner, children, invoices, payments.
3. `./scripts/backup.sh` — including the verify step.
4. **The database was destroyed** (`DROP DATABASE`), not simulated.
5. `./scripts/restore.sh` from the encrypted backup.
6. Row counts compared against the manifest; RLS re-verified; the §6 checklist walked.

**What it proved.** Row counts came back identical to the manifest (`child 64`, `invoice 256`, `payment 230`, `child_ledger_entry 486`, `organization 2`, `user 2`). The dashboard showed the same 64 active children and 16 debtors as before the drop, and the debtors view recomputed **40,210,000 so'm** from the restored ledger — the same figure as before. Tenant isolation survived: the second kindergarten still saw **0** children, a cross-tenant request still returned `404`, and a raw SQL query with no tenant context still returned **0** rows. Writes worked (a payment was recorded and reversed), Celery reconnected, and the vendor console listed both organizations.

**And it proved the premise.** Dumped with the ordinary application role, the same database produced a 40 KB file — full schema, plausible-looking, **zero rows**. With `kg_crm_backup`: 1.2 MB, 65 children, 3 organizations. That 40 KB file is what a naive backup script would have been storing every night.

Repeat this rehearsal after any change to the database roles, the RLS policies, or the backup scripts — those three are what can quietly break a restore.
