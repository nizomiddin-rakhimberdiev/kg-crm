"""
Eski sukut stavkalarini ochiq qotirish (D6, Q10 davomi).

1-bosqichda `payroll.income_tax_rate` va `payroll.pension_rate` ning
SUKUT qiymati 12 % / 0,1 % dan 0 ga tushdi (Q10: soliq ushlashni bog'cha
ongli ravishda yoqishi kerak). Lekin sozlamaga hech qachon tegmagan va
shu sukut bilan ishlab kelgan bog'cha uchun bu jimgina o'zgarish:
keyingi oylik qoralamasida ushlanma yo'qolib, xodimga ortiqcha pul
chiqadi va soliq to'lanmay qoladi.

Bu buyruq aynan shunday tashkilotlarni topadi — sozlama ochiq
yozilmagan, lekin yakunlangan oylikda haqiqatan ushlanma bo'lgan — va
eski qiymatni OCHIQ yozadi. Xulq o'zgarmaydi; endi u tanlov sifatida
ko'rinadi va sozlamalar ekranida o'zgartirilishi mumkin.

Sukut bo'yicha dry-run; yozish uchun `--apply`. Har yozuv auditda.

    python manage.py pin_legacy_payroll_rates                 # hamma, dry-run
    python manage.py pin_legacy_payroll_rates --tenant slug   # bittasi
    python manage.py pin_legacy_payroll_rates --apply
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context

#: (sozlama, `PayrollItem` ustuni, 1-bosqichgacha bo'lgan sukut)
LEGACY = (
    ("payroll.income_tax_rate", "tax_income", 12),
    ("payroll.pension_rate", "tax_pension", 0.1),
)
ACTOR = "system:pin_legacy_payroll_rates"


class Command(BaseCommand):
    help = "Eski sukut oylik stavkalariga tayangan tashkilotlarda ularni ochiq yozadi."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--tenant", help="Faqat shu slug")
        parser.add_argument("--apply", action="store_true", help="Haqiqatan yozish")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.organizations.models import Organization

        with platform_context():
            queryset = Organization.objects.all()
            if options.get("tenant"):
                queryset = queryset.filter(slug=options["tenant"])
                if not queryset.exists():
                    raise CommandError(f"'{options['tenant']}' topilmadi.")
            orgs = list(queryset.order_by("slug"))

        planned = 0
        for organization in orgs:
            with organization_context(organization.id):
                changes = self._plan(organization)
                for key, value in changes:
                    planned += 1
                    self.stdout.write(f"  {organization.slug}: {key} = {value}")
                if changes and options["apply"]:
                    with transaction.atomic():
                        self._write(organization, changes)

        if planned == 0:
            self.stdout.write("Eski sukutga tayangan tashkilot yo'q — hech narsa qilinmaydi.")
        elif not options["apply"]:
            self.stdout.write(
                self.style.WARNING(f"\n[dry-run] {planned} ta qiymat. Yozish: --apply")
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"\n{planned} ta qiymat yozildi (auditda)."))

    def _plan(self, organization: Any) -> list[tuple[str, Any]]:
        from apps.payroll.models import PayrollItem, PayrollStatus
        from apps.settings_app.models import SystemSetting

        plan = []
        for key, column, legacy in LEGACY:
            if SystemSetting.objects.filter(key=key, branch__isnull=True).exists():
                continue  # bog'cha o'zi tanlagan — tegilmaydi
            withheld = PayrollItem.objects.filter(
                **{f"{column}__gt": 0},
                payroll_run__status__in=[PayrollStatus.FINALIZED, PayrollStatus.PAID],
            ).exists()
            if withheld:
                plan.append((key, legacy))
        return plan

    def _write(self, organization: Any, changes: list[tuple[str, Any]]) -> None:
        from apps.audit import services as audit
        from apps.settings_app.services import set_setting

        for key, value in changes:
            set_setting(organization=organization, key=key, value=value)
            audit.record(
                action="update",
                organization=organization,
                actor_email=ACTOR,
                entity_type="setting",
                changes={"key": key, "value": value, "reason": "D6: eski sukut ochiq yozildi"},
            )
