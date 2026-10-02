#!/usr/bin/env bash
#
# Zaxira nusxa HAQIQATAN olinayotganini tekshiradi (PLAN 5.9).
#
# Nega alohida skript. `scripts/backup.sh` yaxshi ishlaydi va o'zini
# tekshiradi ham — lekin u ISHGA TUSHIRILGAN bo'lishi kerak. Audit
# paytida aniqlandi: skript va hujjat bor, serverda cron esa YO'Q,
# ya'ni birorta zaxira nusxa olinmagan. Bu holat tashqaridan ko'rinmaydi:
# "backup bor" degan hujjat bilan "backup olinayapti" degan fakt
# o'rtasidagi farqni faqat fayllarga qarab bilish mumkin.
#
# Shuning uchun bu skript ikki narsani ayta oladi:
#
#   * eng yangi nusxa qancha vaqt oldin olingan;
#   * u ishonchli hajmdami.
#
# Monitoringga ulash uchun: nol bo'lmagan chiqish kodi = muammo.
#
# Ishlatish:
#   ./scripts/backup-check.sh                 # sukut: ./backups, 48 soat
#   ./scripts/backup-check.sh --dir /mnt/nas --max-age-hours 24

set -euo pipefail

DIR="./backups"
MAX_AGE_HOURS=48
MIN_BYTES=$((50 * 1024))

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir) DIR="$2"; shift 2 ;;
        --max-age-hours) MAX_AGE_HOURS="$2"; shift 2 ;;
        --min-bytes) MIN_BYTES="$2"; shift 2 ;;
        *) echo "Noma'lum argument: $1" >&2; exit 2 ;;
    esac
done

die() { echo "ZAXIRA MUAMMOSI: $*" >&2; exit 1; }

[[ -d "$DIR" ]] || die "katalog yo'q: $DIR — zaxira nusxa hech qachon olinmagan"

# Eng yangi dump (shifrlangan yoki shifrlanmagan).
newest="$(find "$DIR" -maxdepth 1 -type f \( -name 'kg-crm-*.dump' -o -name 'kg-crm-*.dump.enc' \) \
    -exec stat -f '%m %N' {} + 2>/dev/null || find "$DIR" -maxdepth 1 -type f \
    \( -name 'kg-crm-*.dump' -o -name 'kg-crm-*.dump.enc' \) -printf '%T@ %p\n' 2>/dev/null)"
[[ -n "$newest" ]] || die "$DIR ichida bitta ham dump yo'q"

line="$(echo "$newest" | sort -rn | head -1)"
mtime="${line%% *}"
file="${line#* }"
mtime="${mtime%%.*}"

now="$(date +%s)"
age_hours=$(( (now - mtime) / 3600 ))
size="$(wc -c < "$file" | tr -d ' ')"

echo "Eng yangi nusxa: $file"
echo "Yoshi:           ${age_hours} soat"
echo "Hajmi:           ${size} bayt"

(( age_hours <= MAX_AGE_HOURS )) \
    || die "oxirgi nusxa ${age_hours} soat oldin olingan (chegara ${MAX_AGE_HOURS})"
(( size >= MIN_BYTES )) \
    || die "fayl juda kichik (${size} bayt) — bo'sh dump bo'lishi mumkin"

echo "Zaxira nusxa joyida."
