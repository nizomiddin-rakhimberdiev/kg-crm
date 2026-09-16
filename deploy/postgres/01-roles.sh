#!/bin/bash
#
# Uchta rol, uchta ish (docs/03 §6.3).
#
# Bu skript faqat BIR MARTA — baza volume'i birinchi marta yaratilganda —
# ishlaydi. Mavjud bazaga qo'lda qo'llash kerak (docs/deployment.md).
#
# Nega bitta rol yetmaydi:
#
#   $POSTGRES_USER   EGA. Migratsiyalar shu rol bilan bajariladi, chunki
#                    ular jadval yaratadi va siyosat qo'yadi.
#
#   kg_crm_app       ISH VAQTI. Ilova shu rol bilan ulanadi. U jadval
#                    egasi EMAS, ya'ni `ALTER TABLE ... NO FORCE ROW LEVEL
#                    SECURITY` yoki `DROP POLICY` qila olmaydi. Farq
#                    nazariy emas: ega huquqi bilan ishlaydigan ilovada
#                    bitta SQL in'ektsiyasi butun RLS qatlamini O'CHIRIB
#                    tashlashi mumkin.
#
#   kg_crm_backup    ZAXIRA, `BYPASSRLS` bilan. Busiz `pg_dump` FORCE RLS
#                    ostida qatorlarni KO'RMAYDI va jimgina BO'SH zaxira
#                    yozadi — zaxira bor deb o'ylab yurasiz, tiklash kuni
#                    esa ichida hech narsa yo'qligi ma'lum bo'ladi.
set -euo pipefail

: "${APP_DB_PASSWORD:?01-roles.sh: APP_DB_PASSWORD berilmagan}"
: "${BACKUP_DB_PASSWORD:?01-roles.sh: BACKUP_DB_PASSWORD berilmagan}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    CREATE ROLE kg_crm_app LOGIN PASSWORD '${APP_DB_PASSWORD}';
    CREATE ROLE kg_crm_backup LOGIN PASSWORD '${BACKUP_DB_PASSWORD}' BYPASSRLS;

    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO kg_crm_app, kg_crm_backup;
    GRANT USAGE ON SCHEMA public TO kg_crm_app, kg_crm_backup;

    -- Migratsiyalar hali ishlamagan, ya'ni jadvallar YO'Q. Shuning uchun
    -- huquqlar mavjudlariga emas, KELAJAKDAGILARGA beriladi — aks holda
    -- har bir yangi migratsiyadan keyin GRANT ni qo'lda takrorlash kerak
    -- bo'lardi va uni bir marta unutish ilovani ishdan chiqarardi.
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kg_crm_app;
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT USAGE, SELECT ON SEQUENCES TO kg_crm_app;

    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT SELECT ON TABLES TO kg_crm_backup;
    ALTER DEFAULT PRIVILEGES FOR ROLE "${POSTGRES_USER}" IN SCHEMA public
        GRANT SELECT ON SEQUENCES TO kg_crm_backup;
SQL

echo "[kg-crm] rollar yaratildi: kg_crm_app (cheklangan), kg_crm_backup (BYPASSRLS, faqat o'qish)"
