"""
Mavjud avanslarni ochiq hisob-fakturalarga qo'llaydi (PLAN 1.2, Q1).

**Nega migratsiya emas.** `finance.0009` mavjud `payment.invoice`
bog'lanishini taqsimot jadvaliga ko'chiradi va bu birorta raqamni
o'zgartirmaydi. Bu buyruq esa BOSHQA ish: u hech qaysi hujjatga
biriktirilmagan pulni — avansni — ochiq fakturalarga yotqizadi, ya'ni
ekrandagi raqamlarni o'zgartiradi. Mijozning moliyaviy ma'lumotini
o'zgartiradigan ish esa avtomatik ishga tushmasligi va egasining ko'zi
oldida bajarilishi kerak.

Auditdagi holat: Ibragimov Robiya 830 000 + 540 000 to'lagan, lekin
ikkala to'lov ham "— avans —" bo'lib yozilgan va sentabr fakturasi
"To'lanmagan" bo'lib turibdi. Bu buyruq shu pulni fakturaga yotqizadi.

Ishlatish::

    # Avval KO'RISH — hech narsa yozilmaydi
    python manage.py apply_open_credits --tenant oriental-kinderland --dry-run

    # Ro'yxat to'g'ri bo'lsa, qo'llash
    python manage.py apply_open_credits --tenant oriental-kinderland

`--tenant` MAJBURIY: bir buyruq bilan hamma bog'chaning pulini
qimirlatib yuborish — qaytarib bo'lmaydigan turdagi xato.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context
from apps.finance import services
from apps.finance.models import Invoice
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Taqsimlanmagan to'lovlarni (avanslarni) ochiq hisob-fakturalarga qo'llaydi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--tenant", required=True, help="Tashkilot slug'i")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Faqat ko'rsatadi, hech narsa yozmaydi",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        slug: str = options["tenant"]
        dry_run: bool = options["dry_run"]

        with platform_context():
            organization = Organization.objects.filter(slug=slug).first()
        if organization is None:
            raise CommandError(f"'{slug}' bilan tashkilot topilmadi.")

        self.stdout.write(f"Tashkilot: {organization.name} ({slug})")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — hech narsa yozilmaydi"))

        applied_total = Decimal("0")
        touched = 0

        with organization_context(organization.id):
            # Avansi bor bolalar — ochiq hujjati borlari bilan birga.
            open_invoices = (
                Invoice.objects.filter(status__in=services.OPEN_INVOICE_STATUSES)
                .select_related("child")
                .order_by("child_id", "due_date", "number")
            )
            by_child: dict[Any, list[Invoice]] = {}
            for invoice in open_invoices:
                by_child.setdefault(invoice.child_id, []).append(invoice)

            for invoices in by_child.values():
                child = invoices[0].child
                advance = services.child_advance(child)
                if advance <= 0:
                    continue

                remaining = advance
                plan: list[tuple[Invoice, Decimal]] = []
                for invoice in invoices:
                    if remaining <= 0:
                        break
                    outstanding = invoice.amount_due - invoice.amount_paid
                    if outstanding <= 0:
                        continue
                    share = min(remaining, outstanding)
                    plan.append((invoice, share))
                    remaining -= share

                if not plan:
                    continue

                touched += 1
                self.stdout.write(f"\n  {child.full_name} — avans {advance:,.2f}")
                for invoice, share in plan:
                    self.stdout.write(f"    → {invoice.number}: {share:,.2f}")
                    applied_total += share

                if not dry_run:
                    with transaction.atomic():
                        for invoice, _share in plan:
                            services.apply_advance_to_invoice(invoice=invoice)

        self.stdout.write("")
        verb = "qo'llanadi" if dry_run else "qo'llandi"
        self.stdout.write(
            self.style.SUCCESS(f"{touched} ta bola, jami {applied_total:,.2f} so'm {verb}.")
        )
        if dry_run and touched:
            self.stdout.write("Haqiqatan qo'llash uchun `--dry-run` siz qayta ishga tushiring.")
