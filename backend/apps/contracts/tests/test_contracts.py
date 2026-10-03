"""
Contract templates and contracts (PLAN 6.5).

The rules that matter: a typo in a placeholder is caught when the template
is saved; a contract keeps the values it was made with even after the
tariff changes — the database refuses an edit; another kindergarten's
child, template or contract is 404.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.db import DatabaseError, transaction
from django.utils import timezone

from apps.children.models import Child, ChildGuardian, Guardian
from apps.contracts.models import Contract
from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

TEMPLATES = "/api/v1/contract-templates"
CONTRACTS = "/api/v1/contracts"
BODY = (
    "Shartnoma {{shartnoma.raqam}} ({{shartnoma.sana}})\n"
    "{{bogcha.nomi}}, STIR {{bogcha.stir}}\n"
    "Bola: {{bola.fio}}, tugʻilgan {{bola.tugilgan_sana}}\n"
    "Vasiy: {{vasiy.fio}}, {{vasiy.telefon}}\n"
    "Oylik toʻlov: {{tarif.summa}} soʻm"
)


def _child(tenant, *, fee: str = "1200000", with_guardian: bool = True) -> Child:
    from apps.finance.models import TariffPlan

    with organization_context(tenant.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            name=f"Tarif {fee}",
            amount=Decimal(fee),
        )
        child = Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 5, 4),
            gender="male",
            tariff=tariff,
            enrolled_on=date(2026, 9, 1),
        )
        if with_guardian:
            guardian = Guardian.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name="Nodira",
                last_name="Karimova",
                phone="+998901112233",
            )
            ChildGuardian.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                child=child,
                guardian=guardian,
                relation="mother",
                is_primary=True,
            )
    return child


def _template(client, body: str = BODY) -> dict:
    response = client.post(TEMPLATES, {"name": "Asosiy", "body": body}, format="json")
    assert response.status_code == 201, response.json()
    return response.json()["data"]


def _contract(client, child, template) -> dict:
    response = client.post(
        CONTRACTS, {"child_id": str(child.id), "template_id": template["id"]}, format="json"
    )
    assert response.status_code == 201, response.json()
    return response.json()["data"]


class TestTemplates:
    def test_an_unknown_placeholder_is_refused_on_save(self, tenant_a):
        response = tenant_a.client().post(
            TEMPLATES, {"name": "X", "body": "Bola: {{bola.fiO}} {{bola.manzil}}"}, format="json"
        )
        assert response.status_code == 422
        assert "{{bola.manzil}}" in response.json()["error"]["message"]

    def test_editing_the_text_bumps_the_version(self, tenant_a):
        client = tenant_a.client()
        template = _template(client)
        response = client.patch(
            f"{TEMPLATES}/{template['id']}", {"body": BODY + "\nQoʻshimcha"}, format="json"
        )
        assert response.json()["data"]["version"] == 2

    def test_the_editor_gets_the_server_list(self, tenant_a):
        names = tenant_a.client().get(f"{TEMPLATES}/placeholders").json()["data"]
        assert "bola.fio" in names and "tarif.summa" in names

    def test_deleting_switches_it_off(self, tenant_a):
        client = tenant_a.client()
        template = _template(client)
        assert client.delete(f"{TEMPLATES}/{template['id']}").status_code == 204
        assert client.get(TEMPLATES).json()["data"] == []

    def test_a_manager_cannot_edit_templates(self, tenant_a):
        from apps.online_payments.tests.test_endpoints import _member_client

        response = _member_client(tenant_a, "manager").post(
            TEMPLATES, {"name": "X", "body": "x"}, format="json"
        )
        assert response.status_code == 403


class TestContracts:
    def test_values_are_filled_in(self, tenant_a):
        client = tenant_a.client()
        child = _child(tenant_a)
        contract = _contract(client, child, _template(client))
        text = contract["rendered_text"]
        assert contract["number"] == f"SH-{timezone.localdate().year}-0001"
        assert "Valiyev Ali" in text and "04.05.2021" in text
        assert "Karimova Nodira" in text and "+998901112233" in text
        assert "1 200 000 soʻm" in text
        assert contract["status"] == "draft"

    def test_a_missing_value_prints_as_a_blank_to_fill_by_hand(self, tenant_a):
        client = tenant_a.client()
        contract = _contract(client, _child(tenant_a, with_guardian=False), _template(client))
        assert "Vasiy: __________, __________" in contract["rendered_text"]
        assert "STIR __________" in contract["rendered_text"]

    def test_numbers_grow(self, tenant_a):
        client = tenant_a.client()
        template = _template(client)
        child = _child(tenant_a)
        _contract(client, child, template)
        second = _contract(client, child, template)
        assert second["number"].endswith("-0002")

    def test_the_contract_keeps_its_values_after_the_tariff_changes(self, tenant_a):
        from apps.finance.models import TariffPlan

        client = tenant_a.client()
        child = _child(tenant_a)
        contract = _contract(client, child, _template(client))
        with organization_context(tenant_a.organization.id):
            TariffPlan.objects.filter(pk=child.tariff_id).update(amount=Decimal("2000000"))
        again = client.get(f"{CONTRACTS}/{contract['id']}").json()["data"]
        assert "1 200 000" in again["rendered_text"]

    def test_the_database_refuses_an_edit_of_the_text(self, tenant_a):
        client = tenant_a.client()
        contract = _contract(client, _child(tenant_a), _template(client))
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(DatabaseError),
            transaction.atomic(),
        ):
            Contract.objects.filter(pk=contract["id"]).update(rendered_text="boshqa matn")

    def test_sign_then_terminate(self, tenant_a):
        client = tenant_a.client()
        contract = _contract(client, _child(tenant_a), _template(client))
        today = timezone.localdate()
        signed = client.post(
            f"{CONTRACTS}/{contract['id']}/sign", {"signed_on": str(today)}, format="json"
        ).json()["data"]
        assert signed["status"] == "signed"
        assert (
            client.post(
                f"{CONTRACTS}/{contract['id']}/sign", {"signed_on": str(today)}, format="json"
            ).status_code
            == 422
        )
        ended = client.post(
            f"{CONTRACTS}/{contract['id']}/terminate",
            {"terminated_on": str(today), "reason": "Koʻchib ketdi"},
            format="json",
        ).json()["data"]
        assert ended["status"] == "terminated"

    def test_signing_in_the_future_is_refused(self, tenant_a):
        client = tenant_a.client()
        contract = _contract(client, _child(tenant_a), _template(client))
        tomorrow = timezone.localdate() + timedelta(days=1)
        response = client.post(
            f"{CONTRACTS}/{contract['id']}/sign", {"signed_on": str(tomorrow)}, format="json"
        )
        assert response.status_code == 422

    def test_list_by_child(self, tenant_a):
        client = tenant_a.client()
        template = _template(client)
        child = _child(tenant_a)
        _contract(client, child, template)
        rows = client.get(CONTRACTS, {"child": str(child.id)}).json()["data"]
        assert len(rows) == 1


class TestIsolation:
    def test_another_kindergartens_child_is_404(self, tenant_a, tenant_b):
        template = _template(tenant_a.client())
        foreign = _child(tenant_b)
        response = tenant_a.client().post(
            CONTRACTS, {"child_id": str(foreign.id), "template_id": template["id"]}, format="json"
        )
        assert response.status_code == 404

    def test_another_kindergartens_template_is_404(self, tenant_a, tenant_b):
        foreign_template = _template(tenant_b.client())
        response = tenant_a.client().post(
            CONTRACTS,
            {"child_id": str(_child(tenant_a).id), "template_id": foreign_template["id"]},
            format="json",
        )
        assert response.status_code == 404

    def test_another_kindergartens_contract_is_404(self, tenant_a, tenant_b):
        client_b = tenant_b.client()
        contract = _contract(client_b, _child(tenant_b), _template(client_b))
        client_a = tenant_a.client()
        assert client_a.get(f"{CONTRACTS}/{contract['id']}").status_code == 404
        response = client_a.post(
            f"{CONTRACTS}/{contract['id']}/sign",
            {"signed_on": str(timezone.localdate())},
            format="json",
        )
        assert response.status_code == 404


class TestRowScope:
    """ADR-21: a group's teacher reaches only her own groups' children."""

    def test_a_restricted_user_cannot_reach_other_groups_children(self, tenant_a, monkeypatch):
        client = tenant_a.client()
        template = _template(client)
        child = _child(tenant_a)
        made = _contract(client, child, template)

        monkeypatch.setattr("apps.children.scope.is_group_restricted", lambda user: True)
        monkeypatch.setattr("apps.children.scope.visible_group_ids", lambda user: set())
        response = client.post(
            CONTRACTS, {"child_id": str(child.id), "template_id": template["id"]}, format="json"
        )
        assert response.status_code == 404
        assert client.get(CONTRACTS).json()["data"] == []
        assert client.get(f"{CONTRACTS}/{made['id']}").status_code == 404
