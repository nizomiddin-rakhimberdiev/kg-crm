"""
Bola kelmagan oylarga yozilgan fakturalarni bekor qiladi (audit, 2026-10-30).

Auditda prod'dagi `analiz` tenantida 131 ta shunday hujjat topildi:
toʻliq baza yozilib, ustiga −100% chegirma qoʻyilgan, natijada summa 0
va holati "toʻlangan". Kassaga tegmagan, lekin hisobotdagi yalpi baza
+176 950 000 ga, "qayta hisob" esa −84 985 000 ga sunʼiy oshgan.

Sababi tuzatildi (`children.is_billable_for`), bu buyruq esa allaqachon
yozilgan hujjatlarni tozalaydi — oʻchirmaydi, BEKOR qiladi: qarshi
yozuv bilan (3-invariant).

Sukut boʻyicha `--dry-run`: hech narsa oʻzgarmaydi, faqat roʻyxat
koʻrsatiladi.

    python manage.py void_pre_enrolment_invoices --slug analiz
    python manage.py void_pre_enrolment_invoices --slug analiz --apply
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.core.tenancy import organization_context, platform_context

REASON = "Bola bu oyda bogʻchada boʻlmagan (audit, 2026-10-30)"


class Command(BaseCommand):
    help = "Qabul sanasidan oldingi oylarga yozilgan fakturalarni bekor qiladi (dry-run sukut)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", required=True, help="Tashkilot slugʻi")
        parser.add_argument("--apply", action="store_true", help="Haqiqatan bekor qilish")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.children.services import is_billable_for
        from apps.finance import services
        from apps.finance.models import Invoice, InvoiceStatus
        from apps.organizations.models import Organization

        slug, apply_it = options["slug"], options["apply"]
        with platform_context():
            organization = Organization.objects.filter(slug=slug).first()
            if organization is None:
                raise CommandError(f"Tashkilot topilmadi: {slug}")

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{organization.name} ({slug})"))
        mode = self.style.ERROR("BEKOR QILISH") if apply_it else self.style.WARNING("dry-run")
        self.stdout.write(f"Rejim: {mode}")

        voided = skipped_paid = 0
        with organization_context(organization.id):
            rows = (
                Invoice.objects.exclude(status=InvoiceStatus.CANCELLED)
                .select_related("child")
                .order_by("child__last_name", "period_year", "period_month")
            )
            for invoice in rows:
                if is_billable_for(
                    invoice.child,
                    period_year=invoice.period_year,
                    period_month=invoice.period_month,
                ):
                    continue
                label = (
                    f"  {invoice.child.full_name} · "
                    f"{invoice.period_month:02d}.{invoice.period_year} · "
                    f"{invoice.number} · {invoice.amount_due}"
                )
                # Haqiqatan toʻlangan hujjat bu yerda bekor qilinmaydi:
                # u pul harakati bilan bogʻlangan va uni qaytarish —
                # alohida qaror.
                if invoice.amount_paid > 0:
                    skipped_paid += 1
                    self.stdout.write(self.style.WARNING(f"{label} — toʻlovi bor, tegilmadi"))
                    continue
                self.stdout.write(label)
                if apply_it:
                    services.cancel_invoice(invoice=invoice, reason=REASON)
                voided += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Bekor qilinadi: {voided} ta")
            if not apply_it
            else self.style.SUCCESS(f"Bekor qilindi: {voided} ta")
        )
        if skipped_paid:
            self.stdout.write(
                self.style.WARNING(f"Toʻlovi borligi uchun tegilmadi: {skipped_paid}")
            )
