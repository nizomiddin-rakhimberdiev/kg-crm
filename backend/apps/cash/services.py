"""
Kassa servislari (docs/03 §13a, ADR-17).

Bu modul bitta va'da beradi: **pul harakat qilgan har bir joyda yozuv
qoladi.** Shuning uchun `post_movement()` ni chaqirish moliya, chiqim va
oylik modullari uchun majburiy — ular bir-birining modellarini emas,
shu servisni chaqiradi (1-invariant).
"""

from __future__ import annotations

import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.cash.models import (
    CashAccount,
    CashAccountKind,
    CashCount,
    CashHandover,
    CashMovement,
    HandoverStatus,
    MoneyOperation,
    MovementDirection,
    MovementSource,
    OperationKind,
)
from apps.core.exceptions import BusinessRuleViolation

__all__ = [
    "DEFAULT_ACCOUNTS",
    "ensure_branch_accounts",
    "account_for_method",
    "post_movement",
    "reverse_movements_for",
    "transfer",
    "hand_over",
    "confirm_handover",
    "reject_handover",
    "close_day",
    "record_operation",
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
                    "oʻsha tushumni yozing yoki boshqa hisobni tanlang."
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
        raise BusinessRuleViolation(gettext("Bir hisobdan oʻziga oʻtkazib boʻlmaydi."))
    if source.organization_id != target.organization_id:
        raise BusinessRuleViolation(gettext("Hisoblar boshqa tashkilotga tegishli."))

    group = uuid.uuid4()
    when = occurred_at or timezone.now()
    text = description or gettext("Hisoblar orasida oʻtkazma")
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


# --- Bosqich 12.5: naqd pul qo'ldan qo'lga va kun yopilishi ---


def cash_pot(*, branch: Any) -> CashAccount:
    """Filialning naqd kassasi — topshirish shu qop ichida bo'ladi."""
    return account_for_method(branch=branch, method="cash")


@transaction.atomic
def hand_over(
    *,
    from_user: Any,
    to_user: Any,
    amount: Decimal,
    note: str = "",
    branch: Any = None,
    account: CashAccount | None = None,
) -> CashHandover:
    """
    Naqd pulni boshqa odamga topshirish — u TASDIQLAGUNCHA pul topshiruvchida.

    Qopdan pul chiqmaydi: kassa bitta, faqat ushlab turgan qo'l almashadi.
    Hech kim qo'lida yo'q pulni topshira olmaydi (ADR-29 ruhi) — kutilayotgan
    topshiriqlar ham hisobga olinadi, aks holda bitta pul ikki marta
    "berilardi".
    """
    from apps.cash.selectors import custody_of

    amount = _money(amount)
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Summa musbat boʻlishi kerak."))
    if to_user.pk == from_user.pk:
        raise BusinessRuleViolation(gettext("Oʻzingizga topshirib boʻlmaydi."))
    if to_user.organization_id != from_user.organization_id or not to_user.is_active:
        raise BusinessRuleViolation(gettext("Qabul qiluvchi topilmadi."))

    # Naqd yoki bank hisobi bo'yicha: kassir kun oxirida ikkalasini ham
    # topshiradi — naqdni qo'lda, terminal/Click/o'tkazmani hisobot bilan.
    pot = account or cash_pot(branch=branch or from_user.branch)
    if pot.organization_id != from_user.organization_id or pot.kind not in ("cash", "bank"):
        raise BusinessRuleViolation(gettext("Hisob topilmadi."))
    held = custody_of(user=from_user, account=pot)
    if amount > held:
        raise BusinessRuleViolation(
            gettext("Qoʻlingizda {held} soʻm bor — {amount} soʻm topshirib boʻlmaydi.").format(
                held=_som(held), amount=_som(amount)
            )
        )
    return CashHandover.objects.create(
        organization=pot.organization,
        branch=pot.branch,
        cash_account=pot,
        from_user=from_user,
        to_user=to_user,
        amount=amount,
        note=note.strip()[:255],
    )


def _decide(handover: CashHandover, user: Any, status: str, note: str) -> CashHandover:
    if handover.to_user_id != user.pk:
        from rest_framework.exceptions import PermissionDenied

        # Tenant ichida — mavjudligi sir emas, lekin tasdiq faqat qabul
        # qiluvchining so'zi. Egasi ham uning o'rniga "oldim" demaydi.
        raise PermissionDenied(gettext("Faqat qabul qiluvchi tasdiqlaydi."))
    if handover.status != HandoverStatus.PENDING:
        raise BusinessRuleViolation(gettext("Bu topshiriq allaqachon koʻrib chiqilgan."))
    handover.status = status
    handover.decided_at = timezone.now()
    handover.decision_note = note.strip()[:255]
    handover.save(update_fields=["status", "decided_at", "decision_note", "updated_at"])
    return handover


@transaction.atomic
def confirm_handover(*, handover: CashHandover, user: Any) -> CashHandover:
    """Qabul qiluvchi "oldim" deydi — pul endi uning qo'lida hisoblanadi."""
    locked = CashHandover.objects.select_for_update().get(pk=handover.pk)
    return _decide(locked, user, HandoverStatus.CONFIRMED, "")


@transaction.atomic
def reject_handover(*, handover: CashHandover, user: Any, reason: str) -> CashHandover:
    """Rad etish — SABAB bilan: "sanoqda 450 000 chiqdi"."""
    if not reason.strip():
        raise BusinessRuleViolation(gettext("Sabab yozilishi shart."))
    locked = CashHandover.objects.select_for_update().get(pk=handover.pk)
    return _decide(locked, user, HandoverStatus.REJECTED, reason)


@transaction.atomic
def close_day(
    *,
    account: CashAccount,
    counted: Decimal | None = None,
    reason: str = "",
    created_by: Any = None,
    denominations: dict[str, int] | None = None,
) -> CashCount:
    """
    Kun yopilishi: jismoniy sanoq tizimdagi qoldiq bilan solishtiriladi.

    Farq bo'lsa — SABABI bilan `count` harakati, va qop sanoqqa tenglashadi.
    Excel'dagi "tenglashtiruvchi qator"dan farqi shu: farq yashirinmaydi,
    u kim sanagani va nega deb yozilgan alohida yozuv.
    """
    from apps.cash.selectors import account_balance

    notes = {str(int(note)): int(count) for note, count in (denominations or {}).items() if count}
    if notes:
        by_notes = _money(
            sum((Decimal(note) * count for note, count in notes.items()), Decimal("0"))
        )
        if counted is not None and _money(counted) != by_notes:
            raise BusinessRuleViolation(
                gettext(
                    "Kupyuralar yigʻindisi {notes} — kiritilgan sanoq {counted} bilan mos emas."
                ).format(notes=_som(by_notes), counted=_som(_money(counted)))
            )
        counted = by_notes
    if counted is None:
        raise BusinessRuleViolation(gettext("Sanoq summasini yoki kupyuralarni kiriting."))
    counted = _money(counted)
    if counted < 0:
        raise BusinessRuleViolation(gettext("Sanoq manfiy boʻlishi mumkin emas."))
    today = timezone.localdate()
    if CashCount.objects.filter(cash_account=account, counted_on=today).exists():
        raise BusinessRuleViolation(gettext("Bu hisob uchun bugungi kun allaqachon yopilgan."))

    system = _money(account_balance(account_id=account.id))
    difference = counted - system
    reason = reason.strip()[:255]
    if difference != 0 and not reason:
        raise BusinessRuleViolation(
            gettext("Sanoqda {kind} {amount} soʻm — sababini yozing.").format(
                kind=gettext("kamomad") if difference < 0 else gettext("ortiqcha"),
                amount=_som(abs(difference)),
            )
        )

    count = CashCount.objects.create(
        organization=account.organization,
        branch=account.branch,
        cash_account=account,
        counted_on=today,
        system_balance=system,
        counted=counted,
        difference=difference,
        reason=reason,
        denominations=notes,
        created_by=created_by,
    )
    if difference != 0:
        post_movement(
            account=account,
            direction=MovementDirection.IN if difference > 0 else MovementDirection.OUT,
            amount=abs(difference),
            source_type=MovementSource.COUNT,
            source_id=count.id,
            description=(
                f"{gettext('Kamomad') if difference < 0 else gettext('Ortiqcha')}: {reason}"
            )[:255],
            created_by=created_by,
            allow_negative=True,
        )
        from apps.intelligence import alerts

        alerts.notify(
            organization_id=account.organization_id,
            text=gettext("💰 Kassa farqi ({pot}): {amount} soʻm. Sabab: {reason}").format(
                pot=account.name, amount=_som(difference), reason=reason
            ),
        )
    return count


# --- Xarajat bo'lmagan pul harakatlari (Bosqich 13.2b) ---


def _dividend_tax(amount: Decimal, branch: Any) -> Decimal:
    from apps.settings_app.services import get_setting

    try:
        percent = Decimal(str(get_setting(key="tax.dividend_percent", branch=branch) or "0"))
    except ArithmeticError:
        percent = Decimal("0")
    return (amount * percent / Decimal("100")).quantize(Decimal("1"))


def lend_money(
    *,
    account: CashAccount,
    amount: Decimal,
    occurred_on: Any,
    person: str,
    reason: str,
    created_by: Any = None,
    allow_negative: bool = False,
) -> MoneyOperation:
    """
    Qarzga pul beradi — CHIQIM emas (mijoz soʻrovi, 2026-10-28).

    Mijozning soʻzi: *"summadan ayrilaversin, lekin xisob kitobga ham
    tushaversin, u qarz pullar boʻlishi mumkin, uni qaytarish
    imkoniyati ham boʻlishi kerak"*.

    Shuning uchun u foyda-zararga tushmaydi: bogʻcha bu puldan
    kambagʻal boʻlgani yoʻq, pul kimdadir turibdi. Kassadan esa
    chiqadi, chunki pul haqiqatan qoʻldan ketdi — va ADR-29 bu yerda
    ham ishlaydi: qopda yoʻq pulni qarzga ham berib boʻlmaydi.

    "Kimga" MAJBURIY: egasiz qarz keyin hech kimdan soʻralmaydi.
    """
    if not (person or "").strip():
        raise BusinessRuleViolation(gettext("Pul kimga berilganini yozing."))
    return record_operation(
        kind=OperationKind.LOAN_OUT,
        account=account,
        amount=amount,
        occurred_on=occurred_on,
        reason=reason,
        counterparty=person,
        created_by=created_by,
        allow_negative=allow_negative,
    )


@transaction.atomic
def return_loan(
    *,
    loan: MoneyOperation,
    account: CashAccount,
    amount: Decimal,
    occurred_on: Any,
    note: str = "",
    created_by: Any = None,
) -> MoneyOperation:
    """
    Qarz qaytdi — pul yana kassaga tushadi.

    Qaytish ASL hujjatga bogʻlanadi (`settles`), aks holda "kimda
    qancha qoldi?" degan savolga javob boʻlmasdi: pul shunchaki
    kassaga tushib, qaysi qarzniki ekani esda qolmasdi.

    Qarzdan KOʻPROQ qaytarib boʻlmaydi: ortiqcha pul — boshqa hodisa
    (sovgʻa, boshqa daromad), va uni qarz deb yozish keyin qarzlar
    roʻyxatini manfiyga tushirardi.
    """
    if loan.kind != OperationKind.LOAN_OUT:
        raise BusinessRuleViolation(gettext("Bu hujjat qarz emas."))
    amount = _money(amount)
    if amount > loan.outstanding:
        raise BusinessRuleViolation(
            gettext("Qarzdan koʻp qaytarib boʻlmaydi — qolgani {amount} soʻm.").format(
                amount=f"{loan.outstanding:,.0f}".replace(",", " ")
            )
        )
    return record_operation(
        kind=OperationKind.LOAN_RETURN,
        account=account,
        amount=amount,
        occurred_on=occurred_on,
        reason=note.strip() or gettext("Qarz qaytdi: {person}").format(person=loan.counterparty),
        counterparty=loan.counterparty,
        created_by=created_by,
        settles=loan,
    )


@transaction.atomic
def record_operation(
    *,
    kind: str,
    account: CashAccount,
    amount: Decimal,
    occurred_on: Any,
    reason: str,
    subtype: str = "",
    period: tuple[int, int] | None = None,
    counterparty: str = "",
    created_by: Any = None,
    allow_negative: bool = False,
    settles: MoneyOperation | None = None,
) -> MoneyOperation:
    """
    Hujjat + pul harakati, bitta tranzaksiyada (invariant 12).

    Chiqadigan pul ADR-29 ga bo'ysunadi: qopda yo'q pul egaga ham
    berilmaydi (`allow_negative` — ogohlantirishni o'qigan odam uchun).
    """
    from apps.cash.models import OPERATION_DIRECTION, OPERATION_SUBTYPES

    if kind not in OPERATION_DIRECTION:
        raise BusinessRuleViolation(gettext("Notoʻgʻri operatsiya turi."))
    if subtype not in OPERATION_SUBTYPES[kind]:
        raise BusinessRuleViolation(gettext("Bu turda bunday aniqlik yoʻq."))
    reason = (reason or "").strip()
    if not reason:
        raise BusinessRuleViolation(gettext("Sabab yozilishi shart."))
    amount = _money(amount)
    if amount <= 0:
        raise BusinessRuleViolation(gettext("Summa musbat boʻlishi kerak."))
    if occurred_on > timezone.localdate():
        raise BusinessRuleViolation(gettext("Sana kelajakda boʻlishi mumkin emas."))

    year, month = period or (occurred_on.year, occurred_on.month)
    tax = (
        _dividend_tax(amount, account.branch)
        if kind == OperationKind.OWNER_DRAW and subtype == "dividend"
        else Decimal("0")
    )
    operation = MoneyOperation.objects.create(
        organization=account.organization,
        branch=account.branch,
        kind=kind,
        subtype=subtype,
        cash_account=account,
        amount=amount,
        occurred_on=occurred_on,
        period_year=year,
        period_month=month,
        counterparty=counterparty.strip()[:120],
        reason=reason[:255],
        tax_amount=tax,
        # Qaysi qarzni yopyapti — hujjat bilan BIRGA yoziladi: baza
        # cheklovi `loan_return` ni bogʻlanishsiz qabul qilmaydi.
        settles=settles,
        created_by=created_by,
    )
    post_movement(
        account=account,
        direction=OPERATION_DIRECTION[kind],
        amount=amount,
        source_type=MovementSource.OPERATION,
        source_id=operation.id,
        description=f"{operation.get_kind_display()}: {reason}"[:255],
        occurred_at=timezone.make_aware(datetime.combine(occurred_on, time(12))),
        created_by=created_by,
        allow_negative=allow_negative,
    )
    return operation
