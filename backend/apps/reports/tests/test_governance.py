"""
Boshqaruv modellari A / B / C (Bosqich 13.6, brif §2, §5.4, §8; testlar
1, 9, 16, 17, 18).

Raqamlar modelga bog'liq emas — faqat jarayon. A: ega o'zi tasdiqlaydi.
B: boshqaruvchi topshiradi, rahbar savol beradi, qaytaradi yoki qabul
qiladi. C: filiallar topshiradi, ega konsolidatsiyani tasdiqlaydi.
Topshirilgan nusxa o'zgarmaydi; boshqaruvchi raqamni o'zgartira olmaydi;
ulashish havolasi faqat o'qish uchun, muddatli, suv belgili.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cash import services as cash
from apps.cash.models import CashAccount
from apps.children.models import Child
from apps.core.tenancy import organization_context
from apps.finance import services as finance
from apps.finance.models import TariffPlan
from apps.reports import pack

pytestmark = pytest.mark.django_db

YEAR, MONTH = 2026, 9
FEE = Decimal("3050000")
PERIOD = {"year": YEAR, "month": MONTH}


@pytest.fixture
def org(tenant_a: Any) -> Any:
    tenant_a.fund("500000000", kind="all")
    return tenant_a


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    from apps.intelligence import alerts

    messages: list[tuple[str, str]] = []
    monkeypatch.setattr(alerts, "_send", lambda chat, text: messages.append((chat, text)))
    monkeypatch.setattr(alerts, "transaction", SimpleNamespace(on_commit=lambda fn: fn()))
    return messages


def _ctx(tenant: Any) -> Any:
    return organization_context(tenant.organization.id)


def _at(day: date) -> datetime:
    return timezone.make_aware(datetime.combine(day, time(10)))


def _children(tenant: Any, count: int, branch: Any = None) -> list[Child]:
    branch = branch or tenant.branch
    with _ctx(tenant):
        tariff, _ = TariffPlan.objects.get_or_create(
            organization=tenant.organization,
            branch=branch,
            name="Asosiy",
            defaults={"amount": FEE},
        )
        kids = [
            Child.objects.create(
                organization=tenant.organization,
                branch=branch,
                first_name=f"Bola{index}",
                last_name=f"Filial{branch.code}",
                date_of_birth=date(2021, 3, 14),
                gender="male",
                tariff=tariff,
                is_existing_client=True,
                enrolled_on=date(2025, 9, 1),
            )
            for index in range(count)
        ]
        for child in kids:
            finance.issue_invoice(child=child, period_year=YEAR, period_month=MONTH)
        return kids


def _pay(tenant: Any, child: Child, amount: Decimal, day: date = date(2026, 9, 10)) -> Any:
    with _ctx(tenant):
        return finance.record_payment(
            child=child,
            amount=amount,
            method="cash",
            paid_at=_at(day),
            backdate_reason="Test tarixi",
        )


def _setting(tenant: Any, key: str, value: Any, branch: Any = None) -> None:
    from apps.settings_app.services import set_setting

    with _ctx(tenant):
        set_setting(organization=tenant.organization, key=key, value=value, branch=branch)


def _user(tenant: Any, role: str, email: str, *, finance_center: bool = False) -> Any:
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import Permission, RolePermission, User

    with _ctx(tenant):
        role_row = tenant.role(role)
        if finance_center:
            RolePermission.objects.get_or_create(
                role=role_row, permission=Permission.objects.get(code="reports.finance")
            )
        user = User.objects.create_user(
            email=email,
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=email.split("@")[0].title(),
            organization=tenant.organization,
            role=role_row,
            branch=tenant.branch if role != "org_owner" else None,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    client.user = user  # type: ignore[attr-defined]
    return client


def _review(client: Any, **extra: Any) -> dict[str, Any]:
    response = client.get("/api/v1/reports/review", {**PERIOD, **extra})
    assert response.status_code == 200, response.content
    return response.json()["data"]


def _post(client: Any, path: str, body: dict[str, Any] | None = None) -> Any:
    return client.post(f"/api/v1/reports/review/{path}", {**PERIOD, **(body or {})}, format="json")


def _explain_blockers(client: Any) -> None:
    """Qizil tekshiruv va "Diqqat"ga izoh — topshirish sharti."""
    for blocker in _review(client)["blockers"]:
        response = _post(client, "note", {"path": blocker["path"], "text": "Sababi maʼlum"})
        assert response.status_code == 201, response.content


@pytest.fixture
def b_model(org: Any) -> Any:
    _setting(org, "governance.model", "B")
    kids = _children(org, 3)
    for kid in kids[:2]:
        _pay(org, kid, FEE)
    return org


@pytest.fixture
def manager(b_model: Any) -> Any:
    return _user(b_model, "manager", "boshqaruvchi@alfa.uz", finance_center=True)


# --- 1: uch model — bir xil raqamlar ---


def test_1_the_three_models_give_the_same_numbers(org: Any):
    kids = _children(org, 3)
    _pay(org, kids[0], FEE)
    client = org.client()
    checksums = []
    for model in ("A", "B", "C"):
        _setting(org, "governance.model", model)
        data = client.get("/api/v1/reports/pack", PERIOD).json()["data"]
        checksums.append(data["checksum"])
        assert _review(client)["model"] == model
    assert len(set(checksums)) == 1


def test_the_model_defaults_to_a(org: Any):
    assert _review(org.client())["model"] == "A"


# --- A model ---


def test_a_model_the_owner_approves_and_a_frozen_copy_is_kept(org: Any):
    kids = _children(org, 2)
    _pay(org, kids[0], FEE)
    client = org.client()

    refused = _post(client, "approve")
    assert refused.status_code == 422  # izohsiz qizil tekshiruvlar bor
    _explain_blockers(client)
    approved = _post(client, "approve")
    assert approved.status_code == 201, approved.content

    review = _review(client)
    assert review["status"] == "accepted"
    assert review["snapshot"]["version"] == 1
    assert [event["kind"] for event in review["events"]][-1] == "approve"


def test_a_model_has_no_submission(org: Any):
    assert _post(org.client(), "submit").status_code == 422


# --- B model ---


def test_9_b_model_will_not_submit_with_an_unexplained_red_check(b_model: Any, manager: Any):
    review = _review(manager)
    assert review["status"] == "draft"
    assert review["ready"] is False
    paths = {blocker["path"] for blocker in review["blockers"]}
    assert "checks:month_closed" in paths

    refused = _post(manager, "submit")
    assert refused.status_code == 422
    assert "Oy yopilgan" in refused.json()["error"]["message"]


def test_an_attention_item_needs_a_note_before_submitting(b_model: Any, manager: Any):
    from apps.expenses.models import Expense, ExpenseCategory
    from apps.expenses.services import approve_expense

    with _ctx(b_model):
        category = ExpenseCategory.objects.create(
            organization=b_model.organization, branch=b_model.branch, name="Taʼmir"
        )
        expense = Expense.objects.create(
            organization=b_model.organization,
            branch=b_model.branch,
            category=category,
            amount=Decimal("2500000"),
            expense_date=date(2026, 9, 12),
            cash_account=CashAccount.objects.get(branch=b_model.branch, kind="cash"),
        )
        approve_expense(expense=expense, approved_by=b_model.owner)

    paths = {blocker["path"] for blocker in _review(manager)["blockers"]}
    assert f"attention:expense_without_document:expense:{expense.id}" in paths


def test_b_model_submit_question_answer_accept(b_model: Any, manager: Any, sent: list):
    from apps.accounts.models import User

    with _ctx(b_model):
        User.objects.filter(pk=b_model.owner.pk).update(telegram_chat_id="9001")
    owner = b_model.client()
    _explain_blockers(manager)

    submitted = _post(manager, "submit")
    assert submitted.status_code == 201, submitted.content
    review = _review(owner)
    assert review["status"] == "submitted"
    assert review["snapshot"]["version"] == 1
    assert any("topshirildi" in text.lower() for _chat, text in sent)

    asked = _post(owner, "question", {"path": "revenue.chain.collected", "text": "Nega kam?"})
    assert asked.status_code == 201, asked.content
    assert _review(owner)["status"] == "question"

    blocked = _post(owner, "accept")
    assert blocked.status_code == 422  # javobsiz savol bor

    question_id = asked.json()["data"]["id"]
    answered = _post(
        manager, "answer", {"question": question_id, "text": "Ikki oila oy oxirida toʻlaydi"}
    )
    assert answered.status_code == 201, answered.content
    assert _review(owner)["status"] == "submitted"

    accepted = _post(owner, "accept")
    assert accepted.status_code == 201, accepted.content
    review = _review(owner)
    assert review["status"] == "accepted"
    thread = [event for event in review["events"] if event["path"] == "revenue.chain.collected"]
    assert [event["kind"] for event in thread] == ["question", "answer"]
    assert thread[1]["parent"] == question_id


def test_b_model_return_needs_a_reason_and_resubmission_makes_a_new_version(
    b_model: Any, manager: Any
):
    owner = b_model.client()
    _explain_blockers(manager)
    _post(manager, "submit")

    assert _post(owner, "return", {"text": ""}).status_code == 422
    assert _post(owner, "return", {"text": "Bank koʻchirmasi yoʻq"}).status_code == 201
    assert _review(owner)["status"] == "returned"

    with _ctx(b_model):
        kid = Child.objects.filter(organization=b_model.organization).order_by("first_name").last()
    _pay(b_model, kid, FEE)
    _explain_blockers(manager)
    again = _post(manager, "submit")
    assert again.status_code == 201, again.content

    review = _review(owner)
    assert review["status"] == "resubmitted"
    assert review["snapshot"]["version"] == 2
    assert review["accepted_by"] == []


def test_every_leader_accepts_separately_when_configured(b_model: Any, manager: Any):
    _setting(b_model, "governance.acceptors", "owner,director")
    director = _user(b_model, "director", "direktor@alfa.uz")
    owner = b_model.client()
    _explain_blockers(manager)
    _post(manager, "submit")

    assert _post(owner, "accept").status_code == 201
    review = _review(owner)
    assert review["status"] == "submitted"
    assert len(review["accepted_by"]) == 1

    assert _post(director, "accept").status_code == 201
    assert _review(owner)["status"] == "accepted"


def test_16_a_reversal_after_submission_shows_a_change_and_keeps_the_old_version(
    b_model: Any, manager: Any
):
    owner = b_model.client()
    _explain_blockers(manager)
    _post(manager, "submit")

    with _ctx(b_model):
        from apps.finance.models import Payment

        payment = Payment.objects.filter(organization=b_model.organization).first()
        finance.reverse_payment(payment=payment, reason="Xato kiritilgan")

    review = _review(owner)
    assert review["changed"] is True
    assert review["snapshot"]["version"] == 1


def test_the_deadline_is_the_fifth_of_next_month(b_model: Any, manager: Any):
    assert _review(manager)["deadline"] == "2026-10-05"
    _setting(b_model, "governance.deadline_day", 10)
    assert _review(manager)["deadline"] == "2026-10-10"


def test_a_late_report_reminds_the_owner_once(b_model: Any, sent: list, monkeypatch: Any):
    from apps.accounts.models import User
    from apps.reports import tasks

    with _ctx(b_model):
        User.objects.filter(pk=b_model.owner.pk).update(telegram_chat_id="9001")
    monkeypatch.setattr(tasks.timezone, "localdate", lambda: date(2026, 10, 7))

    assert tasks.remind_late_reports()["reminded"] == 1
    assert any("muddat" in text.lower() for _chat, text in sent)
    assert tasks.remind_late_reports()["reminded"] == 0


def test_a_report_on_time_is_not_late(b_model: Any, sent: list, monkeypatch: Any):
    from apps.reports import tasks

    monkeypatch.setattr(tasks.timezone, "localdate", lambda: date(2026, 10, 3))
    assert tasks.remind_late_reports()["reminded"] == 0


# --- 17: huquqlar ---


def test_17_the_manager_cannot_change_a_number(b_model: Any, manager: Any):
    from apps.reports.models import ReportSnapshot

    _explain_blockers(manager)
    _post(manager, "submit")

    # Raqamni o'zgartiradigan endpoint umuman yo'q: egasi uchun ham 405;
    # boshqaruvchi undan oldin ruxsatda to'xtaydi (403).
    owner = b_model.client()
    for method in ("put", "patch", "delete"):
        for client, expected in ((manager, (403, 405)), (owner, (405,))):
            response = getattr(client, method)("/api/v1/reports/pack", PERIOD, format="json")
            assert response.status_code in expected

    with _ctx(b_model):
        snapshot = ReportSnapshot.objects.get()
        with pytest.raises(DatabaseError), transaction.atomic():
            ReportSnapshot.objects.filter(pk=snapshot.pk).update(
                data={"sections": []}, checksum="0" * 64
            )
        with pytest.raises(DatabaseError), transaction.atomic():
            ReportSnapshot.objects.filter(pk=snapshot.pk).delete()


def test_17_the_manager_cannot_accept_return_or_ask(b_model: Any, manager: Any):
    _explain_blockers(manager)
    _post(manager, "submit")
    for path, body in (
        ("accept", {}),
        ("return", {"text": "Oʻzim"}),
        ("question", {"path": "summary", "text": "?"}),
    ):
        assert _post(manager, path, body).status_code == 403


def test_17_salaries_by_name_stay_with_payroll_rights(b_model: Any, manager: Any):
    from apps.hr.models import Employee
    from apps.payroll import services as payroll

    with _ctx(b_model):
        Employee.objects.create(
            organization=b_model.organization,
            branch=b_model.branch,
            first_name="Salima",
            last_name="Karimova",
            hire_date=date(2025, 1, 10),
            base_salary=Decimal("4000000"),
        )
        run = payroll.create_run(
            organization=b_model.organization,
            branch=b_model.branch,
            period_year=YEAR,
            period_month=MONTH,
        )
        payroll.finalize_run(run=run)

    opened = manager.get("/api/v1/reports/pack", PERIOD)
    assert opened.status_code == 200
    payroll_section = next(s for s in opened.json()["data"]["sections"] if s["key"] == "payroll")
    assert Decimal(payroll_section["accrued"]) == Decimal("4000000")
    assert "Karimova" not in json.dumps(opened.json())
    assert manager.get("/api/v1/payroll/runs").status_code == 403


def test_17_nobody_below_the_owner_can_restrict_the_owner(org: Any):
    director = _user(org, "director", "direktor@alfa.uz")
    owner_role = org.role("org_owner")
    response = director.put(
        f"/api/v1/roles/{owner_role.id}/permissions",
        {"permissions": ["children.read"]},
        format="json",
    )
    assert response.status_code in (403, 404)


def test_17_who_opened_the_report_is_in_the_history(b_model: Any, manager: Any):
    manager.get("/api/v1/reports/pack", PERIOD)
    opens = _review(b_model.client())["opens"]
    assert any(row["user"] == manager.user.full_name for row in opens)


def test_without_finance_rights_the_manager_still_cannot_open_the_pack(b_model: Any):
    plain = _user(b_model, "manager", "oddiy@alfa.uz")
    assert plain.get("/api/v1/reports/pack", PERIOD).status_code == 403
    assert plain.get("/api/v1/reports/review", PERIOD).status_code == 403


@pytest.mark.tenancy
def test_another_tenants_review_never_shows(b_model: Any, manager: Any, tenant_b: Any):
    owner = b_model.client()
    _explain_blockers(manager)
    asked_on = _post(manager, "submit")
    assert asked_on.status_code == 201
    question = _post(owner, "question", {"path": "summary", "text": "?"}).json()["data"]["id"]

    other = tenant_b.client()
    assert _review(other)["events"] == []
    answer = _post(other, "answer", {"question": question, "text": "Begona"})
    assert answer.status_code == 404


# --- Ulashish havolasi ---


def _approved(org: Any) -> Any:
    kids = _children(org, 2)
    _pay(org, kids[0], FEE)
    client = org.client()
    _explain_blockers(client)
    assert _post(client, "approve").status_code == 201
    return client


def test_a_share_link_opens_a_watermarked_pdf_until_it_expires(org: Any):
    client = _approved(org)
    created = client.post(
        "/api/v1/reports/review/share", {**PERIOD, "label": "Bank", "days": 7}, format="json"
    )
    assert created.status_code == 201, created.content
    url = created.json()["data"]["url"]
    token = url.rstrip("/").split("/")[-1]

    public = APIClient().get(f"/api/v1/public/reports/{token}")
    assert public.status_code == 200
    assert public["Content-Type"] == "application/pdf"
    assert b"%PDF" in b"".join(public.streaming_content)[:8]

    links = _review(client)["share_links"]
    assert links[0]["opened"] == 1
    assert links[0]["label"] == "Bank"

    from apps.reports.models import ReportShareLink

    with _ctx(org):
        ReportShareLink.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    assert APIClient().get(f"/api/v1/public/reports/{token}").status_code == 404


def test_a_revoked_link_stops_working(org: Any):
    client = _approved(org)
    created = client.post(
        "/api/v1/reports/review/share", {**PERIOD, "label": "Investor"}, format="json"
    ).json()["data"]
    token = created["url"].rstrip("/").split("/")[-1]
    revoked = client.post(f"/api/v1/reports/review/share/{created['id']}/revoke")
    assert revoked.status_code == 200
    assert APIClient().get(f"/api/v1/public/reports/{token}").status_code == 404


def test_only_a_frozen_report_can_be_shared(org: Any):
    response = org.client().post(
        "/api/v1/reports/review/share", {**PERIOD, "label": "Bank"}, format="json"
    )
    assert response.status_code == 422


def test_a_made_up_token_is_not_found(org: Any):
    from apps.children.telegram import build_code

    fake = build_code(org.organization.id)
    assert APIClient().get(f"/api/v1/public/reports/{fake}").status_code == 404
    assert APIClient().get("/api/v1/public/reports/garbage").status_code == 404


@pytest.mark.tenancy
def test_a_share_link_cannot_be_revoked_by_another_tenant(org: Any, tenant_b: Any):
    client = _approved(org)
    created = client.post(
        "/api/v1/reports/review/share", {**PERIOD, "label": "Bank"}, format="json"
    ).json()["data"]
    response = tenant_b.client().post(f"/api/v1/reports/review/share/{created['id']}/revoke")
    assert response.status_code == 404


# --- 18: tarmoq va konsolidatsiya ---


@pytest.fixture
def two_branches(org: Any) -> tuple[Any, Any, Any]:
    from apps.branches.models import Branch
    from apps.cash.services import ensure_branch_accounts

    with _ctx(org):
        second = Branch.objects.create(organization=org.organization, name="Gorkiy", code="GRK")
        ensure_branch_accounts(branch=second)
    first_kids = _children(org, 2)
    second_kids = _children(org, 3, branch=second)
    _pay(org, first_kids[0], FEE)
    for kid in second_kids:
        _pay(org, kid, FEE)
    with _ctx(org):
        source = CashAccount.objects.get(branch=second, kind="cash")
        target = CashAccount.objects.get(branch=org.branch, kind="cash")
        cash.transfer(
            source=source,
            target=target,
            amount=Decimal("1000000"),
            occurred_at=_at(date(2026, 9, 20)),
        )
    return org, org.branch, second


def test_18_consolidation_is_the_sum_without_inter_branch_transfers(two_branches: Any):
    from apps.reports import money

    org, first, second = two_branches
    with _ctx(org):
        flows = [
            money.cash_flow(
                organization_id=org.organization.id, year=YEAR, month=MONTH, branch_id=branch
            )
            for branch in (first.id, second.id, None)
        ]
        packs = [
            pack.build(organization_id=org.organization.id, year=YEAR, month=MONTH, branch_id=b)
            for b in (first.id, second.id, None)
        ]

    def collected(data: dict[str, Any]) -> Decimal:
        revenue = next(s for s in data["sections"] if s["key"] == "revenue")
        return Decimal(next(r["value"] for r in revenue["chain"] if r["id"] == "collected"))

    assert collected(packs[2]) == collected(packs[0]) + collected(packs[1])
    for key in ("tuition", "total"):
        assert Decimal(flows[2]["inflows"][key]) == Decimal(flows[0]["inflows"][key]) + Decimal(
            flows[1]["inflows"][key]
        )

    assert Decimal(flows[0]["transfers"]["inter_branch_in"]) == Decimal("1000000")
    assert Decimal(flows[1]["transfers"]["inter_branch_out"]) == Decimal("1000000")
    assert Decimal(flows[2]["transfers"]["eliminated"]) == Decimal("1000000")
    assert Decimal(flows[2]["transfers"]["in"]) == 0
    assert Decimal(flows[2]["transfers"]["out"]) == 0
    assert all(flow["check"]["ok"] for flow in flows)
    assert Decimal(flows[2]["closing"]) == Decimal(flows[0]["closing"]) + Decimal(
        flows[1]["closing"]
    )


def test_the_network_table_marks_the_best_and_the_worst(two_branches: Any):
    org, first, second = two_branches
    data = org.client().get("/api/v1/reports/network", PERIOD).json()["data"]
    rows = {row["branch_id"]: row for row in data["rows"]}
    assert set(rows) == {str(first.id), str(second.id)}
    assert Decimal(rows[str(second.id)]["collection_rate"]) == Decimal("100.0")
    assert Decimal(rows[str(first.id)]["collection_rate"]) == Decimal("50.0")
    assert data["best"]["collection_rate"] == str(second.id)
    assert data["worst"]["collection_rate"] == str(first.id)
    assert Decimal(data["eliminated_transfers"]) == Decimal("1000000")


def test_c_model_consolidation_waits_for_every_branch(two_branches: Any):
    org, first, second = two_branches
    _setting(org, "governance.model", "C")
    owner = org.client()
    _explain_blockers(owner)
    refused = _post(owner, "approve")
    assert refused.status_code == 422
    assert "Gorkiy" in refused.json()["error"]["message"]

    for branch in (first, second):
        scoped = {"branch": str(branch.id)}
        for blocker in _review(owner, **scoped)["blockers"]:
            _post(owner, "note", {**scoped, "path": blocker["path"], "text": "Maʼlum"})
        assert _post(owner, "submit", scoped).status_code == 201
        assert _post(owner, "accept", scoped).status_code == 201

    _explain_blockers(owner)
    assert _post(owner, "approve").status_code == 201


def test_a_branch_bound_manager_cannot_see_the_network(two_branches: Any):
    org, _first, _second = two_branches
    reader = _user(org, "manager", "filial@alfa.uz", finance_center=True)
    assert reader.get("/api/v1/reports/network", PERIOD).status_code == 403
