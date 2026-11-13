#!/bin/sh
#
# certbot `--deploy-hook` — sertifikat YANGILANGANDAN keyin ishlaydi.
#
# certbot `/etc/letsencrypt/live/<domen>/` ga yozadi, nginx esa faqat
# ikki faylni alohida `certs` volume'idan oʻqiydi (`scripts/tls-setup.sh`
# — butun `letsencrypt` katalogi nginx'ga berilmaydi). Bu hook boʻlmasa
# yangilangan sertifikat nginx'ga hech qachon yetib bormaydi.
#
# `RENEWED_LINEAGE` ni certbot oʻzi beradi. nginx faylni sezib qayta
# yuklaydi (`deploy/nginx/entrypoint.sh`).
set -eu

OUT="${CERTS_OUT:-/out}"

# Avval vaqtinchalik nom, keyin `mv`: nginx yarim yozilgan kalitni
# oʻqib qolmasin.
cp "$RENEWED_LINEAGE/fullchain.pem" "$OUT/fullchain.pem.new"
cp "$RENEWED_LINEAGE/privkey.pem" "$OUT/privkey.pem.new"
mv "$OUT/fullchain.pem.new" "$OUT/fullchain.pem"
mv "$OUT/privkey.pem.new" "$OUT/privkey.pem"
echo "[certbot] yangi sertifikat nginx'ga koʻchirildi: $RENEWED_LINEAGE"
