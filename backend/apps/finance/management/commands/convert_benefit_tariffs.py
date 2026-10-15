"""
"Imtiyoz-tarif"ni haqiqiy imtiyozga aylantiradi (Bosqich 12.2).

**Nima uchun.** Bog'cha imtiyozlarni tarif qilib kiritgan — "KAM
TA`MINLANGANLAR — 0 so'm", "XODIMLAR FARZANDLARI — 1 525 000". Summa to'g'ri,
lekin sababi yo'q, kim bergani yo'q va "Imtiyozlar" hisobotida ko'rinmaydi —
brifdagi "toifa faqat rang bilan belgilanadi" muammosining tizimdagi shakli.

**Nima qiladi**, `--tariff` dagi har bir faol bolaga:

* tarifini `--to-tariff` (asosiy narx) ga o'tkazadi;
* unga `--kind` turidagi imtiyoz yozadi — `--reason` bilan, `--from` sanasidan.

Bola to'laydigan summa odatda o'zgarmaydi (1 525 000 = 3 050 000 − 50%) —
endi u SABABI bilan turadi. Summa farq qilsa, buyruq buni ko'rsatadi:
odam qaror qilsin.

Sukut bo'yicha dry-run. Takror ishga tushirish xavfsiz: imtiyozi bor bola
qayta o'tkazilmaydi.

Ishlatish::

    python manage.py convert_benefit_tariffs --slug orientalkinderland \\
        --tariff "XODIMLAR FARZANDLARI" --to-tariff "V.I.P" \\
        --kind staff_child --reason "Xodim farzandi" --from 2026-11-01
    # ... va o'sha buyruq --apply bilan
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.tenancy import organization_context, platform_context
from apps.finance.charges import som

ALLOWED_KINDS = ("staff_child", "low_income", "full")


class Command(BaseCommand):
    help = "Imtiyoz-tarifdagi bolalarni asosiy tarif + turi bor imtiyozga o'tkazadi (dry-run)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", help="Faqat shu tashkilot (sukut: hammasi).")
        parser.add_argument("--tariff", required=True, help="Imtiyoz-tarif nomi (aniq).")
        parser.add_argument("--to-tariff", required=True, help="Asosiy tarif nomi (aniq).")
        parser.add_argument("--kind", required=True, help=" | ".join(ALLOWED_KINDS))
        parser.add_argument("--reason", required=True, help="Imtiyoz sababi.")
        parser.add_argument("--from", dest="valid_from", help="Boshlanish sanasi (YYYY-MM-DD).")
        parser.add_argument("--apply", action="store_true", help="Haqiqatan yozish.")

    def handle(self, *args: Any, **options: Any) -> None:
        if options["kind"] not in ALLOWED_KINDS:
            raise CommandError(f"--kind: {', '.join(ALLOWED_KINDS)} dan biri bo'lishi kerak.")
        reason = options["reason"].strip()
        if not reason:
            raise CommandError("--reason bo'sh bo'lmasin.")
        valid_from = (
            date.fromisoformat(options["valid_from"])
            if options["valid_from"]
            else date.today().replace(day=1)
        )
        from apps.organizations.models import Organization

        with platform_context():
            orgs = Organization.objects.order_by("slug")
            if options["slug"]:
                orgs = orgs.filter(slug=options["slug"])
                if not orgs.exists():
                    raise CommandError(f"Tashkilot topilmadi: {options['slug']}")
            targets = list(orgs.values_list("id", "slug"))

        apply: bool = options["apply"]
        self.stdout.write(
            "Rejim: " + ("YOZILADI" if apply else "DRY-RUN — hech narsa yozilmaydi") + "\n"
        )
        moved = 0
        for org_id, slug in targets:
            with organization_context(org_id), transaction.atomic():
                moved += self._organization(slug, options, reason, valid_from, apply=apply)
        self.stdout.write(
            f"\n{moved} ta bola " + ("oʻtkazildi." if apply else "oʻtkaziladi (--apply bilan).")
        )

    def _organization(
        self, slug: str, options: dict[str, Any], reason: str, valid_from: date, *, apply: bool
    ) -> int:
        from apps.children.models import Child
        from apps.finance.models import Discount, DiscountType, TariffPlan
        from apps.finance.services import apply_discount

        source = TariffPlan.objects.filter(name=options["tariff"], is_active=True).first()
        target = TariffPlan.objects.filter(name=options["to_tariff"], is_active=True).first()
        if source is None or target is None:
            return 0

        moved = 0
        children = Child.objects.filter(tariff=source, is_active=True, archived_at__isnull=True)
        for child in children.order_by("last_name", "first_name"):
            if Discount.objects.filter(child=child, is_active=True, kind=options["kind"]).exists():
                continue
            probe = Discount(
                child=child,
                branch=child.branch,
                kind=options["kind"],
                discount_type=DiscountType.PERCENT,
            )
            after, _ = apply_discount(target.amount, probe)
            note = "" if after == source.amount else f" ⚠ summa {som(source.amount)} → {som(after)}"
            self.stdout.write(
                f"  {slug} · {child.full_name}: «{source.name}» → «{target.name}» + "
                f"{options['kind']}{note}"
            )
            if apply:
                child.tariff = target
                child.save(update_fields=["tariff", "updated_at"])
                Discount.objects.create(
                    organization=child.organization,
                    branch=child.branch,
                    child=child,
                    kind=options["kind"],
                    discount_type=DiscountType.PERCENT,
                    value=0,
                    reason=reason[:255],
                    valid_from=valid_from,
                )
            moved += 1
        return moved
