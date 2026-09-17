#!/usr/bin/env bash
#
# KG-CRM — takrorlanuvchi deploy.
#
# Maqsad: serverga kirib qo'lda biror narsa o'zgartirish KERAK
# BO'LMASIN. Har bir qadam shu yerda, bir xil tartibda, har safar.
#
#   git clone → cp .env.production.example .env → (to'ldiring) → ./scripts/deploy.sh
#
# Qadamlar ATAYLAB shu tartibda:
#   1. sozlama tekshiriladi   — yarim ko'tarilgan stek qolmasin
#   2. tasvirlar yig'iladi    — eski tasvir bilan yangi migratsiya ishlamasin
#   3. baza va Redis          — qolganlari ularsiz ishlamaydi
#   4. migratsiya             — EGA roli bilan, bir marta, bitta joyda
#   5. check_rls              — migratsiya siyosatlarni HAQIQATAN qo'ydimi
#   6. collectstatic          — nginx o'qiydigan volume to'ldiriladi
#   7. ilova ko'tariladi
#   8. health                 — "ishga tushdi" emas, "javob beryapti"
#
# Migratsiya konteyner boot'ida ATAYLAB emas: bir nechta nusxa bir vaqtda
# ko'tarilsa, ular bir xil migratsiyani birga bajarishga urinadi.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

COMPOSE="docker compose -f compose.prod.yaml"
GREEN=$'\033[32m'; RED=$'\033[31m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; OFF=$'\033[0m'

step() { printf '\n%s▸ %s%s\n' "$BOLD" "$1" "$OFF"; }
fail() { printf '%s✗ %s%s\n' "$RED" "$1" "$OFF"; exit 1; }
ok()   { printf '  %s✓ %s%s\n' "$GREEN" "$1" "$OFF"; }

# --- 1. Sozlama ---
step "Sozlama tekshirilmoqda"

[ -f .env ] || fail ".env topilmadi. Namuna: cp .env.production.example .env"

# shellcheck disable=SC1091
set -a; . ./.env; set +a

for var in DJANGO_SECRET_KEY OWNER_DB_PASSWORD APP_DB_PASSWORD BACKUP_DB_PASSWORD \
           DJANGO_ALLOWED_HOSTS PUBLIC_BASE_URL; do
    [ -n "${!var:-}" ] || fail "$var .env da to'ldirilmagan"
done

# Kalit uzunligi: bu HS256 imzo kaliti hamdir (RFC 7518 §3.2). Server
# baribir tekshiradi va yiqiladi — lekin deploy'ning 7-qadamida
# yiqilgandan ko'ra, 1-qadamda aytgani yaxshi.
[ "${#DJANGO_SECRET_KEY}" -ge 32 ] || fail "DJANGO_SECRET_KEY kamida 32 belgi bo'lishi kerak"

[ "$OWNER_DB_PASSWORD" != "$APP_DB_PASSWORD" ] || fail "Ega va ilova parollari bir xil bo'lmasligi kerak"
ok "sozlama to'liq"

# --- 2. Tasvirlar ---
step "Tasvirlar yig'ilmoqda"
$COMPOSE build
ok "tasvirlar tayyor"

# --- 3. Baza va Redis ---
step "Baza va Redis ko'tarilmoqda"
$COMPOSE up -d db redis
# shellcheck disable=SC2016  # o'zgaruvchilar KONTEYNER ichida ochilishi kerak
$COMPOSE exec -T db sh -c 'until pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do sleep 1; done'
ok "baza javob beryapti"

# --- 4. Migratsiya (EGA roli bilan) ---
step "Migratsiyalar qo'llanmoqda"
$COMPOSE run --rm --no-deps \
    -e POSTGRES_USER="${POSTGRES_OWNER:-kg_crm}" \
    -e POSTGRES_PASSWORD="$OWNER_DB_PASSWORD" \
    web python manage.py migrate --noinput
ok "migratsiyalar qo'llandi"

# --- 5. RLS holati ---
step "RLS holati tekshirilmoqda"
# Qo'llanilgan migratsiya tahrirlansa Django uni QAYTA ISHGA
# TUSHIRMAYDI — ya'ni jonli baza eski siyosatlar bilan qolib ketishi
# mumkin, va tashqaridan hammasi normal ko'rinadi (CLAUDE.md 8-invariant).
$COMPOSE run --rm --no-deps \
    -e POSTGRES_USER="${POSTGRES_OWNER:-kg_crm}" \
    -e POSTGRES_PASSWORD="$OWNER_DB_PASSWORD" \
    web python manage.py check_rls || fail "RLS siyosatlari kutilgan holatda emas — deploy TO'XTATILDI"
ok "RLS kuchda"

# --- 6. Statik fayllar ---
step "Statik fayllar yig'ilmoqda"
$COMPOSE run --rm --no-deps web python manage.py collectstatic --noinput >/dev/null
ok "statik fayllar volume'da"

# --- 7. Ilova ---
step "Ilova ko'tarilmoqda"
$COMPOSE up -d
ok "konteynerlar ishga tushdi"

# --- 8. Health ---
step "Tiriklik tekshiruvi"
PORT="${HTTP_PORT:-80}"
# nginx `server_name` sifatida $DOMAIN ni kutadi, va Django
# ALLOWED_HOSTS ham xuddi shu qiymatga cheklangan (to'g'ri production
# konfiguratsiyasi — "localhost" ochiq qoldirilmagan). Loopback orqali
# so'ralganda curl Host sarlavhasini URL'dagi "localhost"dan oladi, va
# bu ALLOWED_HOSTS bilan mos kelmaydi — Django `400 DisallowedHost`
# qaytaradi, ilova esa aslida sog'lom bo'lsa ham. Sarlavha aniq
# ko'rsatilishi shart.
HEALTH_HOST="${DOMAIN:-localhost}"
# `X-Forwarded-Proto: https`: TLS yoqilgan bo'lsa (`DJANGO_SECURE_SSL_REDIRECT=True`,
# to'g'ri production holati), bu sarlavhasiz so'rov Django'dan `301`
# oladi — nginx haqiqiy so'rovlarda qo'yadigan sarlavha shu, health
# tekshiruvi ham xuddi shunday so'rashi kerak (compose.prod.yaml dagi
# web healthcheck'dagi bilan bir xil sabab).
for attempt in $(seq 1 30); do
    # `-f` bilan cheklanib bo'lmaydi: u `301` ni XATO deb hisoblamaydi,
    # ya'ni "HTTPS'ga haydaldi" javobi ham muvaffaqiyat bo'lib ko'rinardi.
    # Shuning uchun ham kod, ham TANA tekshiriladi.
    BODY=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: ${HEALTH_HOST}" -H "X-Forwarded-Proto: https" "http://localhost:${PORT}/api/v1/health" || true)
    if [ "$BODY" = "200" ] && curl -s -H "Host: ${HEALTH_HOST}" -H "X-Forwarded-Proto: https" "http://localhost:${PORT}/api/v1/health" | grep -q '"status":"ok"'; then
        ok "health javob berdi ($((attempt * 2))s)"
        curl -s -H "Host: ${HEALTH_HOST}" -H "X-Forwarded-Proto: https" "http://localhost:${PORT}/api/v1/health"; echo
        printf '\n%sDEPLOY TUGADI%s\n' "$GREEN$BOLD" "$OFF"
        printf '%s  TLS uchun: ./scripts/tls-setup.sh%s\n' "$DIM" "$OFF"
        exit 0
    fi
    sleep 2
done

printf '%s✗ health javob bermadi%s\n' "$RED" "$OFF"
$COMPOSE logs --tail=40 web
exit 1
