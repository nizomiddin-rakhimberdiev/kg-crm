#!/bin/sh
#
# Kunlik zaxira nusxa uchun cron qatorini o'rnatadi (PLAN 5.9).
#
# Nega skript: 2026-10-02 auditida ma'lum bo'ldiki, `backup.sh` va
# hujjat bor edi, lekin jadval O'RNATILMAGAN va `backups/` bo'm-bo'sh —
# ya'ni hech qachon zaxira olinmagan. Qo'lda yoziladigan qator unutiladi;
# bitta buyruq — yo'q.
#
#   ./scripts/install-backup-cron.sh          # nima qilinishini ko'rsatadi
#   ./scripts/install-backup-cron.sh --apply  # crontab'ga yozadi
#
# Takroriy ishga tushirish xavfsiz: qator allaqachon bo'lsa, hech narsa
# qo'shilmaydi. Batafsil: docs/ops/backup.md §3.
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${BACKUP_LOG:-/var/log/kg-crm-backup.log}"
# 02:30 — tungi Celery vazifalari orasida (hisob-faktura 02:00, muddati
# o'tganlar 03:00): zaxira yarim bajarilgan hisob-kitobni ushlamaydi.
LINE="30 2 * * *  cd $ROOT && ./scripts/backup.sh >> $LOG 2>&1"
MARK="scripts/backup.sh"

CURRENT="$(crontab -l 2>/dev/null || true)"

if printf '%s\n' "$CURRENT" | grep -qF "$MARK"; then
    echo "Allaqachon o'rnatilgan:"
    printf '%s\n' "$CURRENT" | grep -F "$MARK"
    exit 0
fi

if [ "${1:-}" != "--apply" ]; then
    echo "[dry-run] crontab'ga qo'shiladigan qator:"
    echo "  $LINE"
    echo "Yozish uchun: $0 --apply"
    exit 0
fi

{ [ -n "$CURRENT" ] && printf '%s\n' "$CURRENT"; printf '%s\n' "$LINE"; } | crontab -
echo "O'rnatildi:"
echo "  $LINE"
echo "Ertaga tekshiring: ./scripts/backup-check.sh"
