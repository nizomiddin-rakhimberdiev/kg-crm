#!/usr/bin/env bash
#
# `/private` demo stekini (standalone, ADR-13) yangilash — `deploy.sh` ning
# kichik ukasi. Asosiy `deploy.sh` FAQAT SaaS stekini yangilaydi; bu stek
# alohida tasvirlar bilan ishlaydi va o'zi yangilanmaydi. Ikkalasini ham
# yangilash kerak bo'lsa: ./scripts/deploy.sh && ./scripts/deploy-private.sh
#
# Qadamlar deploy.sh bilan bir xil tartibda: build → migrate (ega roli) →
# check_rls → collectstatic → up → tiriklik.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

ENV_FILE="${PRIVATE_ENV_FILE:-.env.private}"
COMPOSE="docker compose -f compose.private-demo.yaml --env-file $ENV_FILE"
GREEN=$'\033[32m'; RED=$'\033[31m'; BOLD=$'\033[1m'; OFF=$'\033[0m'

step() { printf '\n%s▸ %s%s\n' "$BOLD" "$1" "$OFF"; }
fail() { printf '%s✗ %s%s\n' "$RED" "$1" "$OFF"; exit 1; }
ok()   { printf '  %s✓ %s%s\n' "$GREEN" "$1" "$OFF"; }

step "Sozlama tekshirilmoqda"
[ -f "$ENV_FILE" ] || fail "$ENV_FILE topilmadi"
# shellcheck disable=SC1090
set -a; . "./$ENV_FILE"; set +a
for var in OWNER_DB_PASSWORD APP_DB_PASSWORD; do
  [ -n "${!var:-}" ] || fail "$ENV_FILE ichida $var bo'sh"
done
ok "sozlama to'liq"

step "Tasvirlar yig'ilmoqda"
$COMPOSE build private-web private-worker private-nginx >/dev/null
ok "tasvirlar tayyor"

step "Migratsiyalar qo'llanmoqda (ega roli bilan)"
$COMPOSE run --rm --no-deps \
  -e POSTGRES_USER="${POSTGRES_OWNER:-kg_crm}" \
  -e POSTGRES_PASSWORD="$OWNER_DB_PASSWORD" \
  private-web python manage.py migrate --noinput
ok "migratsiyalar qo'llandi"

step "RLS holati tekshirilmoqda"
$COMPOSE run --rm --no-deps \
  -e POSTGRES_USER="${POSTGRES_OWNER:-kg_crm}" \
  -e POSTGRES_PASSWORD="$OWNER_DB_PASSWORD" \
  private-web python manage.py check_rls || fail "RLS siyosatlari kutilgan holatda emas — deploy TO'XTATILDI"
ok "RLS kuchda"

step "Statik fayllar yig'ilmoqda"
$COMPOSE run --rm --no-deps private-web python manage.py collectstatic --noinput >/dev/null
ok "statik fayllar volume'da"

step "Ilova ko'tarilmoqda"
$COMPOSE up -d >/dev/null
ok "konteynerlar ishga tushdi"

step "Tiriklik tekshiruvi"
for _ in $(seq 1 30); do
  STATUS=$($COMPOSE ps --format '{{.Service}} {{.Health}}' | awk '$1=="private-web"{print $2}')
  if [ "$STATUS" = "healthy" ]; then ok "private-web healthy"; exit 0; fi
  sleep 2
done
fail "private-web 60 s ichida healthy bo'lmadi: $($COMPOSE ps --format '{{.Service}} {{.Status}}')"
