# Deployment Runbook

Operational document. The design documents are `00`–`06`; this one is about getting the thing onto a server and keeping it there.

---

## 1. What runs

Six containers, one command.

| Service | Image | Purpose | Host port |
|---------|-------|---------|-----------|
| `nginx` | built (`deploy/Dockerfile.web`) | Serves the SPA, proxies `/api/`, terminates TLS | 80, 443 |
| `web` | built (`backend/Dockerfile`) | Gunicorn, 3 workers | — |
| `worker` | same image | Celery worker | — |
| `beat` | same image | Celery scheduler — **exactly one instance** | — |
| `db` | `postgres:17-alpine` | — | — |
| `redis` | `redis:7-alpine` | Cache + Celery broker, AOF persistence | — |

`db` and `redis` publish **no host ports**. They are reachable only from the compose network. This is the single largest difference from `backend/docker-compose.yml`, which exposes both for local convenience.

`beat` must never be scaled past one. Two schedulers enqueue every periodic task twice — two invoice runs, two SMS batches.

---

## 2. First deploy on a fresh server

Requirements: Docker Engine with the Compose plugin, a domain pointed at the server, ports 80/443 open.

```bash
git clone <repo> kg-crm && cd kg-crm
cp .env.production.example .env
$EDITOR .env                     # see §3
./scripts/deploy.sh
```

That is the whole procedure. The script refuses to continue rather than half-finishing: it validates configuration before building, and stops the deploy if the RLS check fails.

Then, once DNS resolves to the server:

```bash
./scripts/tls-setup.sh
```

Until certificates exist nginx serves plain HTTP — deliberately. TLS needs a certificate, the certificate needs an ACME request to reach port 80, and that needs nginx already running. A configuration that always demanded TLS would make the first deploy impossible.

---

## 3. Configuration

Every value lives in `.env`, which is never committed. `.env.production.example` lists all of them.

Generate each secret separately:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

`DJANGO_SECRET_KEY` is also the JWT signing key, so it must be at least 32 bytes — `production.py` refuses to boot below that, and `deploy.sh` checks it at step 1 so the failure arrives before the build rather than after it.

**Three database passwords, because there are three roles** (`deploy/postgres/01-roles.sh`):

| Role | Used by | Rights |
|------|---------|--------|
| `kg_crm` (owner) | migrations only | owns the tables |
| `kg_crm_app` | the running application | DML only — **cannot** disable RLS or drop policies |
| `kg_crm_backup` | `pg_dump` | read-only + `BYPASSRLS` |

The split is what stops a single SQL-injection with owner rights from turning off Row-Level Security across every tenant. `kg_crm_backup` needs `BYPASSRLS` for a different reason: under `FORCE ROW LEVEL SECURITY` an ordinary role's `pg_dump` sees no rows and writes a **silently empty backup** — the worst kind of failure, since it looks fine until the day you need it.

> The role script runs only when the Postgres volume is first created. Applying it to an existing database is manual.

---

## 4. Deploying a change

```bash
git pull
./scripts/deploy.sh
```

Same script. It rebuilds, migrates, re-checks RLS, re-collects static files, and restarts. Migrations run as a **separate step**, never at container boot: several containers starting at once would run the same migration concurrently.

`python manage.py check_rls` runs on every deploy and **gates it**. An edited migration is not re-applied by Django, so a live database can silently keep old policies while everything looks healthy — this check is what catches that.

**There is no automatic deploy.** GitHub Actions only runs tests and a build (and currently fails at startup for an account-level reason); nothing watches `main`. A commit reaches the site only when someone runs the script above on the server. `main` should always equal what is deployed — push it forward after each deploy.

**The `/private` demo is a second stack and does not update itself.** `deploy.sh` touches only the SaaS stack. After deploying, run:

```bash
./scripts/deploy-private.sh
```

It repeats the same steps (build → migrate as owner → `check_rls` → collectstatic → up → health) against `compose.private-demo.yaml` with `.env.private`. Forgetting it is the classic "I deployed but the demo still looks old".

---

## 5. Routine operations

```bash
C="docker compose -f compose.prod.yaml"

$C ps                            # what is running
$C logs -f web                   # application logs
$C logs -f worker                # background jobs
$C restart web                   # restart one service
$C exec db psql -U kg_crm kg_crm # database shell (owner)

# Django admin is NOT routed in production (P2-006) — it is a session-based,
# 2FA-less second privileged path, and the platform console replaces it.
# For break-glass work use the shell:
$C run --rm web python manage.py shell
```

Create a vendor (platform console) account — a command, not an endpoint, because an endpoint that mints vendor accounts would be the single most valuable target in the system:

```bash
$C run --rm web python manage.py create_platform_user
```

---

## 6. Health

`GET /api/v1/health` returns `200` with `{"status": "ok"}` or `503` with `"degraded"`, and names which dependency failed:

```json
{"status": "ok", "checks": {"database": "ok", "cache": "ok"}}
```

The cache check writes and reads back rather than only reading — a dead Redis can still return `None` without raising, which once let the endpoint report "ok" while login was returning `500`.

The check also pings the Celery worker. A dead worker reports `degraded` — and `degraded` deliberately still returns **`200`**: without a worker the system is still readable and still takes payments, so a load balancer must not pull the server out of rotation. Only `error` (database or cache gone) returns `503`.

**Request tracing.** Every response carries an `X-Request-ID`, and every log line is prefixed with it. If a client sends the header, that value is kept — so a frontend error and the backend log for it share one identifier. The error screen in the SPA shows the id, which turns "something broke yesterday afternoon" into one `grep`.

---

## 7. Troubleshooting

**`health` never answers.** `$C logs web`. Most often `DJANGO_ALLOWED_HOSTS` does not include the host being requested — Django answers `400` before any view runs.

**Static files 404.** `collectstatic` did not populate the shared volume: `$C run --rm web python manage.py collectstatic --noinput`.

**`check_rls` fails the deploy.** Do not bypass it. `$C run --rm web python manage.py check_rls` prints which tables are wrong; `--fix` reapplies the policies.

**502 from nginx.** First check that `web` is up (`$C ps`, `$C logs web`). If it is, this used to have a second cause worth knowing: and it is worth knowing why. nginx resolves an `upstream` hostname **once, at startup**, and caches the address forever; in Docker a recreated container gets a new IP, so nginx kept proxying to a dead address and the whole site answered `502` — after every deploy, silently. The configuration now resolves `web` through Docker's DNS on each request (`deploy/nginx/_shared.conf`). If you see this again, check that the `resolver` line is still present.

**`301` to HTTPS on every API call, before certificates exist.** `DJANGO_SECURE_SSL_REDIRECT=True` with nginx in HTTP-only mode redirects everything to a URL that does not answer yet. Set it to `False` until `tls-setup.sh` has run, then back to `True`. nginx performs the redirect itself in TLS mode, so the Django-level flag is a second line of defence, not the only one.

**Certificate did not issue.** `dig +short <domain>` must return the server's address, and port 80 must be reachable from the internet. Let's Encrypt rate-limits repeated failures, so fix DNS before retrying.

---

## 8. Staging

A staging instance is the same stack with a different project name, different ports and its own data. Nothing is shared — separate network, separate volumes, separate database — so a broken deploy on staging cannot reach production.

```bash
git clone <repo> kg-crm-staging && cd kg-crm-staging
cp .env.production.example .env
```

Then change four things in `.env`:

```bash
COMPOSE_PROJECT_NAME=kg-crm-staging
HTTP_PORT=8080
HTTPS_PORT=8443
DOMAIN=staging.kg-crm.uz
PUBLIC_BASE_URL=https://staging.kg-crm.uz
DJANGO_ALLOWED_HOSTS=staging.kg-crm.uz
```

**Generate new secrets.** Reusing production's `DJANGO_SECRET_KEY` would make staging tokens valid against production, and reusing the database passwords would put production credentials on a machine that exists to be broken.

```bash
./scripts/deploy.sh
```

Staging is where a change is tried before production sees it: migrations against real-shaped data, the RLS check, a backup and a restore, TLS issuance. Populate it from a production backup (`restore.sh`) when you need realistic data — and remember that copy is real personal data and deserves the same care as production.

---

## 9. What the first real deploy found

This procedure was executed end-to-end before being written down. It failed three times, and each failure is now closed — recorded here because all three are invisible to code review and only appear on a real server.

| Failure | Cause | Fix |
|---|---|---|
| `collectstatic` → `Permission denied` | The container runs as a non-root user; a fresh Docker named volume is created **root-owned** | The directories are created in the image with the right owner, so the volume inherits it (`backend/Dockerfile`) |
| Health check passed while the API was unusable | `curl -f` treats a `301` as success, so "redirected to HTTPS" looked healthy | The check now requires `200` **and** `"status":"ok"` in the body — in `deploy.sh` and in the container healthcheck |
| `502` for the whole site after restarting `web` | nginx cached the upstream IP from startup; the recreated container had a different one | Per-request DNS resolution through Docker's resolver |

Verified afterwards, on the running stack: the application role cannot `ALTER TABLE … NO FORCE ROW LEVEL SECURITY` nor `DROP POLICY` (`must be owner of table`); a query with no tenant context returns **0** rows; the backup role reads rows but cannot write; Celery worker and beat are both live; and with `web`'s IP forcibly changed from `172.18.0.5` to `172.18.0.8`, nginx — untouched — still answered correctly.

---

## 10. Not yet done

Honest list — these are open, not implied:

- **Off-server copy of backups.** `scripts/backup.sh` and `scripts/restore.sh` exist and the restore has been rehearsed against a destroyed database ([`backup-restore.md`](./backup-restore.md)). What is still manual: scheduling the nightly cron on the server and copying the encrypted files somewhere other than that server.
- **Error tracking and log aggregation.** Every response and log line now carries a request id (§6), but logs still only go to stdout on one machine: there is no aggregation, no search across restarts, and no alerting. A crash at 02:00 is found by looking, not by being told.
- **A real SMS gateway.** `NOTIFICATION_PROVIDER=console` writes messages to the log.
- **Three known vulnerabilities in frontend dev tooling** (vite dev-server path traversal; Vitest UI RCE). Neither runs in production, and the CI gate audits shipped dependencies (`--omit=dev`), which are clean. Fixing them needs a major upgrade that is currently blocked by a peer-dependency deadlock: `@vitejs/plugin-react` supports vite ≤ 7, vitest 5 requires vite ≥ 6.4, and npm refuses the combination. Revisit when `@vitejs/plugin-react` adds vite 8 support.
