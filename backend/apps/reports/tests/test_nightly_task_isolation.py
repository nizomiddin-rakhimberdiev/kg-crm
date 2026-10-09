"""
Bitta tashkilotning nosozligi qolganlarini toʻxtatmasin.

`recompute_balances` har kecha har bir bolaning balans keshini
ledger bilan solishtiradi — kesh siljishi jimgina yuz beradi va eng
yomon joyda, qarz talab qilishda chiqadi. `send_debt_reminders` esa
qarzdorlarga eslatma yuboradi.

Ikkalasi ham tashkilotlar boʻylab BITTA siklda aylanardi, himoyasiz:
ikkinchi tashkilotda xato chiqsa, uchinchisidan oxirigacha boʻlgan
hamma tashkilot oʻsha kechani umuman oʻtkazib yuborardi. Qayta
urinish ham yordam bermaydi — xato takrorlansa, roʻyxatning quyruq
qismi HECH QACHON tekshirilmaydi, va buni hech kim sezmaydi, chunki
tekshiruvning oʻzi jim.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from apps.reports import tasks

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


def test_one_bad_organization_does_not_stop_the_nightly_check(tenant_a: Any, tenant_b: Any):
    from apps.children.models import Child
    from apps.core.tenancy import organization_context

    for tenant in (tenant_a, tenant_b):
        with organization_context(tenant.organization.id):
            Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Ali",
                last_name="Valiyev",
                date_of_birth="2021-03-14",
                gender="male",
            )

    calls = {"n": 0}

    def _boom(child: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("ledger javob bermadi")
        return child.balance

    with (
        patch.object(tasks, "recompute_child_balance", _boom, create=True),
        patch("apps.finance.services.recompute_child_balance", _boom),
    ):
        result = tasks.recompute_balances()

    # Ikkinchi tashkilot baribir tekshirildi, birinchisi sanaldi.
    assert result["failed"] == 1
    assert result["checked"] >= 1


def test_a_failing_reminder_organization_does_not_block_the_rest(tenant_a: Any, tenant_b: Any):
    from apps.core.tenancy import organization_context
    from apps.settings_app.services import set_setting

    for tenant in (tenant_a, tenant_b):
        with organization_context(tenant.organization.id):
            set_setting(
                key="notifications.sms_enabled", value=True, organization=tenant.organization
            )

    calls = {"n": 0}

    def _boom(**kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("provayder javob bermadi")
        return []

    with patch("apps.notifications.services.queue_debt_reminders", side_effect=_boom):
        result = tasks.send_debt_reminders()

    assert result["failed"] == 1
