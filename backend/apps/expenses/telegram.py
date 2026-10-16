"""
Chiqimni Telegram orqali kiritish (Bosqich 13.3c, brif §4).

Oqim ikki qadam:

1. xodim summa (va xohlasa chek rasmini, izohni) yuboradi —
   "150 000 kartoshka" — bot oxirgi ishlatilgan toifalarni tugma qiladi;
2. tugma bosiladi — chiqim filialning naqd kassasidan yoziladi, rasm chek
   bo'lib biriktiriladi.

Ruxsat — xuddi ekrandagidek (`expenses.create`); qopda pul yetmasa ADR-29
bot javobida aytiladi. Bot holatsiz: hamma narsa qoralamada.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone

from apps.core.exceptions import BusinessRuleViolation
from apps.core.permissions import has_permission_code
from apps.expenses.models import Expense, ExpenseCategory, ExpenseDraft

logger = logging.getLogger(__name__)

__all__ = ["download_photo", "start_draft", "choose_category"]

#: Tugmada nechta toifa.
BUTTONS = 8
_AMOUNT = re.compile(r"\d[\d\s.,]*")

TEXTS = {
    "need_amount": "Summani yozing, masalan: 150 000 kartoshka",
    "forbidden": "Chiqim kiritishga ruxsatingiz yoʻq.",
    "pick": "{amount} soʻm — qaysi toifa?",
    "no_categories": "Chiqim toifalari yoʻq — avval ilovada toifa qoʻshing.",
    "saved": "✓ Saqlandi: {amount} soʻm — {category} (naqd kassa).",
    "duplicate": "Bu chiqim allaqachon saqlangan.",
    "expired": "Bu tugma eskirgan — summani qayta yuboring.",
}


def _som(value: Decimal) -> str:
    return f"{int(value):,}".replace(",", " ")


def _branch(user: Any) -> Any:
    from apps.branches.models import Branch

    if user.branch_id:
        return user.branch
    return Branch.objects.filter(is_active=True).order_by("created_at").first()


def parse(text: str) -> tuple[Decimal | None, str]:
    """`"150 000 kartoshka, piyoz"` → (150000, "kartoshka, piyoz")."""
    match = _AMOUNT.search(text or "")
    if match is None:
        return None, (text or "").strip()
    digits = re.sub(r"[^\d]", "", match.group(0).split(",")[0].split(".")[0])
    if not digits or int(digits) <= 0:
        return None, (text or "").strip()
    note = (text[: match.start()] + text[match.end() :]).strip(" ,.-—:\n\t")
    return Decimal(digits), note[:255]


def _recent_categories(branch: Any) -> list[ExpenseCategory]:
    return list(
        ExpenseCategory.objects.filter(branch=branch, is_active=True)
        .annotate(last_used=Max("expenses__created_at"))
        .order_by(F("last_used").desc(nulls_last=True), "name")[:BUTTONS]
    )


def start_draft(*, user: Any, text: str, photo_file_id: str = "") -> tuple[str, str, Any]:
    """Qoralama + toifa tugmalari. Qaytaradi: (natija, matn, klaviatura)."""
    if not has_permission_code(user, "expenses.create"):
        return "expense_forbidden", TEXTS["forbidden"], None
    amount, note = parse(text)
    if amount is None:
        return "expense_needs_amount", TEXTS["need_amount"], None
    branch = _branch(user)
    categories = _recent_categories(branch) if branch is not None else []
    if not categories:
        return "expense_no_categories", TEXTS["no_categories"], None
    draft = ExpenseDraft.objects.create(
        organization=user.organization,
        branch=branch,
        user=user,
        amount=amount,
        note=note,
        photo_file_id=photo_file_id[:255],
        category_ids=[str(category.id) for category in categories],
    )
    rows = [
        [{"text": category.name, "callback_data": f"x:{draft.id.hex}:{index}"}]
        for index, category in enumerate(categories)
    ]
    return (
        "expense_draft",
        TEXTS["pick"].format(amount=_som(amount)),
        {"inline_keyboard": rows},
    )


@transaction.atomic
def choose_category(*, user: Any, data: str) -> tuple[str, str]:
    """Tugma: qoralamadan chiqim. Qaytaradi: (natija, matn)."""
    from apps.cash import services as cash
    from apps.expenses.services import approve_expense

    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "x" or not parts[2].isdigit():
        return "ignored", ""
    draft = (
        ExpenseDraft.objects.select_for_update().filter(pk=parts[1], user=user).first()
        if re.fullmatch(r"[0-9a-f]{32}", parts[1])
        else None
    )
    if draft is None:
        return "expense_expired", TEXTS["expired"]
    if draft.expense_id is not None:
        return "expense_duplicate", TEXTS["duplicate"]
    index = int(parts[2])
    if index >= len(draft.category_ids):
        return "expense_expired", TEXTS["expired"]
    category = ExpenseCategory.objects.filter(pk=draft.category_ids[index]).first()
    if category is None:
        return "expense_expired", TEXTS["expired"]

    today = timezone.localdate()
    till = cash.cash_pot(branch=draft.branch)
    expense = Expense.objects.create(
        organization=draft.organization,
        branch=draft.branch,
        category=category,
        amount=draft.amount,
        expense_date=today,
        period_year=today.year,
        period_month=today.month,
        description=draft.note,
        cash_account=till,
    )
    try:
        approve_expense(expense=expense, approved_by=user)
    except BusinessRuleViolation as exc:
        transaction.set_rollback(True)
        return "expense_refused", str(exc)

    if draft.photo_file_id:
        try:
            expense.receipt.save("telegram.jpg", ContentFile(download_photo(draft.photo_file_id)))
        except Exception:  # noqa: BLE001 — chek kelmasa ham chiqim saqlanadi
            logger.exception("Telegram chek rasmi yuklanmadi")
    draft.expense = expense
    draft.save(update_fields=["expense", "updated_at"])
    return "expense_created", TEXTS["saved"].format(
        amount=_som(draft.amount), category=category.name
    )


def download_photo(file_id: str) -> bytes:
    """Telegram'dan rasm: `getFile` → fayl yo'li → baytlar."""
    import requests

    token = str(getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN yo'q")
    meta = requests.get(
        f"https://api.telegram.org/bot{token}/getFile", params={"file_id": file_id}, timeout=10
    )
    meta.raise_for_status()
    path = meta.json()["result"]["file_path"]
    content = requests.get(f"https://api.telegram.org/file/bot{token}/{path}", timeout=20)
    content.raise_for_status()
    return content.content
