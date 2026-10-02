"""
`/api/v1/insights` (docs/07 §11, Appendix B).

Cross-tenant: B tashkilotining egasi A'ning insight'iga 404 oladi — 403
emas (CLAUDE.md, 2-invariant). Amallar audit yozadi.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.core.tenancy import organization_context
from apps.intelligence.models import Insight, InsightStatus

pytestmark = pytest.mark.django_db


def _row(tenant, **overrides) -> Insight:
    fields = {
        "organization": tenant.organization,
        "branch": tenant.branch,
        "type": "payment_delay",
        "severity": "warning",
        "status": InsightStatus.NEW,
        "subject_type": "branch",
        "subject_id": tenant.branch.id,
        "evidence": {"children_count": 4, "max_days_overdue": 22},
        "recommendation_key": "payment_delay.review_debtors",
        "deep_link": "/debtors?overdue_days=15",
        "generated_at": timezone.now(),
    }
    fields.update(overrides)
    with organization_context(tenant.organization.id):
        return Insight.objects.create(**fields)


def _detail(name: str, row: Insight) -> str:
    return reverse(f"v1:insight-{name}", kwargs={"pk": row.id})


class TestList:
    def test_defaults_to_open_and_all_shows_history(self, tenant_a):
        _row(tenant_a)
        _row(tenant_a, status=InsightStatus.RESOLVED, resolved_at=timezone.now())
        client = tenant_a.client()

        default = client.get(reverse("v1:insight-list")).json()["data"]
        assert [r["status"] for r in default] == ["new"]

        everything = client.get(reverse("v1:insight-list"), {"status": "all"}).json()["data"]
        assert sorted(r["status"] for r in everything) == ["new", "resolved"]

    def test_serializer_exposes_snapshot_not_names(self, tenant_a):
        row = _row(tenant_a)
        data = tenant_a.client().get(_detail("detail", row)).json()["data"]
        assert data["evidence"] == {"children_count": 4, "max_days_overdue": 22}
        assert data["deep_link"] == "/debtors?overdue_days=15"
        assert data["is_open"] is True
        assert "children" not in data or "full_name" not in str(data)

    def test_cashier_reads_but_cannot_close(self, tenant_a):
        """Kassirda `dashboard.read` bor, `dashboard.update` yoʻq → amal 403."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        row = _row(tenant_a)
        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="cashier@alfa.uz",
                password="Kuchli-Parol-2026",
                full_name="Kassir",
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                role=tenant_a.role("cashier"),
            )
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {issue_token_pair(cashier)['access']}")
        assert client.get(reverse("v1:insight-list")).status_code == 200
        assert client.post(_detail("resolve", row)).status_code == 403


class TestCrossTenant:
    @pytest.mark.tenancy
    def test_other_tenant_gets_404_on_every_route(self, tenant_a, tenant_b):
        row = _row(tenant_a)
        stranger = tenant_b.client()
        assert stranger.get(_detail("detail", row)).status_code == 404
        for name in ("seen", "resolve", "dismiss"):
            assert stranger.post(_detail(name, row)).status_code == 404, name
        # Ro'yxatda ham ko'rinmaydi.
        assert stranger.get(reverse("v1:insight-list")).json()["data"] == []
        with organization_context(tenant_a.organization.id):
            assert Insight.objects.get(pk=row.pk).status == InsightStatus.NEW


class TestActions:
    def test_seen_is_idempotent(self, tenant_a):
        row = _row(tenant_a)
        client = tenant_a.client()
        first = client.post(_detail("seen", row)).json()["data"]
        second = client.post(_detail("seen", row)).json()["data"]
        assert first["status"] == "seen" and first["seen_at"] == second["seen_at"]

    def test_resolve_closes_and_writes_audit(self, tenant_a):
        row = _row(tenant_a)
        response = tenant_a.client().post(_detail("resolve", row))
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "resolved" and data["is_open"] is False
        with organization_context(tenant_a.organization.id):
            log = AuditLog.objects.get(action="insight.resolve", entity_id=row.id)
            assert log.actor_id == tenant_a.owner.id

    def test_dismiss_sets_seven_day_window_and_writes_audit(self, tenant_a):
        row = _row(tenant_a)
        data = tenant_a.client().post(_detail("dismiss", row)).json()["data"]
        assert data["status"] == "dismissed"
        with organization_context(tenant_a.organization.id):
            row.refresh_from_db()
            assert row.dismissed_until - row.dismissed_at == timedelta(days=7)
            assert AuditLog.objects.filter(action="insight.dismiss", entity_id=row.id).exists()

    def test_closing_closed_row_is_422(self, tenant_a):
        row = _row(tenant_a, status=InsightStatus.RESOLVED, resolved_at=timezone.now())
        response = tenant_a.client().post(_detail("dismiss", row))
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "BUSINESS_RULE_VIOLATION"


class TestBriefing:
    def test_briefing_shape(self, tenant_a):
        _row(tenant_a, severity="critical")
        _row(tenant_a, type="attendance_drop", subject_type="group", subject_id=tenant_a.branch.id)
        _row(tenant_a, status=InsightStatus.DISMISSED, dismissed_at=timezone.now())
        data = tenant_a.client().get(reverse("v1:insight-briefing")).json()["data"]
        assert data["date"] == timezone.localdate().isoformat()
        assert data["open_count"] == 2
        assert [i["severity"] for i in data["insights"]][0] == "critical"
        assert isinstance(data["checks"]["working_day"], bool)
        # Egasi filial tanlamagan — har bir filial alohida; faol bola yo'q → None.
        assert data["checks"]["attendance_by_branch"] == {str(tenant_a.branch.id): None}

    def test_briefing_for_a_branch(self, tenant_a):
        data = (
            tenant_a.client()
            .get(reverse("v1:insight-briefing"), {"branch": str(tenant_a.branch.id)})
            .json()["data"]
        )
        assert "attendance" in data["checks"] and "attendance_by_branch" not in data["checks"]
