"""
Bank ko'chirmasi: o'qish, ustunlarni moslashtirish va qatorlarni hujjatga
bog'lash (Bosqich 13.3d, brif §4).

Bog'lash tartibi — eng ishonchlisidan:

kirim
  1. yo'ldagi pul (Click/Payme/terminal) — o'sha kunlik reestr yig'indisi
     yoki bitta to'lov kutilgan summasi bilan teng;
  2. tizimda bor kirim — o'tkazma bilan kelgan to'lov, boshqa daromad,
     egadan kiritma, kredit, o'z qoplari orasidagi o'tkazma (summa teng,
     sana ±3 kun);
  3. ota-ona to'lovi tizimda yo'q — maqsaddagi shartnoma raqami yoki
     bitta bolaga tegishli ism bo'yicha YANGI to'lov;
chiqim
  4. tizimda bor chiqim — xarajat, oylik, egaga to'lov, soliq, qaytarish,
     o'tkazma (summa teng, sana ±3 kun).

Qolgani "moslashtirilmagan" navbatga tushadi: odam qaror qiladi. Taxmin
qilinmaydi — ikki bola bir xil ismda bo'lsa, qator navbatda qoladi.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.cash.models import (
    BankStatement,
    BankStatementLine,
    CashAccount,
    CashMovement,
    LineStatus,
)
from apps.core.exceptions import BusinessRuleViolation

__all__ = [
    "expense_from_line",
    "ignore_line",
    "import_statement",
    "match_line",
    "payment_from_line",
    "preview",
]

#: Sana ±shuncha kun ichida bo'lsa, summa teng qator o'sha hujjat.
MATCH_WINDOW_DAYS = 3
#: Yo'ldagi pul to'lovdan shuncha kun ichida bankka tushadi.
TRANSIT_WINDOW_DAYS = 7
_DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d.%m.%y", "%d-%m-%Y")
_APOSTROPHES = "ʻʼ‘’`'"
_PROVIDER_WORDS = {
    "click": ("click",),
    "payme": ("payme",),
    "terminal": ("uzcard", "humo", "terminal", "visa", "pos"),
}


# --- O'qish ---


def _rows(file_bytes: bytes, file_name: str) -> list[list[Any]]:
    """Faylning birinchi varag'i — xom qiymatlar (sana `date` bo'lib qoladi)."""
    if file_name.lower().endswith((".csv", ".txt")):
        text = file_bytes.decode("utf-8-sig", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,\t")
        except csv.Error:
            dialect = csv.excel
        return [list(row) for row in csv.reader(io.StringIO(text), dialect)]

    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 — fayl foydalanuvchidan, har xil buzuq bo'ladi
        raise BusinessRuleViolation(
            gettext("Faylni oʻqib boʻlmadi — Excel (.xlsx) yoki CSV yuboring.")
        ) from exc
    return [list(row) for row in workbook.worksheets[0].iter_rows(values_only=True)]


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _header_index(rows: list[list[Any]]) -> int:
    """Sarlavha — kamida uchta matnli katakli birinchi qator (oldida bank nomi bo'lishi mumkin)."""
    for index, row in enumerate(rows[:30]):
        texts = [_cell(value) for value in row if _cell(value)]
        if len(texts) >= 3 and all(not text.replace(" ", "").isdigit() for text in texts):
            return index
    raise BusinessRuleViolation(gettext("Faylda ustun sarlavhalari topilmadi."))


def preview(*, file_bytes: bytes, file_name: str) -> dict[str, Any]:
    """Ustun sarlavhalari va birinchi qatorlar — moslashtirish oynasi uchun."""
    rows = _rows(file_bytes, file_name)
    head = _header_index(rows)
    headers = [_cell(value) for value in rows[head]]
    sample = [[_cell(value) for value in row] for row in rows[head + 1 : head + 6] if any(row)]
    return {"headers": headers, "sample": sample}


def _amount(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    text = str(value).replace(" ", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(",", "")
    text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise BusinessRuleViolation(
            gettext("Summa oʻqilmadi: {value}.").format(value=value)
        ) from exc


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _cell(value).split(" ")[0]
    for pattern in _DATE_FORMATS:
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


@dataclass
class ParsedLine:
    line_no: int
    booked_on: date
    direction: str
    amount: Decimal
    purpose: str
    counterparty: str
    reference: str


def _parse(rows: list[list[Any]], mapping: dict[str, str]) -> list[ParsedLine]:
    head = _header_index(rows)
    headers = [_cell(value) for value in rows[head]]

    def column(key: str) -> int | None:
        name = mapping.get(key)
        if not name:
            return None
        if name not in headers:
            raise BusinessRuleViolation(gettext("Ustun topilmadi: {name}.").format(name=name))
        return headers.index(name)

    date_col = column("date")
    if date_col is None:
        raise BusinessRuleViolation(gettext("Sana ustunini tanlang."))
    amount_col, credit_col, debit_col = column("amount"), column("credit"), column("debit")
    if amount_col is None and credit_col is None and debit_col is None:
        raise BusinessRuleViolation(gettext("Summa yoki debet/kredit ustunlarini tanlang."))
    purpose_col, party_col, ref_col = column("purpose"), column("counterparty"), column("reference")

    def get(row: list[Any], index: int | None) -> Any:
        return row[index] if index is not None and index < len(row) else None

    parsed: list[ParsedLine] = []
    for offset, row in enumerate(rows[head + 1 :], start=1):
        booked = _date(get(row, date_col))
        if booked is None:
            continue  # jami, bo'sh yoki izoh qatorlari
        if amount_col is not None:
            value = _amount(get(row, amount_col))
            direction, amount = ("in" if value > 0 else "out"), abs(value)
        else:
            credit, debit = _amount(get(row, credit_col)), _amount(get(row, debit_col))
            direction, amount = ("in", credit) if credit > 0 else ("out", debit)
        if amount <= 0:
            continue
        parsed.append(
            ParsedLine(
                line_no=offset,
                booked_on=booked,
                direction=direction,
                amount=amount.quantize(Decimal("0.01")),
                purpose=_cell(get(row, purpose_col)),
                counterparty=_cell(get(row, party_col))[:255],
                reference=_cell(get(row, ref_col))[:100],
            )
        )
    return parsed


# --- Bog'lash ---


def _plain(text: str) -> str:
    cleaned = text.casefold()
    for mark in _APOSTROPHES:
        cleaned = cleaned.replace(mark, "")
    return cleaned


def _already_linked(kind: str, ids: list[str]) -> bool:
    return any(
        BankStatementLine.objects.filter(
            match_kind=kind, matched_ids__contains=[identifier]
        ).exists()
        for identifier in ids
    )


def _match_transit(line: BankStatementLine) -> list[str] | None:
    """Kunlik reestr yoki bitta to'lov — kutilgan summa bilan teng."""
    from apps.finance.selectors import in_transit

    rows = [
        row
        for row in in_transit(organization_id=line.organization_id, branch_id=line.branch_id)
        if row["cash_account_id"] == str(line.cash_account_id)
        and line.booked_on - timedelta(days=TRANSIT_WINDOW_DAYS)
        <= date.fromisoformat(row["paid_on"])
        <= line.booked_on
    ]
    text = _plain(f"{line.purpose} {line.counterparty}")
    hinted = [
        method for method, words in _PROVIDER_WORDS.items() if any(word in text for word in words)
    ]
    if hinted:
        preferred = [row for row in rows if row["method"] in hinted]
        rows = preferred or rows

    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["method"], row["paid_on"]), []).append(row)
    for group in groups.values():
        if sum(Decimal(row["expected_amount"]) for row in group) == line.amount:
            return [row["payment_id"] for row in group]
    for row in rows:
        if Decimal(row["expected_amount"]) == line.amount:
            return [row["payment_id"]]
    return None


#: Kirim/chiqim harakati manbai → moslik turi. To'lov — faqat bankka
#: to'g'ridan-to'g'ri keladigan usul bilan (yo'ldagi pul 1-qoida bilan).
_MOVEMENT_KINDS = {
    "in": ("payment", "operation", "transfer"),
    "out": ("expense", "operation", "payroll", "advance", "refund", "transfer", "payment_reversal"),
}


def _match_movement(line: BankStatementLine) -> tuple[str, str] | None:
    from apps.finance.models import TRANSIT_METHODS, Payment

    window = (
        timezone.make_aware(
            datetime.combine(line.booked_on - timedelta(days=MATCH_WINDOW_DAYS), time.min)
        ),
        timezone.make_aware(
            datetime.combine(line.booked_on + timedelta(days=MATCH_WINDOW_DAYS), time.max)
        ),
    )
    candidates = CashMovement.objects.filter(
        cash_account_id=line.cash_account_id,
        direction=line.direction,
        amount=line.amount,
        source_type__in=_MOVEMENT_KINDS[line.direction],
        occurred_at__range=window,
        source_id__isnull=False,
    ).order_by("occurred_at")
    for movement in candidates:
        source_id = str(movement.source_id)
        if (
            movement.source_type == "payment"
            and Payment.objects.filter(pk=movement.source_id, method__in=TRANSIT_METHODS).exists()
        ):
            continue
        kind = movement.source_type
        if kind == "transfer" and movement.transfer_group:
            source_id = str(movement.transfer_group)
        if not _already_linked(kind, [source_id]):
            return kind, source_id
    return None


def _find_child(line: BankStatementLine) -> Any:
    """
    Maqsaddagi shartnoma raqami yoki ism — BITTA bolaga olib borsagina.

    Ikki bola bir xil ismda bo'lsa `None`: noto'g'ri bolaga yozilgan pul
    yashirin qarzning eng yomon turi.
    """
    from apps.children.models import Child, EnrollmentStatus
    from apps.contracts.models import Contract

    text = _plain(line.purpose)
    tokens = set(re.findall(r"[0-9a-zа-яё\-/]+", text))
    for contract in Contract.objects.filter(branch_id=line.branch_id).select_related("child"):
        if _plain(contract.number) in tokens:
            return contract.child
    matches = [
        child
        for child in Child.objects.filter(branch_id=line.branch_id, is_active=True).exclude(
            enrollment_status__in=[EnrollmentStatus.WITHDRAWN, EnrollmentStatus.GRADUATED]
        )
        if _plain(child.first_name) in tokens and _plain(child.last_name) in tokens
    ]
    return matches[0] if len(matches) == 1 else None


def _create_payment(line: BankStatementLine, user: Any) -> str | None:
    from apps.finance.services import record_payment

    child = _find_child(line)
    if child is None:
        return None
    payment = record_payment(
        child=child,
        amount=line.amount,
        method="bank_transfer",
        reference=(line.reference or line.purpose)[:100],
        paid_at=timezone.make_aware(datetime.combine(line.booked_on, time(12))),
        received_by=user,
        backdate_reason=gettext("Bank koʻchirmasidan"),
        allocation_reason=gettext("Bank koʻchirmasidan"),
        idempotency_key=f"stmt:{line.fingerprint}"[:64],
    )
    return str(payment.id)


def match_line(line: BankStatementLine, user: Any = None) -> bool:
    """Qatorni hujjatga bog'laydi. `True` — bog'landi."""
    from apps.finance.models import Payment
    from apps.finance.services import settle_payments

    kind: str = ""
    ids: list[str] = []
    if line.direction == "in":
        transit = _match_transit(line)
        if transit:
            settle_payments(
                payments=list(Payment.objects.filter(pk__in=transit).select_related("child")),
                settled_on=line.booked_on,
                reference=(line.reference or line.purpose)[:120],
                created_by=user,
            )
            kind, ids = "settlement", transit
    if not kind:
        found = _match_movement(line)
        if found:
            kind, ids = found[0], [found[1]]
    if not kind and line.direction == "in":
        created = _create_payment(line, user)
        if created:
            kind, ids = "payment_created", [created]
    if not kind:
        return False
    line.status = LineStatus.MATCHED
    line.match_kind = kind
    line.matched_ids = ids
    line.save(update_fields=["status", "match_kind", "matched_ids", "updated_at"])
    return True


# --- Import ---


@transaction.atomic
def import_statement(
    *,
    account: CashAccount,
    file_bytes: bytes,
    file_name: str,
    mapping: dict[str, str],
    closing_balance: Decimal | None = None,
    uploaded_by: Any = None,
) -> BankStatement:
    """Qatorlarni yozadi (takrorlarini o'tkazib), bog'laydi, qoldiqni solishtiradi."""
    from apps.cash.selectors import account_balance

    if account.kind != "bank":
        raise BusinessRuleViolation(gettext("Koʻchirma faqat bank hisobiga yuklanadi."))
    parsed = _parse(_rows(file_bytes, file_name), mapping)
    if not parsed:
        raise BusinessRuleViolation(gettext("Faylda summa va sanasi bor qator topilmadi."))

    statement = BankStatement.objects.create(
        organization=account.organization,
        branch=account.branch,
        cash_account=account,
        file_name=file_name[:255],
        period_from=min(line.booked_on for line in parsed),
        period_to=max(line.booked_on for line in parsed),
        closing_balance=closing_balance,
        mapping=mapping,
        uploaded_by=uploaded_by,
    )
    seen: dict[str, int] = {}
    created: list[BankStatementLine] = []
    skipped = 0
    for item in parsed:
        base = hashlib.sha256(
            "|".join(
                [
                    str(account.id),
                    item.booked_on.isoformat(),
                    item.direction,
                    f"{item.amount:.2f}",
                    item.purpose,
                    item.counterparty,
                    item.reference,
                ]
            ).encode()
        ).hexdigest()[:56]
        seen[base] = seen.get(base, 0) + 1
        fingerprint = f"{base}#{seen[base]}"
        if BankStatementLine.objects.filter(cash_account=account, fingerprint=fingerprint).exists():
            skipped += 1
            continue
        created.append(
            BankStatementLine.objects.create(
                organization=account.organization,
                branch=account.branch,
                statement=statement,
                cash_account=account,
                line_no=item.line_no,
                booked_on=item.booked_on,
                direction=item.direction,
                amount=item.amount,
                purpose=item.purpose,
                counterparty=item.counterparty,
                reference=item.reference,
                fingerprint=fingerprint,
            )
        )

    matched = sum(1 for line in created if match_line(line, uploaded_by))
    end = timezone.make_aware(datetime.combine(statement.period_to, time.max))
    statement.system_balance = account_balance(account_id=account.id, up_to=end)
    statement.line_count = len(created)
    statement.matched_count = matched
    statement.skipped_count = skipped
    statement.save(
        update_fields=[
            "system_balance",
            "line_count",
            "matched_count",
            "skipped_count",
            "updated_at",
        ]
    )
    return statement


# --- Navbat: odam qaror qiladi ---


def _decide(line: BankStatementLine, user: Any, kind: str, ids: list[str], note: str = "") -> None:
    if line.status != LineStatus.UNMATCHED:
        raise BusinessRuleViolation(gettext("Bu qator allaqachon koʻrib chiqilgan."))
    line.status = LineStatus.IGNORED if kind == "ignored" else LineStatus.MATCHED
    line.match_kind = "" if kind == "ignored" else kind
    line.matched_ids = ids
    line.note = note[:255]
    line.decided_by = user
    line.save(
        update_fields=["status", "match_kind", "matched_ids", "note", "decided_by", "updated_at"]
    )


@transaction.atomic
def ignore_line(*, line: BankStatementLine, note: str, user: Any = None) -> BankStatementLine:
    """E'tiborsiz — SABAB bilan: "nega bu qator hech narsaga bog'lanmagan?"."""
    if not note.strip():
        raise BusinessRuleViolation(gettext("Sabab yozilishi shart."))
    _decide(line, user, "ignored", [], note.strip())
    return line


@transaction.atomic
def expense_from_line(*, line: BankStatementLine, category: Any, user: Any = None) -> Any:
    """
    Chiqim qatoridan xarajat (bank xizmati, SMS, avtomatik yechimlar).

    Pul bankdan allaqachon chiqqan — ko'chirma buni aytadi; shuning uchun
    qoldiq tekshiruvi to'smaydi (`allow_negative`).
    """
    from apps.expenses.models import Expense
    from apps.expenses.services import approve_expense

    if line.direction != "out":
        raise BusinessRuleViolation(gettext("Faqat chiqim qatoridan xarajat yaratiladi."))
    if category.organization_id != line.organization_id:
        raise BusinessRuleViolation(gettext("Toifa topilmadi."))
    expense = Expense.objects.create(
        organization=line.organization,
        branch=line.branch,
        category=category,
        amount=line.amount,
        expense_date=line.booked_on,
        period_year=line.booked_on.year,
        period_month=line.booked_on.month,
        description=(line.purpose or line.counterparty)[:255],
        cash_account=line.cash_account,
    )
    approve_expense(expense=expense, approved_by=user, allow_negative=True)
    _decide(line, user, "expense", [str(expense.id)])
    return expense


@transaction.atomic
def payment_from_line(*, line: BankStatementLine, child: Any, user: Any = None) -> Any:
    """Kirim qatoridan ota-ona to'lovi — bolani odam tanlagan (ism ikki bolada bo'lsa)."""
    from apps.finance.services import record_payment

    if line.direction != "in":
        raise BusinessRuleViolation(gettext("Faqat kirim qatoridan toʻlov yaratiladi."))
    if child.organization_id != line.organization_id:
        raise BusinessRuleViolation(gettext("Bola topilmadi."))
    payment = record_payment(
        child=child,
        amount=line.amount,
        method="bank_transfer",
        reference=(line.reference or line.purpose)[:100],
        paid_at=timezone.make_aware(datetime.combine(line.booked_on, time(12))),
        received_by=user,
        backdate_reason=gettext("Bank koʻchirmasidan"),
        allocation_reason=gettext("Bank koʻchirmasidan"),
        idempotency_key=f"stmt:{line.fingerprint}"[:64],
    )
    _decide(line, user, "payment_created", [str(payment.id)])
    return payment
