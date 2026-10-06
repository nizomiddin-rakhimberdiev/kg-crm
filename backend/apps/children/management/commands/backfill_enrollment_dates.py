"""
Qabul sanasi yo'q bolalarga uni qo'yadi (PLAN 7.1).

    python manage.py backfill_enrollment_dates            # quruq rejim
    python manage.py backfill_enrollment_dates --apply
    python manage.py backfill_enrollment_dates --tenant paddington --apply

Nega kerak: "Yangi bola" formasida qabul sanasi maydoni yo'q edi, shuning
uchun u bo'sh qolardi va birinchi oy proporsional hisoblanmasdi — oyning
25-kunida kelgan bolaga ham to'liq oy yozilardi. Forma tuzatildi; bu
buyruq esa allaqachon kiritilgan bolalarni to'g'rilaydi.

**Faqat HISOB-FAKTURASI YO'Q bolalar.** Fakturasi bor bolaga sana
qo'yilsa ham hisob o'zgarmaydi (`_is_first_period` avvalgi faktura
borligini ko'radi), lekin ularga tegmaslik aniqroq: chiqarilgan hujjat
hujjat bo'lib qoladi va uni orqaga qarab qayta hisoblamaymiz.

Sana qayerdan: bolaning yaratilgan kuni (`created_at`) — bu taxmin,
lekin yagona bor ma'lumot. Shuning uchun buyruq har bir qatorni ko'rsatadi
va `--apply` siz hech narsa yozmaydi.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context


class Command(BaseCommand):
    help = "Set the enrolment date for children that have none (dry run unless --apply)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--apply", action="store_true", help="Write the changes.")
        parser.add_argument("--tenant", help="Organization slug; default: all.")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.children.models import Child
        from apps.finance.models import Invoice
        from apps.organizations.models import Organization

        apply = bool(options["apply"])
        with platform_context():
            organizations = Organization.objects.order_by("name")
            if options.get("tenant"):
                organizations = organizations.filter(slug=options["tenant"])
                if not organizations.exists():
                    raise CommandError(f"No organization with slug {options['tenant']!r}.")
            targets = list(organizations.values_list("id", "name"))

        total_set = total_skipped = 0
        for organization_id, name in targets:
            with organization_context(organization_id):
                missing = list(
                    Child.objects.filter(enrolled_on__isnull=True, archived_at__isnull=True)
                )
                if not missing:
                    continue
                self.stdout.write(f"\n{name}:")
                to_set: list[tuple[Any, Any]] = []
                for child in missing:
                    if Invoice.objects.filter(child=child).exists():
                        total_skipped += 1
                        self.stdout.write(f"  - {child.full_name}: fakturasi bor, tegilmaydi")
                        continue
                    to_set.append((child, child.created_at.date()))
                    self.stdout.write(f"  + {child.full_name}: {child.created_at.date()}")

                if apply and to_set:
                    with transaction.atomic():
                        for child, enrolled_on in to_set:
                            child.enrolled_on = enrolled_on
                            child.save(update_fields=["enrolled_on", "updated_at"])
                total_set += len(to_set)

        verb = "Yozildi" if apply else "Quruq rejim - hech narsa yozilmadi"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{verb}: {total_set} ta bolaga sana qo'yiladi, "
                f"{total_skipped} tasi fakturasi borligi uchun chetda."
            )
        )
