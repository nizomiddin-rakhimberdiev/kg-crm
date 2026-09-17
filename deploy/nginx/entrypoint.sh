#!/bin/sh
#
# Sertifikat bor-yo'qligiga qarab sozlamani tanlaydi.
#
# Tovuq-tuxum muammosi: TLS uchun sertifikat kerak, sertifikat olish
# uchun esa ACME so'rovi 80-portdan kirishi kerak — ya'ni nginx
# ALLAQACHON ishlab turishi kerak. Agar sozlama har doim TLS talab
# qilsa, yangi serverda nginx umuman ko'tarilmaydi va birinchi deploy
# shu yerda to'xtaydi.
#
# Shuning uchun: sertifikat yo'q bo'lsa — HTTP rejim (ACME so'rovi
# o'tadi, sayt ishlaydi), paydo bo'lgach — TLS rejim.
set -e

CERT=/etc/nginx/certs/fullchain.pem
KEY=/etc/nginx/certs/privkey.pem
OUT=/etc/nginx/conf.d/default.conf

# Tasvirdagi standart sozlama bizniki bilan to'qnashmasin.
rm -f /etc/nginx/conf.d/default.conf

export DOMAIN="${DOMAIN:-_}"

# `www.<domen>` ham xizmat ko'rsatilsin — shu bilan birga bo'lishi
# SHART: `DJANGO_ALLOWED_HOSTS` allaqachon ikkalasini ham kutadi
# (.env.production.example), va nginx faqat bittasini bilsa, www
# orqali kelgan so'rov "no server_name match" bilan qaytardi.
#
# `DOMAIN=_` (haqiqiy domensiz lokal sinov) da www qo'shilmaydi —
# "www._" ma'nosiz nom bo'lardi.
if [ "$DOMAIN" != "_" ]; then
    export WWW_DOMAIN="www.${DOMAIN}"
else
    export WWW_DOMAIN="_"
fi

# shellcheck disable=SC2016  # envsubst AYNAN literal ${DOMAIN} ni kutadi
if [ -s "$CERT" ] && [ -s "$KEY" ]; then
    echo "[kg-crm] sertifikat topildi → HTTPS rejim ($DOMAIN, $WWW_DOMAIN)"
    envsubst '${DOMAIN} ${WWW_DOMAIN}' < /etc/nginx/kg-templates/tls.conf > "$OUT"
else
    echo "[kg-crm] sertifikat yo'q → HTTP rejim. TLS uchun: scripts/tls-setup.sh"
    envsubst '${DOMAIN} ${WWW_DOMAIN}' < /etc/nginx/kg-templates/http-only.conf > "$OUT"
fi
