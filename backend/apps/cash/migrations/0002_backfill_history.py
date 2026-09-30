"""
Mavjud tarixni kassa jurnaliga ko'chiradi (docs/03 §13a — "Backfill").

Nega migratsiya, oddiy skript emas: jadvalni jonli bazaga qo'shish
sxema o'zgarishigina emas, ma'lumot o'zgarishi ham. Usiz mijoz
yangilanishdan keyin ochgan birinchi ekranda nol ko'radi va shundan
keyingi hech bir raqamga ishonmasligi mumkin — va haq bo'ladi.

**RLS ostida ishlaydi.** Kontekstsiz siyosat hech qanday qatorni
ko'rsatmaydi va migratsiya hech narsa qilmasdan "muvaffaqiyatli"
tugardi (docs/03 §6.3) — `attendance.0004_drop_late_status` da aynan
shu sabab bilan har bir tashkilot alohida aylanib chiqiladi.

**Idempotent:** har bir hujjat uchun yozuv bor-yo'qligi tekshiriladi,
shuning uchun qayta ishga tushirish ikkinchi nusxa yaratmaydi.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Any

from django.db import migrations
from django.utils import timezone

# Filial ochilganda yaratiladigan qoplar — `apps/cash/services.py` dagi
# `DEFAULT_ACCOUNTS` bilan bir xil. Migratsiya servisni ATAYLAB import
# qilmaydi: kelajakda o'zgargan kod eski migratsiyaning ma'nosini
# o'zgartirib yubormasligi kerak.
DEFAULT_ACCOUNTS: tuple[tuple[str, str, str], ...] = (
    ("Naqd kassa", "cash", "cash"),
    ("Terminal", "terminal", "terminal"),
    ("Bank hisobi", "bank", "bank_transfer"),
    ("Payme / Click", "ewallet", "online"),
)

# `card` nomi keyingi migratsiyada `terminal` ga o'zgaradi; bu yerda
# ikkalasi ham qabul qilinadi, aks holda ikki migratsiyaning tartibi
# bir-biriga bog'lanib qolardi.
METHOD_TO_KIND = {
    "cash": "cash",
    "card": "terminal",
    "terminal": "terminal",
    "bank_transfer": "bank",
    "online": "ewallet",
}


def _aware(value: Any) -> Any:
    """`date` → kun boshidagi `datetime`, vaqt mintaqasi bilan."""
    if isinstance(value, datetime):
        return value
    return timezone.make_aware(datetime.combine(value, time.min))


def _backfill_organization(apps: Any, organization_id: Any) -> None:
    Branch = apps.get_model("branches", "Branch")
    CashAccount = apps.get_model("cash", "CashAccount")
    CashMovement = apps.get_model("cash", "CashMovement")
    Payment = apps.get_model("finance", "Payment")
    Expense = apps.get_model("expenses", "Expense")
    EmployeeAdvance = apps.get_model("payroll", "EmployeeAdvance")

    # --- 1. Har bir filialga qoplar ---
    by_branch: dict[Any, dict[str, Any]] = {}
    for branch in Branch.objects.filter(organization_id=organization_id):
        accounts = {
            account.kind: account
            for account in CashAccount.objects.filter(branch_id=branch.id, is_active=True)
        }
        for name, kind, method in DEFAULT_ACCOUNTS:
            if kind in accounts:
                continue
            accounts[kind] = CashAccount.objects.create(
                id=uuid.uuid4(),
                organization_id=organization_id,
                branch_id=branch.id,
                name=name,
                kind=kind,
                handles_method=method,
                is_active=True,
            )
        by_branch[branch.id] = accounts

    if not by_branch:
        return

    def account_for(branch_id: Any, kind: str) -> Any:
        accounts = by_branch.get(branch_id) or {}
        return accounts.get(kind) or accounts.get("cash")

    known = set(
        CashMovement.objects.filter(organization_id=organization_id).values_list(
            "source_type", "source_id"
        )
    )
    rows: list[Any] = []

    def add(*, account, direction, amount, source_type, source_id, when, text) -> None:
        if account is None or (source_type, source_id) in known:
            return
        rows.append(
            CashMovement(
                id=uuid.uuid4(),
                organization_id=organization_id,
                branch_id=account.branch_id,
                cash_account_id=account.id,
                direction=direction,
                amount=amount,
                source_type=source_type,
                source_id=source_id,
                occurred_at=_aware(when),
                description=(text or "")[:255],
                is_active=True,
            )
        )

    # --- 2. Qabul qilingan to'lovlar (qaytarilganlari EMAS) ---
    for payment in Payment.objects.filter(
        organization_id=organization_id, reversed_at__isnull=True
    ).select_related("child"):
        child = payment.child
        name = f"{child.last_name} {child.first_name}".strip() if child else ""
        add(
            account=account_for(payment.branch_id, METHOD_TO_KIND.get(payment.method, "cash")),
            direction="in",
            amount=payment.amount,
            source_type="payment",
            source_id=payment.id,
            when=payment.paid_at,
            text=name or "To'lov",
        )

    # --- 3. Tasdiqlangan va to'langan chiqimlar ---
    # Hisobotlar bilan BIR XIL qoida (`expense_summary`): kutilayotgan
    # so'rov hali pul emas, shuning uchun u kassadan chiqmaydi.
    for expense in Expense.objects.filter(
        organization_id=organization_id, status__in=["approved", "paid"]
    ).select_related("category"):
        add(
            account=account_for(expense.branch_id, "cash"),
            direction="out",
            amount=expense.amount,
            source_type="expense",
            source_id=expense.id,
            when=expense.expense_date,
            text=getattr(expense.category, "name", "") or "Chiqim",
        )

    # --- 4. Berilgan avanslar ---
    for advance in EmployeeAdvance.objects.filter(
        organization_id=organization_id
    ).select_related("employee"):
        employee = advance.employee
        name = f"{employee.last_name} {employee.first_name}".strip() if employee else ""
        add(
            account=account_for(advance.branch_id, "cash"),
            direction="out",
            amount=advance.amount,
            source_type="advance",
            source_id=advance.id,
            when=advance.paid_on,
            text=f"Avans: {name}".strip(),
        )

    CashMovement.objects.bulk_create(rows, batch_size=500)


def backfill(apps: Any, schema_editor: Any) -> None:
    connection = schema_editor.connection
    Organization = apps.get_model("organizations", "Organization")

    if connection.vendor != "postgresql":  # pragma: no cover — testlarda Postgres
        for organization_id in Organization.objects.values_list("id", flat=True):
            _backfill_organization(apps, organization_id)
        return

    from apps.core.rls import (
        apply_tenant_setting,
        clear_tenant_setting,
        disable_platform_mode,
        enable_platform_mode,
    )

    enable_platform_mode()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM organization")
            organization_ids = [row[0] for row in cursor.fetchall()]
    finally:
        disable_platform_mode()

    try:
        for organization_id in organization_ids:
            apply_tenant_setting(organization_id)
            _backfill_organization(apps, organization_id)
    finally:
        clear_tenant_setting()


def unbackfill(apps: Any, schema_editor: Any) -> None:
    """
    Orqaga yo'l faqat shu migratsiya yozgan turlarni o'chiradi.

    Qoplarning o'zi qoladi: ularni o'chirish `expense.cash_account_id`
    havolasini buzardi, va bo'sh qop hech kimga zarar qilmaydi.
    """
    connection = schema_editor.connection
    CashMovement = apps.get_model("cash", "CashMovement")
    kinds = ["payment", "expense", "advance"]

    if connection.vendor != "postgresql":  # pragma: no cover
        CashMovement.objects.filter(source_type__in=kinds).delete()
        return

    from apps.core.rls import enable_platform_mode, disable_platform_mode

    enable_platform_mode()
    try:
        CashMovement.objects.filter(source_type__in=kinds).delete()
    finally:
        disable_platform_mode()


class Migration(migrations.Migration):
    dependencies = [
        ("cash", "0001_initial"),
        ("expenses", "0003_expense_cash_account"),
        ("finance", "0001_initial"),
        ("payroll", "0003_payrollitem_advance_employeeadvance"),
        ("branches", "0002_branch_tenancy_guard"),
        ("organizations", "0001_initial"),
    ]

    operations = [migrations.RunPython(backfill, unbackfill)]
