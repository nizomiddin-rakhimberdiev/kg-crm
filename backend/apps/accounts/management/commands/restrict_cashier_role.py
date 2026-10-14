"""
Mavjud tashkilotlardagi "Kassir" tizim rolini yangi qoidaga keltiradi (ADR-30).

**Nima uchun.** Mijoz: *"kassir hammasini koʻrib turishi bu xato — unga
faqat oʻzi qabul qilgan pullar koʻrinsin; chiqimlar, umumiy tushum,
oylik maosh va sof natija koʻrinishi kerak emas"*. Yangi tashkilotlar
kassir rolini shunday oladi (`ROLE_MATRIX`, `OWN_PAYMENTS_ROLES`), lekin
rollar har bir tashkilotda maʼlumot — ular oʻz-oʻzidan oʻzgarmaydi.

**Nima qiladi**, faqat `code="cashier"` tizim rolida:

* `payments_own_only = True` — jurnal, kunlik hisobot va kvitansiyada
  faqat oʻzi qabul qilgan toʻlovlar;
* `dashboard.*`, `expenses.*`, `reports.*` ruxsatlarini olib tashlaydi.

`payments.*` ga tegmaydi — toʻlov doskasi kassirning asosiy ishi.
Boshqa rollarga — direktor, menejer, bogʻcha oʻzi yasagan rollar —
tegmaydi.

**Xavfsizlik:** sukut boʻyicha dry-run; takror ishga tushirish xavfsiz.

Ishlatish::

    python manage.py restrict_cashier_role                  # faqat koʻrsatadi
    python manage.py restrict_cashier_role --slug orientalkinderland
    python manage.py restrict_cashier_role --apply
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Role, RolePermission
from apps.core.tenancy import organization_context, platform_context

CASHIER = "cashier"
#: Kassirdan olinadigan modullar — umumiy pul manzarasi.
HIDDEN_MODULES: frozenset[str] = frozenset({"dashboard", "expenses", "reports"})


class Command(BaseCommand):
    help = "Kassir rolini 'faqat oʻz toʻlovlari' qoidasiga keltiradi (sukut: dry-run)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", help="Faqat shu tashkilot (sukut: hammasi).")
        parser.add_argument(
            "--apply", action="store_true", help="Haqiqatan yozish. Usiz — faqat hisobot."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        apply: bool = options["apply"]
        from apps.organizations.models import Organization

        with platform_context():
            orgs = Organization.objects.order_by("slug")
            if options["slug"]:
                orgs = orgs.filter(slug=options["slug"])
                if not orgs.exists():
                    raise CommandError(f"Tashkilot topilmadi: {options['slug']}")
            targets = list(orgs.values_list("id", "slug"))

        self.stdout.write(
            "Rejim: " + ("YOZILADI" if apply else "DRY-RUN — hech narsa yozilmaydi") + "\n"
        )
        changed = 0
        for org_id, slug in targets:
            with organization_context(org_id), transaction.atomic():
                changed += self._organization(slug, apply=apply)

        self.stdout.write(
            f"\n{changed} ta rol "
            + ("oʻzgartirildi." if apply else "oʻzgartiriladi (--apply bilan).")
        )

    def _organization(self, slug: str, *, apply: bool) -> int:
        changed = 0
        for role in Role.objects.filter(code=CASHIER, is_system=True):
            grants = RolePermission.objects.filter(role=role).select_related("permission")
            drop = [rp for rp in grants if rp.permission.module in HIDDEN_MODULES]
            if role.payments_own_only and not drop:
                continue
            codes = ", ".join(sorted(rp.permission.code for rp in drop)) or "—"
            flag = "" if role.payments_own_only else " · faqat oʻz toʻlovlari: yoqiladi"
            self.stdout.write(f"  {slug} · «{role.name}»: olib tashlanadi: {codes}{flag}")
            if apply:
                RolePermission.objects.filter(id__in=[rp.id for rp in drop]).delete()
                if not role.payments_own_only:
                    role.payments_own_only = True
                    role.save(update_fields=["payments_own_only", "updated_at"])
            changed += 1
        return changed
