#!/usr/bin/env bash
#
# KG-CRM — zaxiradan tiklash.
#
# Bu skript MA'LUMOTNI O'CHIRADI va uni zaxiradagi holat bilan
# almashtiradi. Shuning uchun u tasdiq so'raydi va tasdiq sifatida
# baza nomini aynan yozishni talab qiladi — "ha" deb bosib yuborish
# mumkin bo'lmasin.
#
# Ishlatish:
#   ./scripts/restore.sh backups/kg-crm-20260914-120000.dump
#   ./scripts/restore.sh backups/kg-crm-20260914-120000.dump.enc
#
# Tiklashdan KEYIN `check_rls` majburiy: dump ichida RLS siyosatlari
# YO'Q (ular migratsiyada yaratiladi), ya'ni tiklangan baza himoyasiz
# qolishi mumkin. Skript buni o'zi bajaradi va natijasini ko'rsatadi.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

COMPOSE="docker compose -f compose.prod.yaml"
GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; OFF=$'\033[0m'
step() { printf '\n%s▸ %s%s\n' "$BOLD" "$1" "$OFF"; }
ok()   { printf '  %s✓ %s%s\n' "$GREEN" "$1" "$OFF"; }
die()  { printf '  %s✗ %s%s\n' "$RED" "$1" "$OFF"; exit 1; }

DUMP="${1:-}"
[ -n "$DUMP" ] || { echo "Ishlatish: $0 <zaxira-fayli> [media-arxivi]"; exit 2; }
[ -f "$DUMP" ] || die "Fayl topilmadi: $DUMP"

[ -f .env ] || die ".env topilmadi"
# shellcheck disable=SC1091
set -a; . ./.env; set +a

DB="${POSTGRES_DB:-kg_crm}"
OWNER="${POSTGRES_OWNER:-kg_crm}"

# Media arxivi: berilmasa, dump nomidan taxmin qilamiz.
MEDIA="${2:-}"
if [ -z "$MEDIA" ]; then
    GUESS="${DUMP%.enc}"; GUESS="${GUESS%.dump}-media.tar.gz"
    [ -f "$GUESS" ] && MEDIA="$GUESS"
    [ -f "$GUESS.enc" ] && MEDIA="$GUESS.enc"
fi

# --- Ogohlantirish ---
printf '%s%s' "$YELLOW$BOLD" "
  DIQQAT
"
printf '%s' "$OFF"
cat <<INFO
  Baza:    $DB
  Zaxira:  $DUMP
  Media:   ${MEDIA:-yoq}

  Bazaning HOZIRGI mazmuni butunlay o'chiriladi.
INFO
printf '\n  Davom etish uchun baza nomini aynan yozing (%s): ' "$DB"
read -r CONFIRM
[ "$CONFIRM" = "$DB" ] || die "Tasdiq mos kelmadi — hech narsa o'zgartirilmadi"

# --- Shifrni ochish ---
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

decrypt_if_needed() {
    local src="$1" dst="$2"
    if [ "${src##*.}" = "enc" ]; then
        [ -n "${BACKUP_PASSPHRASE:-}" ] || die "Fayl shifrlangan, lekin BACKUP_PASSPHRASE .env da yo'q"
        openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
            -in "$src" -out "$dst" -pass env:BACKUP_PASSPHRASE \
            || die "Shifrni ochib bo'lmadi — parol noto'g'ri yoki fayl buzuq"
    else
        cp "$src" "$dst"
    fi
}

step "Zaxira tayyorlanmoqda"
decrypt_if_needed "$DUMP" "$WORK/db.dump"
ok "dump: $(du -h "$WORK/db.dump" | cut -f1)"

# --- Ilovani to'xtatamiz ---
#
# Tiklash paytida ilova yozishda davom etsa, natija zaxira ham emas,
# joriy holat ham emas — ikkalasining aralashmasi bo'ladi.
step "Ilova to'xtatilmoqda"
$COMPOSE stop web worker beat >/dev/null 2>&1 || true
ok "web · worker · beat to'xtadi"

# --- Bazani almashtiramiz ---
step "Baza tiklanmoqda"
$COMPOSE exec -T db psql -U "$OWNER" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
$COMPOSE exec -T db psql -U "$OWNER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB\";" >/dev/null \
    || die "Eski bazani o'chirib bo'lmadi"
$COMPOSE exec -T db psql -U "$OWNER" -d postgres -c "CREATE DATABASE \"$DB\" OWNER \"$OWNER\";" >/dev/null \
    || die "Baza yaratilmadi"

$COMPOSE exec -T db pg_restore -U "$OWNER" -d "$DB" --no-owner --no-privileges < "$WORK/db.dump" \
    || die "pg_restore yiqildi"
ok "qatorlar tiklandi"

# --- Huquqlar ---
#
# Dump `--no-privileges` bilan olingan, ya'ni GRANT'lar unda YO'Q. Yangi
# bazada `ALTER DEFAULT PRIVILEGES` ham ishlamaydi (u faqat kelajakdagi
# jadvallarga ta'sir qiladi, tiklanganlari esa allaqachon mavjud).
# Shuning uchun huquqlar shu yerda qayta beriladi — busiz ilova
# "permission denied" bilan yiqilardi.
step "Rol huquqlari qayta berilmoqda"
$COMPOSE exec -T db psql -U "$OWNER" -d "$DB" >/dev/null <<SQL
GRANT USAGE ON SCHEMA public TO kg_crm_app, kg_crm_backup;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO kg_crm_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO kg_crm_app;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO kg_crm_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE "$OWNER" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kg_crm_app;
ALTER DEFAULT PRIVILEGES FOR ROLE "$OWNER" IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO kg_crm_app;
ALTER DEFAULT PRIVILEGES FOR ROLE "$OWNER" IN SCHEMA public
    GRANT SELECT ON TABLES TO kg_crm_backup;
SQL
ok "kg_crm_app va kg_crm_backup huquqlari tiklandi"

# --- RLS ---
#
# Dump'da siyosatlar YO'Q: ular migratsiya bilan qo'yiladi va
# `--no-privileges` ularni olib tashlaydi. Ya'ni tiklangan baza shu
# qadamgacha HIMOYASIZ. Bu eng jim xavf, shuning uchun u avtomatik.
step "RLS siyosatlari qayta qo'llanmoqda"
$COMPOSE run --rm --no-deps -T \
    -e POSTGRES_USER="$OWNER" -e POSTGRES_PASSWORD="$OWNER_DB_PASSWORD" \
    web python manage.py check_rls --fix >/dev/null 2>&1 || true
$COMPOSE run --rm --no-deps -T \
    -e POSTGRES_USER="$OWNER" -e POSTGRES_PASSWORD="$OWNER_DB_PASSWORD" \
    web python manage.py check_rls || die "RLS tiklanmadi — baza HIMOYASIZ, ilovani ko'tarmang"
ok "RLS kuchda"

# --- Media ---
if [ -n "$MEDIA" ] && [ -f "$MEDIA" ]; then
    step "Media fayllar tiklanmoqda"
    decrypt_if_needed "$MEDIA" "$WORK/media.tar.gz"
    $COMPOSE run --rm --no-deps -T -v "$WORK:/restore" web \
        sh -c 'rm -rf /app/mediafiles/* && tar xzf /restore/media.tar.gz -C /app/mediafiles' \
        || die "Media tiklanmadi"
    ok "media tiklandi"
fi

# --- Ilovani qaytaramiz ---
step "Ilova ko'tarilmoqda"
$COMPOSE up -d >/dev/null 2>&1
PORT="${HTTP_PORT:-80}"
for _ in $(seq 1 30); do
    if curl -s "http://localhost:${PORT}/api/v1/health" 2>/dev/null | grep -q '"status":"ok"'; then
        ok "health javob berdi"
        printf '\n%sTIKLASH TUGADI%s\n' "$GREEN$BOLD" "$OFF"
        printf '%s  Kritik oqimlarni qo'"'"'lda tekshiring — docs/backup-restore.md §6%s\n' "$DIM" "$OFF"
        exit 0
    fi
    sleep 2
done
die "health javob bermadi — $COMPOSE logs web"
