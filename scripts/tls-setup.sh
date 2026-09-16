#!/usr/bin/env bash
#
# Let's Encrypt sertifikatini oladi va nginx'ni HTTPS rejimiga o'tkazadi.
#
# Deploy'dan KEYIN, alohida ishlatiladi — chunki sertifikat olish uchun
# 80-port allaqachon ochiq va domen serverga yo'naltirilgan bo'lishi kerak.
# `scripts/deploy.sh` shu sababli TLS'siz ham to'liq ishlaydi.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

COMPOSE="docker compose -f compose.prod.yaml"
[ -f .env ] || { echo ".env topilmadi"; exit 1; }
# shellcheck disable=SC1091
set -a; . ./.env; set +a

: "${DOMAIN:?DOMAIN .env da belgilanmagan}"
EMAIL="${CERTBOT_EMAIL:-admin@${DOMAIN}}"

echo "▸ Sertifikat so'ralmoqda: $DOMAIN"
$COMPOSE --profile tls run --rm --entrypoint certbot certbot \
    certonly --webroot -w /var/www/certbot \
    -d "$DOMAIN" --email "$EMAIL" \
    --agree-tos --no-eff-email --non-interactive

echo "▸ Sertifikat nginx ko'radigan volume'ga ko'chirilmoqda"
# nginx `/etc/nginx/certs/` dan o'qiydi; certbot `/etc/letsencrypt/live/...`
# ga yozadi. Ko'chirish ATAYLAB nusxalash bilan: nginx konteyneriga butun
# `letsencrypt` katalogini (barcha domenlar, barcha kalitlar) berish
# o'rniga faqat kerakli ikki fayl beriladi.
$COMPOSE --profile tls run --rm --entrypoint sh \
    -v kg-crm-prod_certs:/out certbot -c \
    "cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem /out/fullchain.pem && \
     cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem  /out/privkey.pem"

echo "▸ nginx qayta ishga tushirilmoqda (HTTPS rejim)"
$COMPOSE up -d --force-recreate nginx
$COMPOSE --profile tls up -d certbot

sleep 3
echo
curl -fsS "https://${DOMAIN}/api/v1/health" && echo "  ✓ HTTPS ishlayapti" \
  || echo "  ! HTTPS javob bermadi — DNS va 443-portni tekshiring"
