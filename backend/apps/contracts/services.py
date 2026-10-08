"""
Contracts — filling a template and keeping the result (PLAN 6.5).

Placeholders are a closed list (`PLACEHOLDERS`): a template that names an
unknown one is refused when it is SAVED, because a typo found on a printed
contract in front of a parent is far more expensive than one found at the
desk. A known placeholder with no value (a child without a guardian, an
organization without a tax id) prints as a blank line to fill in by hand —
never as an empty gap nobody notices.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.contracts.models import Contract, ContractStatus, ContractTemplate
from apps.core.exceptions import BusinessRuleViolation

__all__ = [
    "PLACEHOLDERS",
    "BLANK",
    "unknown_placeholders",
    "render",
    "save_template",
    "create_contract",
    "sign",
    "terminate",
]

BLANK = "__________"

_PATTERN = re.compile(r"\{\{\s*([a-z_]+\.[a-z_]+)\s*\}\}")


def _date(value: date | None) -> str:
    return value.strftime("%d.%m.%Y") if value else ""


def _money(value: Decimal | None) -> str:
    return f"{value:,.0f}".replace(",", " ") if value is not None else ""


def _group_name(ctx: dict[str, Any]) -> str:
    from apps.children.models import Enrollment, EnrollmentState

    enrollment = (
        Enrollment.objects.filter(
            child=ctx["child"], status=EnrollmentState.ACTIVE, end_date__isnull=True
        )
        .select_related("group")
        .first()
    )
    return enrollment.group.name if enrollment else ""


def _price(ctx: dict[str, Any]) -> Any:
    from apps.finance.selectors import child_monthly_price

    if "price" not in ctx:
        ctx["price"] = child_monthly_price(ctx["child"])
    return ctx["price"]


def _setting(key: str, *, money: bool = False) -> Callable[[dict[str, Any]], str]:
    """Sozlamadan o'qiladigan maydon (PLAN 9.3) — direktor, bank, kunlik ovqat puli."""

    def read(_ctx: dict[str, Any]) -> str:
        from apps.settings_app.services import get_setting

        value = get_setting(key=key)
        if value in (None, ""):
            return ""
        if money:
            return _money(Decimal(str(value)))
        return str(value)

    return read


def _guardian(attr: str) -> Callable[[dict[str, Any]], str]:
    def read(ctx: dict[str, Any]) -> str:
        guardian = ctx.get("guardian")
        if guardian is None:
            return ""
        return str(guardian.full_name if attr == "full_name" else getattr(guardian, attr, ""))

    return read


#: Placeholder → how to read it. Uzbek keys: the kindergarten writes them.
PLACEHOLDERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "bola.fio": lambda ctx: ctx["child"].full_name,
    "bola.ism": lambda ctx: ctx["child"].first_name,
    "bola.tugilgan_sana": lambda ctx: _date(ctx["child"].date_of_birth),
    "bola.guruh": _group_name,
    "vasiy.fio": _guardian("full_name"),
    "vasiy.telefon": _guardian("phone"),
    "tarif.nomi": lambda ctx: (_price(ctx).label if _price(ctx) else ""),
    "tarif.summa": lambda ctx: (_money(_price(ctx).amount) if _price(ctx) else ""),
    "bogcha.nomi": lambda ctx: ctx["organization"].name,
    "bogcha.yuridik_nomi": lambda ctx: ctx["organization"].legal_name,
    "bogcha.stir": lambda ctx: ctx["organization"].tax_id,
    "bogcha.telefon": lambda ctx: ctx["organization"].contact_phone,
    "filial.nomi": lambda ctx: ctx["branch"].name,
    "filial.manzil": lambda ctx: ctx["branch"].address,
    "shartnoma.raqam": lambda ctx: ctx["number"],
    "shartnoma.sana": lambda ctx: _date(ctx["today"]),
    # --- Shartnoma rekvizitlari (PLAN 9.3) ---
    "bola.tugilgan_yil": lambda ctx: str(ctx["child"].date_of_birth.year)
    if ctx["child"].date_of_birth
    else "",
    "bogcha.direktor": _setting("contracts.director_name"),
    "bogcha.bank": _setting("contracts.bank_name"),
    "bogcha.hisob_raqam": _setting("contracts.bank_account"),
    "bogcha.mfo": _setting("contracts.bank_mfo"),
    "tolov.kuni": _setting("finance.due_day"),
    "tolov.ovqat_puli": _setting("contracts.daily_meal_fee", money=True),
    "tolov.bepul_kunlar": _setting("contracts.free_absence_days"),
    "bogcha.saqlash_soati": _setting("contracts.daily_hours"),
}


def unknown_placeholders(body: str) -> list[str]:
    return sorted({name for name in _PATTERN.findall(body or "") if name not in PLACEHOLDERS})


def render(body: str, ctx: dict[str, Any]) -> tuple[str, dict[str, str]]:
    """The filled text and the values used — both are frozen on the contract."""
    values: dict[str, str] = {}
    for name in _PATTERN.findall(body):
        if name in PLACEHOLDERS and name not in values:
            values[name] = str(PLACEHOLDERS[name](ctx) or "").strip()

    def fill(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in PLACEHOLDERS:
            return match.group(0)
        return values.get(name) or BLANK

    return _PATTERN.sub(fill, body), values


@transaction.atomic
def save_template(
    *,
    organization: Any,
    template: ContractTemplate | None,
    name: str,
    body: str,
    language: str = "uz",
) -> ContractTemplate:
    unknown = unknown_placeholders(body)
    if unknown:
        raise BusinessRuleViolation(
            gettext("Nomaʼlum maydonlar: {names}.").format(
                names=", ".join("{{" + name + "}}" for name in unknown)
            )
        )
    if template is None:
        return ContractTemplate.objects.create(
            organization=organization, name=name, body=body, language=language
        )
    if body != template.body:
        template.version += 1
    template.name = name
    template.body = body
    template.language = language
    template.save(update_fields=["name", "body", "language", "version", "updated_at"])
    return template


def _next_number(today: date) -> str:
    """`SH-2026-0007` — per organization (the queryset is tenant-scoped), per year."""
    prefix = f"SH-{today.year}-"
    taken = Contract.objects.filter(number__startswith=prefix).values_list("number", flat=True)
    tails = [n.rsplit("-", 1)[1] for n in taken]
    highest = max((int(tail) for tail in tails if tail.isdigit()), default=0)
    return f"{prefix}{highest + 1:04d}"


def create_contract(
    *,
    child: Any,
    template: ContractTemplate,
    guardian: Any = None,
    created_by: Any = None,
) -> Contract:
    """Fills the template for this child now; the result never changes again."""
    if not template.is_active:
        raise BusinessRuleViolation(gettext("Bu shablon oʻchirilgan."))
    if child.archived_at is not None:
        raise BusinessRuleViolation(gettext("Arxivdagi bolaga shartnoma tuzib boʻlmaydi."))
    if guardian is not None and not child.guardian_links.filter(guardian=guardian).exists():
        raise BusinessRuleViolation(gettext("Bu vasiy shu bolaga bogʻlanmagan."))
    if guardian is None:
        link = (
            child.guardian_links.filter(is_primary=True).select_related("guardian").first()
            or child.guardian_links.select_related("guardian").first()
        )
        guardian = link.guardian if link else None

    today = timezone.localdate()
    for _attempt in range(3):
        number = _next_number(today)
        ctx = {
            "child": child,
            "guardian": guardian,
            "organization": child.organization,
            "branch": child.branch,
            "number": number,
            "today": today,
        }
        text, values = render(template.body, ctx)
        try:
            with transaction.atomic():
                return Contract.objects.create(
                    organization_id=child.organization_id,
                    branch_id=child.branch_id,
                    number=number,
                    child=child,
                    guardian=guardian,
                    template=template,
                    template_version=template.version,
                    values=values,
                    rendered_text=text,
                    created_by=created_by,
                )
        except IntegrityError:  # two desks took the same number — take the next
            continue
    raise BusinessRuleViolation(gettext("Shartnoma raqamini band qilib boʻlmadi, qayta urining."))


def sign(contract: Contract, *, signed_on: date) -> Contract:
    if contract.status != ContractStatus.DRAFT:
        raise BusinessRuleViolation(gettext("Faqat qoralama shartnoma imzolanadi."))
    if signed_on > timezone.localdate():
        raise BusinessRuleViolation(gettext("Imzolash sanasi kelajakda boʻlishi mumkin emas."))
    contract.status = ContractStatus.SIGNED
    contract.signed_on = signed_on
    contract.save(update_fields=["status", "signed_on", "updated_at"])
    return contract


def terminate(contract: Contract, *, terminated_on: date, reason: str = "") -> Contract:
    if contract.status == ContractStatus.TERMINATED:
        raise BusinessRuleViolation(gettext("Shartnoma allaqachon bekor qilingan."))
    if contract.signed_on and terminated_on < contract.signed_on:
        raise BusinessRuleViolation(
            gettext("Bekor qilish sanasi imzolash sanasidan oldin boʻlishi mumkin emas.")
        )
    contract.status = ContractStatus.TERMINATED
    contract.terminated_on = terminated_on
    contract.termination_reason = reason[:255]
    contract.save(update_fields=["status", "terminated_on", "termination_reason", "updated_at"])
    return contract
