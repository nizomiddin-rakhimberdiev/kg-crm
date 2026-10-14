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


def _som(value: Decimal) -> str:
    """Xabardagi summa — "6 000 000" koʻrinishida (ingichka boʻsh joy emas)."""
    return f"{value:,.0f}".replace(",", " ")


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


# Filial ochilganda shu IKKITASI yaratiladi (mijoz so'rovi, 2026-10-14).
#
# Avval to'rtta edi — har bir to'lov usuliga bittadan. Bu usul bilan
# qopni chalkashtirgan edi: terminal, o'tkazma va Payme/Click orqali
# kelgan pul bog'chaning BITTA bank hisobiga tushadi, va ular uchun
# alohida qop chiqimni "bankda pul yo'q" deb to'xtatardi, holbuki pul
# bankda turibdi. Usul endi faqat to'lovning o'zida — hisobot uchun.
#
# Nomlar o'zbekcha va bog'cha ularni o'zgartira oladi; `kind` va
# `handles_method` esa kod uchun.
DEFAULT_ACCOUNTS: tuple[tuple[str, str, str], ...] = (
    ("Naqd kassa", CashAccountKind.CASH, "cash"),
    ("Bank hisobi", CashAccountKind.BANK, "bank_transfer"),
)

# To'lov usuli → qaysi qop uni qabul qiladi (`handles_method` qiymati).
# Naqd qo'lga tushadi; qolgan hammasi bankka. Ro'yxatda yo'q usul —
# yangi qo'shilgan bo'lsa ham — bankka boradi: naqd bo'lmagan pul
# kassaga tushmaydi.
_POT_FOR_METHOD: dict[str, str] = {"cash": "cash"}
_BANK_POT = "bank_transfer"


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
    To'lov usuliga mos qop: naqd — kassaga; terminal, o'tkazma va
    Payme/Click — bank hisobiga. Usulning o'zi to'lovda qoladi.

    Mos qop topilmasa naqd kassaga tushadi — va bu ATAYLAB xato emas:
    sozlama kamchiligi tufayli kassirning qo'lidagi puldan voz kechish
    noto'g'ri nosozlik. Topilmagani javobda ko'rinadi, lekin to'lov
    qabul qilinadi.
    """
    pot = _POT_FOR_METHOD.get(method, _BANK_POT)
    account = CashAccount.objects.filter(branch=branch, is_active=True, handles_method=pot).first()
    if account is not None:
        return account

    fallback = CashAccount.objects.filter(
        branch=branch, is_active=True, kind=CashAccountKind.CASH
    ).first()
    if fallback is not None:
        return fallback

    # Filialda umuman qop yo'q — birinchi marta ochamiz va qaytadan qidiramiz.
    ensure_branch_accounts(branch=branch)
    account = CashAccount.objects.filter(branch=branch, is_active=True, handles_method=pot).first()
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
    allow_negative: bool = False,
) -> CashMovement:
    """
    Kassa jurnaliga bitta yozuv qo'shadi.

    Chaqiruvchi uni O'ZI ochgan tranzaksiya ichida chaqirishi kerak —
    hujjat va uning pul harakati bo'linmas bo'lishi shart.

    **Qopda yo'q pul chiqmaydi** (ADR-29). Jonli bog'chada oylik
    "to'langan" deb belgilangandan keyin qoldiq −6 752 500 ga tushib
    qoldi: tizim 12 mln ni 6 mln turgan kassadan jimgina chiqarib
    yubordi. Manfiy qoldiq hech qanday haqiqatni anglatmaydi — u
    "kassaga tushmagan pul bor" degani, ya'ni YETISHMAYOTGAN YOZUV
    bor. Shuning uchun chiqim to'xtaydi va nima yetishmayotganini
    aytadi.

    `allow_negative=True` — foydalanuvchi buni ko'rib turib
    tasdiqlaganda (egasining o'z puli, yozilmagan tushum) va
    TUZATISHLARDA: qaytarilgan to'lovning qarshi yozuvi qopni
    manfiyga tushirishi mumkin, lekin uni to'sish jurnalni yolg'on
    holatda qoldirardi.
    """
    amount = _money(amount)
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Summa musbat boʻlishi kerak."))

    if direction == MovementDirection.OUT and not allow_negative:
        from apps.cash import selectors as cash_selectors

        balance = cash_selectors.account_balance(account_id=account.id)
        if amount > balance:
            raise BusinessRuleViolation(
                gettext(
                    "«{account}» da {balance} soʻm bor, {amount} soʻm chiqmoqda — "
                    "{short} soʻm yetishmaydi. Kassaga tushmagan pul boʻlsa, avval "
                    "oʻsha tushumni yozing yoki boshqa qopni tanlang."
                ).format(
                    account=account.name,
                    balance=_som(balance),
                    amount=_som(amount),
                    short=_som(amount - balance),
                )
            )

    movement = CashMovement.objects.create(
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
    # Tushum va kassa qoldig'i dashboardda — kesh eskirdi.
    from apps.reports.services import invalidate_dashboard_on_commit

    invalidate_dashboard_on_commit(organization_id=account.organization_id)
    return movement


def reverse_movements_for(
    *,
    source_type: str,
    source_id: Any,
    description: str = "",
    created_by: Any = None,
) -> list[CashMovement]:
    """
    Hujjatning qopdagi izini QARSHI yozuv bilan nolga keltiradi.

    Yozuvni o'chirmaydi — teskari yo'nalishdagi yangisini qo'shadi.
    Shunda jurnal "pul kirdi, keyin qaytarildi" deb ko'rsatadi, "hech
    narsa bo'lmagan" emas (D3).

    **Har bir qop bo'yicha SOF qoldiq qaytariladi, yozuvlar sanab emas.**
    Ilgari funksiya har bir yozuvni alohida qaytarib, faqat "↩" bilan
    boshlanganini o'tkazib yuborardi — ya'ni allaqachon qaytarilgan ASL
    yozuvni ikkinchi chaqiruvda YANA qaytarardi. Bir martalik
    chaqiruvchilar (to'lovni qaytarish, oylikni qayta ochish) buni hech
    qachon sezmasdi; chiqimni ikki marta tahrirlash esa kassaga yo'q
    pulni qo'shardi. Sof qoldiq bo'yicha ishlash funksiyani idempotent
    qiladi: hujjatning izi allaqachon nol bo'lsa, hech narsa yozilmaydi.
    """
    net: dict[Any, Decimal] = {}
    accounts: dict[Any, CashAccount] = {}
    for movement in CashMovement.objects.filter(
        source_type=source_type, source_id=source_id
    ).select_related("cash_account"):
        sign = 1 if movement.direction == MovementDirection.IN else -1
        net[movement.cash_account_id] = net.get(movement.cash_account_id, Decimal("0")) + (
            sign * movement.amount
        )
        accounts[movement.cash_account_id] = movement.cash_account

    reversals: list[CashMovement] = []
    for account_id, amount in net.items():
        if amount == 0:
            continue
        reversals.append(
            post_movement(
                account=accounts[account_id],
                # Qopga sof kirgan bo'lsa — chiqaramiz, sof chiqqan bo'lsa — qaytaramiz.
                direction=MovementDirection.OUT if amount > 0 else MovementDirection.IN,
                amount=abs(amount),
                source_type=source_type,
                source_id=source_id,
                description=f"↩ {description or gettext('qaytarildi')}",
                created_by=created_by,
                # Tuzatish hech qachon to'xtatilmaydi (ADR-29): asl pul
                # allaqachon qimirlagan, qarshi yozuvni to'sish jurnalni
                # yolg'on holatda qoldirardi.
                allow_negative=True,
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
    allow_negative: bool = False,
) -> tuple[CashMovement, CashMovement]:
    """
    Qoplar orasida pul ko'chirish — kun oxirida naqdni bankka topshirish
    yoki terminal hisob-kitobi.

    Ikkita yozuv, bitta `transfer_group`: biridan chiqadi, ikkinchisiga
    kiradi. JAMI o'zgarmaydi — o'tkazma pul topmaydi va yo'qotmaydi.
    """
    if source.pk == target.pk:
        raise BusinessRuleViolation(gettext("Bir qopdan oʻziga oʻtkazib boʻlmaydi."))
    if source.organization_id != target.organization_id:
        raise BusinessRuleViolation(gettext("Qoplar boshqa tashkilotga tegishli."))

    group = uuid.uuid4()
    when = occurred_at or timezone.now()
    text = description or gettext("Qoplar orasida oʻtkazma")
    out = post_movement(
        account=source,
        direction=MovementDirection.OUT,
        amount=amount,
        source_type=MovementSource.TRANSFER,
        description=text,
        occurred_at=when,
        created_by=created_by,
        transfer_group=group,
        allow_negative=allow_negative,
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


@transaction.atomic
def adjust_balance(
    *,
    account: CashAccount,
    amount: Decimal,
    reason: str,
    opening: bool = False,
    occurred_at: Any = None,
    created_by: Any = None,
) -> CashMovement:
    """
    Qoldiqni qo'lda to'g'rilash — boshlang'ich qoldiq yoki sanoq farqi
    (ADR-29).

    **Nega kerak.** Bog'cha tizimga yil o'rtasida keladi: seyfida
    allaqachon pul bor, lekin tizimda yo'q. Shu sababli har qanday
    chiqim qopni manfiyga tushirardi — va aynan shu "−6 752 500"
    bo'lib ko'rindi. Chiqimni to'sish esa boshlang'ich qoldiqsiz
    ishni butunlay to'xtatib qo'yardi.

    Yozuv — oddiy harakat (`opening` yoki `manual`), ya'ni jurnal
    append-only qoladi va "qoldiq qayerdan kelgan?" degan savolga
    SABAB bilan javob beradi. Hech narsa ustiga yozilmaydi: ikkinchi
    tuzatish — ikkinchi yozuv.

    Manfiy `amount` — pulni kamaytirish (sanoqda kam chiqdi).
    """
    amount = _money(amount)
    if amount == 0:
        raise BusinessRuleViolation(gettext("Summa nol boʻlishi mumkin emas."))
    if not reason.strip():
        raise BusinessRuleViolation(gettext("Sabab yozilishi shart."))

    return post_movement(
        account=account,
        direction=MovementDirection.IN if amount > 0 else MovementDirection.OUT,
        amount=abs(amount),
        source_type=MovementSource.OPENING if opening else MovementSource.MANUAL,
        description=reason[:255],
        occurred_at=occurred_at,
        created_by=created_by,
        # Tuzatishning o'zi qoldiqqa qarab to'xtamaydi: sanoqda KAM
        # chiqqan pulni yozish ham xuddi shunday haqiqat.
        allow_negative=True,
    )
