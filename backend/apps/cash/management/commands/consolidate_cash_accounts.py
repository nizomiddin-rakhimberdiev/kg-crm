"""
Eski toʻrt qopni ikkitaga birlashtiradi: naqd va bank (2026-10-14).

**Nima uchun.** Filiallar avval toʻrtta qop bilan ochilgan — Terminal
va "Payme / Click" ham alohida. Mijoz toʻgʻri aytdi: bu pullar
bogʻchaning bitta bank hisobiga tushadi, va ular alohida turgani
uchun chiqimni bankdan qilmoqchi boʻlganda "bankda pul yoʻq" degan
xabar chiqardi. Yangi toʻlovlar endi bankka tushadi
(`cash.account_for_method`); bu buyruq ESKI qoldiqni koʻchiradi.

**Qanday.** Har bir eski qop uchun bitta **oʻtkazma** — ikki yangi
yozuv, bitta `transfer_group`. Hech bir eski yozuv tahrirlanmaydi va
oʻchirilmaydi (12-invariant): "terminal puli bankka oʻtdi" degan gap
haqiqatga ham mos, chunki terminal hisob-kitobi aynan shunday ishlaydi.
Qoldigʻi nolga tushgan qop oʻchirib qoʻyiladi (`is_active=False`),
tarixi esa joyida qoladi.

Manfiy eski qop — undan bank puli chiqarilgan degani; kamomad bankka
oʻtadi va bank qoldigʻi yetmasa ham rad etilmaydi, chunki bu tuzatish
(ADR-29).

**Xavfsizlik:** sukut boʻyicha dry-run. Takror ishga tushirish xavfsiz
— koʻchiriladigan narsa qolmagan boʻlsa, hech narsa yozilmaydi.

Ishlatish::

    python manage.py consolidate_cash_accounts                 # faqat koʻrsatadi
    python manage.py consolidate_cash_accounts --slug orientalkinderland
    python manage.py consolidate_cash_accounts --apply
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.cash import selectors
from apps.cash import services as cash
from apps.cash.models import CashAccount, CashAccountKind
from apps.core.tenancy import organization_context, platform_context

#: Endi oʻz qopi boʻlmaydigan usullar — ularning puli bankka tushadi.
RETIRED_METHODS: frozenset[str] = frozenset({"terminal", "online"})
RETIRED_KINDS: frozenset[str] = frozenset({CashAccountKind.TERMINAL, CashAccountKind.EWALLET})


def _som(value: Decimal) -> str:
    return f"{value:,.0f}".replace(",", " ")


class Command(BaseCommand):
    help = "Terminal va Payme/Click qoplarini bank hisobiga birlashtiradi (sukut: dry-run)."

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

        mode = "YOZILADI" if apply else "DRY-RUN — hech narsa yozilmaydi"
        self.stdout.write(f"Rejim: {mode}\n")

        moved_total = 0
        for org_id, slug in targets:
            with organization_context(org_id):
                moved_total += self._organization(slug, apply=apply)

        self.stdout.write(
            f"\nJami {moved_total} ta qop "
            + ("birlashtirildi." if apply else "birlashtiriladi (--apply bilan).")
        )

    def _organization(self, slug: str, *, apply: bool) -> int:
        moved = 0
        retired = CashAccount.objects.filter(is_active=True).select_related("branch")
        retired = [
            a for a in retired if a.kind in RETIRED_KINDS or a.handles_method in RETIRED_METHODS
        ]
        for old in retired:
            with transaction.atomic():
                bank = self._bank_for(old)
                balance = selectors.account_balance(account_id=old.id)
                self.stdout.write(
                    f"  {slug} · {old.branch.name} · «{old.name}»: {_som(balance)} soʻm"
                    f" → «{bank.name}»"
                )
                if apply:
                    text = f"«{old.name}» bank hisobiga birlashtirildi"
                    if balance > 0:
                        cash.transfer(source=old, target=bank, amount=balance, description=text)
                    elif balance < 0:
                        cash.transfer(
                            source=bank,
                            target=old,
                            amount=-balance,
                            description=text,
                            allow_negative=True,
                        )
                    old.is_active = False
                    old.save(update_fields=["is_active", "updated_at"])
            moved += 1
        return moved

    @staticmethod
    def _bank_for(old: CashAccount) -> CashAccount:
        bank = CashAccount.objects.filter(
            branch=old.branch, is_active=True, handles_method="bank_transfer"
        ).first()
        if bank is None:
            # Filialda bank qopi yoʻq — ochamiz (idempotent).
            cash.ensure_branch_accounts(branch=old.branch)
            bank = CashAccount.objects.get(
                branch=old.branch, is_active=True, handles_method="bank_transfer"
            )
        return bank
