#!/usr/bin/env bash
#
# KG-CRM — zaxira nusxa.
#
# Uchta narsani birga qiladi va uchalasi ham majburiy:
#
#   1. BAZANI oladi — `kg_crm_backup` roli bilan. Bu rol `BYPASSRLS`
#      huquqiga ega. Busiz `pg_dump` FORCE RLS ostida hech qanday qator
#      KO'RMAYDI va xatosiz, jimgina BO'SH fayl yozadi.
#
#   2. MEDIA fayllarini oladi — bolalar rasmlari, profil suratlari.
#      Ular bazada emas, volume'da yashaydi; faqat bazani olish "zaxira
#      bor" degan yolg'on tuyg'u berardi.
#
#   3. Zaxirani TEKSHIRADI — uni vaqtinchalik bazaga tiklab, qator
#      sonlarini jonli baza bilan solishtiradi. Tekshirilmagan zaxira —
#      zaxira emas, taxmin. Bu qadam sekinroq, lekin u aynan shu
#      loyihadagi eng xavfli nosozlikni ushlaydi.
#
# Ishlatish:
#   ./scripts/backup.sh                 # to'liq: baza + media + tekshiruv
#   ./scripts/backup.sh --no-verify     # tekshiruvsiz (tavsiya etilmaydi)
#   ./scripts/backup.sh --out /mnt/nas  # boshqa katalogga
#
# Kunlik avtomatik ishlatish uchun: docs/backup-restore.md §3

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

COMPOSE="docker compose -f compose.prod.yaml"
OUT_DIR="./backups"
VERIFY=1
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-14}"

while [ $# -gt 0 ]; do
    case "$1" in
        --out) OUT_DIR="$2"; shift 2 ;;
        --no-verify) VERIFY=0; shift ;;
        *) echo "Noma'lum argument: $1"; exit 2 ;;
    esac
done

GREEN=$'\033[32m'; RED=$'\033[31m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; OFF=$'\033[0m'
step() { printf '%s▸ %s%s\n' "$BOLD" "$1" "$OFF"; }
ok()   { printf '  %s✓ %s%s\n' "$GREEN" "$1" "$OFF"; }
die()  { printf '  %s✗ %s%s\n' "$RED" "$1" "$OFF"; exit 1; }

[ -f .env ] || die ".env topilmadi"
# shellcheck disable=SC1091
set -a; . ./.env; set +a

: "${BACKUP_DB_PASSWORD:?BACKUP_DB_PASSWORD .env da belgilanmagan}"
DB="${POSTGRES_DB:-kg_crm}"

STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT_DIR"
DUMP="$OUT_DIR/kg-crm-$STAMP.dump"
MEDIA="$OUT_DIR/kg-crm-$STAMP-media.tar.gz"
MANIFEST="$OUT_DIR/kg-crm-$STAMP.manifest"

# Zaxira paytidagi haqiqatni yozib qo'yamiz — tekshiruv ham, kelajakdagi
# tiklash ham shunga qarab "to'g'ri tiklandimi?" degan savolga javob beradi.
counted_rows() {
    $COMPOSE exec -T -e PGPASSWORD="$BACKUP_DB_PASSWORD" db \
        psql -U kg_crm_backup -d "$DB" -tAF, -c "
        SELECT 'organization', count(*) FROM organization
        UNION ALL SELECT 'user', count(*) FROM \"user\"
        UNION ALL SELECT 'child', count(*) FROM child
        UNION ALL SELECT 'invoice', count(*) FROM invoice
        UNION ALL SELECT 'payment', count(*) FROM payment
        UNION ALL SELECT 'child_ledger_entry', count(*) FROM child_ledger_entry
        ORDER BY 1;" | tr -d '\r'
}

# --- 1. Baza ---
step "Baza olinmoqda ($DB)"
$COMPOSE ps --status running --services 2>/dev/null | grep -qx db || die "db konteyneri ishlamayapti"

counted_rows > "$MANIFEST" || die "qator sonlarini o'qib bo'lmadi"
TOTAL=$(awk -F, '{s+=$2} END {print s+0}' "$MANIFEST")
[ "$TOTAL" -gt 0 ] || die "jonli bazada 0 qator — zaxiraning ma'nosi yo'q, to'xtatildi"

# `-Fc` — custom format: siqilgan va `pg_restore` bilan tanlab tiklanadi.
$COMPOSE exec -T -e PGPASSWORD="$BACKUP_DB_PASSWORD" db \
    pg_dump -U kg_crm_backup -d "$DB" -Fc --no-owner --no-privileges > "$DUMP" \
    || die "pg_dump yiqildi"

SIZE=$(wc -c < "$DUMP" | tr -d ' ')
[ "$SIZE" -gt 1000 ] || die "dump juda kichik ($SIZE bayt) — bo'sh zaxira"
ok "baza: $(du -h "$DUMP" | cut -f1) · $TOTAL qator"

# --- 2. Media ---
step "Media fayllar olinmoqda"
$COMPOSE run --rm --no-deps -T -v "$(cd "$OUT_DIR" && pwd):/backup" web \
    tar czf "/backup/$(basename "$MEDIA")" -C /app/mediafiles . 2>/dev/null \
    || die "media arxivlanmadi"
ok "media: $(du -h "$MEDIA" | cut -f1)"

# --- 3. Tekshiruv ---
#
# Eng muhim qadam. Zaxira VAQTINCHALIK bazaga tiklanadi va qator sonlari
# solishtiriladi. Tekshirilmagan zaxira faqat tiklash kuni sinaladi — va
# o'sha kun buni bilish uchun eng yomon kun.
if [ "$VERIFY" = "1" ]; then
    step "Zaxira tekshirilmoqda (vaqtinchalik bazaga tiklab)"
    PROBE="kg_crm_verify_$STAMP"

    $COMPOSE exec -T db psql -U "${POSTGRES_OWNER:-kg_crm}" -d postgres \
        -c "CREATE DATABASE \"$PROBE\";" >/dev/null 2>&1 || die "tekshiruv bazasi yaratilmadi"

    cleanup_probe() {
        $COMPOSE exec -T db psql -U "${POSTGRES_OWNER:-kg_crm}" -d postgres \
            -c "DROP DATABASE IF EXISTS \"$PROBE\";" >/dev/null 2>&1 || true
    }
    trap cleanup_probe EXIT

    $COMPOSE exec -T db pg_restore -U "${POSTGRES_OWNER:-kg_crm}" -d "$PROBE" \
        --no-owner --no-privileges < "$DUMP" >/dev/null 2>&1 \
        || die "zaxirani tiklab bo'lmadi — fayl buzuq"

    # Tiklangan nusxa EGA roli bilan o'qiladi va `FORCE` hali qo'yilmagan
    # (siyosatlar dump ichida yo'q), ya'ni barcha qatorlar ko'rinadi.
    RESTORED=$($COMPOSE exec -T db psql -U "${POSTGRES_OWNER:-kg_crm}" -d "$PROBE" -tAF, -c "
        SELECT 'organization', count(*) FROM organization
        UNION ALL SELECT 'user', count(*) FROM \"user\"
        UNION ALL SELECT 'child', count(*) FROM child
        UNION ALL SELECT 'invoice', count(*) FROM invoice
        UNION ALL SELECT 'payment', count(*) FROM payment
        UNION ALL SELECT 'child_ledger_entry', count(*) FROM child_ledger_entry
        ORDER BY 1;" | tr -d '\r')

    if [ "$RESTORED" != "$(cat "$MANIFEST")" ]; then
        printf '%s  jonli:%s\n%s\n' "$DIM" "$OFF" "$(cat "$MANIFEST")"
        printf '%s  zaxirada:%s\n%s\n' "$DIM" "$OFF" "$RESTORED"
        die "qator sonlari MOS KELMADI — zaxira ishonchsiz"
    fi

    cleanup_probe
    trap - EXIT
    ok "tekshiruv o'tdi — qator sonlari aynan mos"
fi

# --- 4. Shifrlash ---
#
# Zaxirada bolalarning shaxsiy ma'lumoti bor. Server tashqarisiga
# chiqarilganda (va u ALBATTA chiqarilishi kerak) u shifrlangan bo'lishi
# shart — aks holda zaxira nusxasi eng oson o'g'irlanadigan nusxa bo'ladi.
if [ -n "${BACKUP_PASSPHRASE:-}" ]; then
    step "Shifrlanmoqda"
    for f in "$DUMP" "$MEDIA"; do
        openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
            -in "$f" -out "$f.enc" -pass env:BACKUP_PASSPHRASE || die "shifrlash yiqildi"
        rm -f "$f"
    done
    ok "shifrlandi (AES-256)"
else
    printf '  %s! BACKUP_PASSPHRASE yo'"'"'q — zaxira SHIFRLANMAGAN%s\n' "$RED" "$OFF"
fi

# --- 5. Eskilarini tozalash ---
step "Eski zaxiralar tozalanmoqda (>$RETAIN_DAYS kun)"
DELETED=$(find "$OUT_DIR" -maxdepth 1 -name 'kg-crm-*' -type f -mtime "+$RETAIN_DAYS" -print -delete | wc -l | tr -d ' ')
ok "$DELETED ta eski fayl o'chirildi · jami: $(find "$OUT_DIR" -maxdepth 1 -name 'kg-crm-*.dump*' | wc -l | tr -d ' ') ta zaxira"

printf '\n%sZAXIRA TAYYOR%s  %s%s%s\n' "$GREEN$BOLD" "$OFF" "$DIM" "$OUT_DIR/kg-crm-$STAMP.*" "$OFF"
printf '%s  Server TASHQARISIGA nusxalashni unutmang — docs/backup-restore.md §4%s\n' "$DIM" "$OFF"
