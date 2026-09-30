"""
Kassa servislari (docs/03 §13a, ADR-17).

Bu modul bitta va'da beradi: **pul harakat qilgan har bir joyda yozuv
qoladi.** Shuning uchun `post_movement()` ni chaqirish moliya, chiqim va
oylik modullari uchun majburiy — ular bir-birining modellarini emas,
shu servisni chaqiradi (1-invariant).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.cash.models import (
    CashAccount,
    CashAccountKind,
    CashMovement,
    MovementDirection,
    MovementSource,
)
from apps.core.exceptions import BusinessRuleViolation

__all__ = [
    "DEFAULT_ACCOUNTS",
    "ensure_branch_accounts",
    "account_for_method",
    "post_movement",
    "reverse_movements_for",
    "transfer",
]


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


# Filial ochilganda shu to'rttasi yaratiladi — to'lov usullariga
# bir-bir mos (docs/03 §13.5). Nomlar o'zbekcha va bog'cha ularni
# o'zgartira oladi; `kind` va `handles_method` esa kod uchun.
DEFAULT_ACCOUNTS: tuple[tuple[str, str, str], ...] = (
    ("Naqd kassa", CashAccountKind.CASH, "cash"),
    ("Terminal", CashAccountKind.TERMINAL, "terminal"),
    ("Bank hisobi", CashAccountKind.BANK, "bank_transfer"),
    ("Payme / Click", CashAccountKind.EWALLET, "online"),
)


@transaction.atomic
def ensure_branch_accounts(*, branch: Any) -> list[CashAccount]:
    """
    Filialda to'rtta sukut qopni ta'minlaydi — idempotent.

    Filial yaratilganda chaqiriladi, lekin har safar chaqirilishi ham
    xavfsiz: mavjud qop qayta yaratilmaydi va qayta nomlanmaydi.
    Bog'cha "Naqd kassa" ni "Kassa №1" deb o'zgartirgan bo'lsa, u
    o'zgarishicha qoladi — biz faqat YO'Q qopni qo'shamiz.
    """
    existing = {
        account.handles_method: account
        for account in CashAccount.objects.filter(branch=branch, is_active=True)
        if account.handles_method
    }
    created: list[CashAccount] = []
    for name, kind, method in DEFAULT_ACCOUNTS:
        if method in existing:
            continue
        created.append(
            CashAccount.objects.create(
                organization=branch.organization,
                branch=branch,
                name=name,
                kind=kind,
                handles_method=method,
            )
        )
    return created


def account_for_method(*, branch: Any, method: str) -> CashAccount:
    """
    To'lov usuliga mos qop.

    Mos qop topilmasa naqd kassaga tushadi — va bu ATAYLAB xato emas:
    sozlama kamchiligi tufayli kassirning qo'lidagi puldan voz kechish
    noto'g'ri nosozlik. Topilmagani javobda ko'rinadi, lekin to'lov
    qabul qilinadi.
    """
    account = CashAccount.objects.filter(
        branch=branch, is_active=True, handles_method=method
    ).first()
    if account is not None:
        return account

    fallback = CashAccount.objects.filter(
        branch=branch, is_active=True, kind=CashAccountKind.CASH
    ).first()
    if fallback is not None:
        return fallback

    # Filialda umuman qop yo'q — birinchi marta ochamiz va qaytadan qidiramiz.
    ensure_branch_accounts(branch=branch)
    account = CashAccount.objects.filter(
        branch=branch, is_active=True, handles_method=method
    ).first()
    if account is None:  # pragma: no cover — `ensure_branch_accounts` kafolati
        raise BusinessRuleViolation(gettext("Filialda kassa hisobi topilmadi."))
    return account


def post_movement(
    *,
    account: CashAccount,
    direction: str,
    amount: Decimal,
    source_type: str,
    source_id: Any = None,
    description: str = "",
    occurred_at: Any = None,
    created_by: Any = None,
    transfer_group: Any = None,
) -> CashMovement:
    """
    Kassa jurnaliga bitta yozuv qo'shadi.

    Chaqiruvchi uni O'ZI ochgan tranzaksiya ichida chaqirishi kerak —
    hujjat va uning pul harakati bo'linmas bo'lishi shart.
    """
    amount = _money(amount)
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Summa musbat bo'lishi kerak."))

    return CashMovement.objects.create(
        organization=account.organization,
        branch=account.branch,
        cash_account=account,
        direction=direction,
        amount=amount,
        source_type=source_type,
        source_id=source_id,
        transfer_group=transfer_group,
        occurred_at=occurred_at or timezone.now(),
        description=description[:255],
        created_by=created_by,
    )


def reverse_movements_for(
    *,
    source_type: str,
    source_id: Any,
    description: str = "",
    created_by: Any = None,
) -> list[CashMovement]:
    """
    Hujjatning barcha harakatlarini QARSHI yozuv bilan bekor qiladi.

    Yozuvni o'chirmaydi — teskari yo'nalishdagi yangisini qo'shadi.
    Shunda jurnal "pul kirdi, keyin qaytarildi" deb ko'rsatadi, "hech
    narsa bo'lmagan" emas. Bu `reverse_payment()` dagi mantiq bilan
    aynan bir xil (D3).
    """
    opposite = {
        MovementDirection.IN: MovementDirection.OUT,
        MovementDirection.OUT: MovementDirection.IN,
    }
    reversals: list[CashMovement] = []
    for movement in CashMovement.objects.filter(
        source_type=source_type, source_id=source_id
    ).select_related("cash_account"):
        # Allaqachon qaytarilganni ikkinchi marta qaytarmaymiz.
        if movement.description.startswith("↩"):
            continue
        reversals.append(
            post_movement(
                account=movement.cash_account,
                direction=opposite[MovementDirection(movement.direction)],
                amount=movement.amount,
                source_type=source_type,
                source_id=source_id,
                description=f"↩ {description or gettext('qaytarildi')}",
                created_by=created_by,
            )
        )
    return reversals


@transaction.atomic
def transfer(
    *,
    source: CashAccount,
    target: CashAccount,
    amount: Decimal,
    description: str = "",
    occurred_at: Any = None,
    created_by: Any = None,
) -> tuple[CashMovement, CashMovement]:
    """
    Qoplar orasida pul ko'chirish — kun oxirida naqdni bankka topshirish
    yoki terminal hisob-kitobi.

    Ikkita yozuv, bitta `transfer_group`: biridan chiqadi, ikkinchisiga
    kiradi. JAMI o'zgarmaydi — o'tkazma pul topmaydi va yo'qotmaydi.
    """
    if source.pk == target.pk:
        raise BusinessRuleViolation(gettext("Bir qopdan o'ziga o'tkazib bo'lmaydi."))
    if source.organization_id != target.organization_id:
        raise BusinessRuleViolation(gettext("Qoplar boshqa tashkilotga tegishli."))

    group = uuid.uuid4()
    when = occurred_at or timezone.now()
    text = description or gettext("Qoplar orasida o'tkazma")
    out = post_movement(
        account=source,
        direction=MovementDirection.OUT,
        amount=amount,
        source_type=MovementSource.TRANSFER,
        description=text,
        occurred_at=when,
        created_by=created_by,
        transfer_group=group,
    )
    into = post_movement(
        account=target,
        direction=MovementDirection.IN,
        amount=amount,
        source_type=MovementSource.TRANSFER,
        description=text,
        occurred_at=when,
        created_by=created_by,
        transfer_group=group,
    )
    return out, into
