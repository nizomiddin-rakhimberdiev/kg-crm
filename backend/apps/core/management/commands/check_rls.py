"""
RLS haqiqatan KUCHDA ekanini tekshiradi (docs/03 §6.3).

Nega alohida buyruq kerak: migratsiya "qo'llanilgan" deb belgilanishi
bilan Django uni boshqa ishga tushirmaydi. Agar migratsiya fayli
keyinroq tahrirlansa — yangi siyosat qo'shilsa yoki `FORCE` yoqilsa —
allaqachon migratsiya qilingan baza **eski holatda qoladi**, va buni
hech narsa aytmaydi.

Aynan shu holat shu loyihada sodir bo'ldi: dev bazasida siyosatlar bor
edi, lekin `FORCE` yo'q edi. Ilova jadval egasi sifatida ulanadi, egasi
esa RLS'ni sukut bo'yicha chetlab o'tadi — ya'ni "RLS bor" degan
ishonch bilan yashab, aslida hech qanday himoya bo'lmagan.

Testlar buni topa olmaydi: ular har safar toza bazada ishlaydi va u
yerda migratsiya to'liq bajariladi. Muammo faqat **mavjud** bazada
bo'ladi, ya'ni uni faqat mavjud bazani so'rab bilish mumkin.

Deploy tartibida `migrate` dan keyin ishlatiladi::

    python manage.py migrate
    python manage.py check_rls   # noldan farqli kod → deploy to'xtaydi
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import connection

from apps.core.rls import (
    AUTH_TABLES,
    DERIVED_TABLES,
    METADATA_TABLES,
    OPERATIONAL_TABLES,
    build_policy_sql,
)

REQUIRED_FUNCTIONS = ("app_current_org", "app_is_platform", "app_is_auth_lookup")


class Command(BaseCommand):
    help = "Postgres RLS siyosatlari kuchda ekanini tekshiradi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Topilgan kamchiliklarni tuzatadi (siyosatlarni qayta qo'yadi).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if connection.vendor != "postgresql":
            self.stdout.write(self.style.WARNING("Postgres emas — tekshiruv o'tkazib yuborildi."))
            return

        expected = {*OPERATIONAL_TABLES, *METADATA_TABLES, *DERIVED_TABLES, *AUTH_TABLES}
        problems: list[str] = []

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT proname FROM pg_proc WHERE proname = ANY(%s)", [list(REQUIRED_FUNCTIONS)]
            )
            found_functions = {row[0] for row in cursor.fetchall()}
            for name in REQUIRED_FUNCTIONS:
                if name not in found_functions:
                    problems.append(f"funksiya yo'q: {name}()")

            cursor.execute(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'r' AND n.nspname = 'public' AND c.relname = ANY(%s)
                """,
                [sorted(expected)],
            )
            state = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

            cursor.execute(
                "SELECT tablename FROM pg_policies WHERE policyname = 'tenant_isolation'"
            )
            with_policy = {row[0] for row in cursor.fetchall()}

        for table in sorted(expected):
            if table not in state:
                problems.append(f"jadval topilmadi: {table}")
                continue
            enabled, forced = state[table]
            if not enabled:
                problems.append(f"RLS yoqilmagan: {table}")
            if not forced:
                # Eng xavfli holat: siyosat bor, lekin egasi uni
                # chetlab o'tadi. Tashqaridan hamma narsa joyida
                # ko'rinadi.
                problems.append(f"FORCE yo'q (egasi chetlab o'tadi): {table}")
            if table not in with_policy:
                problems.append(f"siyosat yo'q: {table}")

        if not problems:
            self.stdout.write(
                self.style.SUCCESS(f"RLS kuchda: {len(expected)} ta jadval tekshirildi.")
            )
            return

        for problem in problems:
            self.stdout.write(self.style.ERROR(f"  ✗ {problem}"))

        if not options["fix"]:
            self.stdout.write("")
            self.stdout.write("Tuzatish: python manage.py check_rls --fix")
            raise SystemExit(1)

        self.stdout.write("")
        self.stdout.write("Siyosatlar qayta qo'yilmoqda…")
        with connection.cursor() as cursor:
            cursor.execute(build_policy_sql())
        self.stdout.write(
            self.style.SUCCESS("Tayyor. Qayta tekshiring: python manage.py check_rls")
        )
