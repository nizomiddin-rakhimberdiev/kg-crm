"""
Reconcile va hayot sikli (docs/07 §9, Appendix B).

Bu yerdagi eng muhim test — `test_same_branch_same_type_cannot_have_two_open_rows`:
u BAZADAN `IntegrityError` kutadi, ilova mantiqidan emas. Ilova to'g'ri
bo'lsa ham, kafolat bazada bo'lishi shart — aks holda ikki parallel
generator ikkita qator yozardi.
"""

from __future__ import annotations

import threading
from datetime import timedelta
from uuid import uuid4

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.core.tenancy import organization_context
from apps.intelligence import services
from apps.intelligence.models import Insight, InsightStatus
from apps.intelligence.rules import InsightDraft

pytestmark = pytest.mark.django_db


def _draft(tenant, *, severity="warning", count=5) -> InsightDraft:
    return InsightDraft(
        type="payment_delay",
        severity=severity,
        subject_type="branch",
        subject_id=tenant.branch.id,
        evidence={"children_count": count, "as_of": "2026-09-17"},
        recommendation_key="payment_delay.review_debtors",
        deep_link="/debtors?overdue_days=15",
    )


def _row(tenant, **overrides) -> Insight:
    fields = {
        "organization": tenant.organization,
        "branch": tenant.branch,
        "type": "payment_delay",
        "severity": "warning",
        "status": InsightStatus.NEW,
        "subject_type": "branch",
        "subject_id": tenant.branch.id,
        "evidence": {"children_count": 1},
        "recommendation_key": "payment_delay.review_debtors",
        "deep_link": "/debtors?overdue_days=15",
        "generated_at": timezone.now(),
    }
    fields.update(overrides)
    return Insight.objects.create(**fields)


def _reconcile(tenant, drafts):
    return services.reconcile(
        organization=tenant.organization, branch_id=tenant.branch.id, drafts=drafts
    )


class TestDatabaseGuarantee:
    def test_same_branch_same_type_cannot_have_two_open_rows(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _row(tenant_a)
            with pytest.raises(IntegrityError), transaction.atomic():
                _row(tenant_a)  # ilova mantiqi CHETLAB o'tilgan — baza to'xtatadi

    def test_closed_row_does_not_block_a_new_open_one(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _row(tenant_a, status=InsightStatus.AUTO_RESOLVED, auto_resolved_at=timezone.now())
            _row(tenant_a)  # partial index faqat ochiqlar uchun
            assert Insight.objects.count() == 2

    def test_branch_level_subject_must_equal_branch(self, tenant_a):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            _row(tenant_a, subject_id=uuid4())

    def test_dismissed_until_only_on_dismissed_rows(self, tenant_a):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(IntegrityError),
            transaction.atomic(),
        ):
            _row(tenant_a, dismissed_until=timezone.now())

    def test_different_branches_each_get_one_open_row(self, tenant_a, tenant_b):
        with organization_context(tenant_a.organization.id):
            _row(tenant_a)
        with organization_context(tenant_b.organization.id):
            _row(tenant_b)
            assert Insight.objects.count() == 1  # RLS: faqat o'ziniki ko'rinadi


class TestReconcile:
    def test_creates_when_condition_present(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            result = _reconcile(tenant_a, [_draft(tenant_a)])
            assert result.created == 1
            row = Insight.objects.get()
            assert row.status == InsightStatus.NEW and row.evidence["children_count"] == 5

    def test_rerun_same_day_refreshes_not_duplicates(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a, count=5)])
            first = Insight.objects.get()
            result = _reconcile(tenant_a, [_draft(tenant_a, count=7, severity="critical")])
            assert result.created == 0 and result.refreshed == 1
            row = Insight.objects.get()
            assert row.id == first.id
            assert row.evidence["children_count"] == 7 and row.severity == "critical"
            assert row.refreshed_at is not None and row.status == InsightStatus.NEW

    def test_refresh_keeps_seen_status(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            services.mark_seen(insight=Insight.objects.get())
            _reconcile(tenant_a, [_draft(tenant_a, count=9)])
            assert Insight.objects.get().status == InsightStatus.SEEN

    def test_condition_absent_closes_open_row_as_auto_resolved(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            result = _reconcile(tenant_a, [])
            assert result.auto_resolved == 1
            row = Insight.objects.get()
            assert row.status == InsightStatus.AUTO_RESOLVED and row.auto_resolved_at is not None

    def test_condition_returns_after_auto_resolved_creates_new_row(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            _reconcile(tenant_a, [])
            result = _reconcile(tenant_a, [_draft(tenant_a)])
            assert result.created == 1
            assert Insight.objects.count() == 2  # tarix — qatorlar
            assert Insight.objects.filter(status=InsightStatus.NEW).count() == 1

    def test_engine_never_reopens_closed_rows(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            closed = Insight.objects.get()
            services.resolve(insight=closed, actor=tenant_a.owner)
            _reconcile(tenant_a, [_draft(tenant_a)])
            closed.refresh_from_db()
            assert closed.status == InsightStatus.RESOLVED
            assert (
                Insight.objects.filter(status=InsightStatus.NEW).exclude(id=closed.id).count() == 1
            )


class TestDismissSuppression:
    def _dismiss_current(self, tenant):
        row = Insight.objects.get(status__in=("new", "seen"))
        services.dismiss(insight=row, actor=tenant.owner)
        return row

    def test_dismissed_condition_is_suppressed_for_7_days(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            row = self._dismiss_current(tenant_a)
            assert row.dismissed_until - row.dismissed_at == timedelta(days=7)
            # 2–7-kunlar: shart davom etadi → yangi qator yo'q.
            for _ in range(6):
                result = _reconcile(tenant_a, [_draft(tenant_a)])
                assert result.created == 0 and result.suppressed == 1
            assert Insight.objects.count() == 1

    def test_dismissed_condition_reappears_after_window(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            row = self._dismiss_current(tenant_a)
            # Oynani "oʻtkazamiz".
            Insight.objects.filter(id=row.id).update(
                dismissed_until=timezone.now() - timedelta(seconds=1)
            )
            result = _reconcile(tenant_a, [_draft(tenant_a)])
            assert result.created == 1
            assert Insight.objects.count() == 2

    def test_dismissed_then_condition_absent_ends_episode(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            row = self._dismiss_current(tenant_a)
            result = _reconcile(tenant_a, [])
            assert result.episodes_ended == 1
            row.refresh_from_db()
            assert row.dismissed_until <= timezone.now()
            assert row.status == InsightStatus.DISMISSED  # holat o'zgarmaydi, faqat oyna yopiladi

    def test_dismissed_then_absent_then_present_creates_new_row_inside_window(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            self._dismiss_current(tenant_a)
            _reconcile(tenant_a, [])  # 3-kun: yo'qoldi
            result = _reconcile(tenant_a, [_draft(tenant_a)])  # 5-kun: qaytdi
            assert result.created == 1  # yangi epizod — 7 kun o'tmasa ham

    def test_resolved_has_no_suppression(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            _reconcile(tenant_a, [_draft(tenant_a)])
            services.resolve(insight=Insight.objects.get(), actor=tenant_a.owner)
            result = _reconcile(tenant_a, [_draft(tenant_a)])
            assert result.created == 1  # "hal qildim" — ma'lumot buni rad etdi


class TestUserActions:
    def test_seen_is_set_once(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            row = _row(tenant_a)
            services.mark_seen(insight=row)
            first = row.seen_at
            services.mark_seen(insight=row)
            assert row.seen_at == first and row.status == InsightStatus.SEEN

    def test_resolve_and_dismiss_write_audit_log(self, tenant_a):
        from apps.audit.models import AuditLog

        with organization_context(tenant_a.organization.id):
            a = _row(tenant_a)
            services.resolve(insight=a, actor=tenant_a.owner)
            b = _row(tenant_a)
            services.dismiss(insight=b, actor=tenant_a.owner)
            actions = set(
                AuditLog.objects.filter(entity_type="insight").values_list("action", flat=True)
            )
            assert actions == {"insight.resolve", "insight.dismiss"}

    def test_closing_a_closed_row_is_a_business_rule_violation(self, tenant_a):
        from apps.core.exceptions import BusinessRuleViolation

        with organization_context(tenant_a.organization.id):
            row = _row(tenant_a)
            services.resolve(insight=row, actor=tenant_a.owner)
            with pytest.raises(BusinessRuleViolation):
                services.dismiss(insight=row, actor=tenant_a.owner)


@pytest.mark.django_db(transaction=True)
class TestConcurrency:
    @pytest.fixture(autouse=True)
    def _plan(self, db):
        # `transaction=True` testlar jadvallarni TOZALAYDI — shu jumladan
        # migratsiya seed qilgan `subscription_plan` ni. Bu test finance'ning
        # poyga testidan keyin yursa, plansiz `tenant_a` ochilmaydi. Shu
        # sababli plan shu yerda ta'minlanadi (`finance/tests/test_concurrency`
        # naqshi).
        from datetime import date
        from decimal import Decimal

        from apps.subscriptions.models import SubscriptionPlan

        SubscriptionPlan.objects.get_or_create(
            code="standard",
            valid_from=date(2026, 1, 1),
            defaults={
                "name": "Standart",
                "currency": "UZS",
                "base_price": Decimal("500000.00"),
                "included_children": 50,
                "overage_step_children": 10,
                "overage_step_price": Decimal("80000.00"),
            },
        )

    def test_concurrent_generation_yields_one_row(self, tenant_a):
        """Ikki thread bir vaqtda — baza toʻxtatadi, yutqazgan refresh qiladi."""
        errors: list[BaseException] = []
        barrier = threading.Barrier(2)

        def worker():
            try:
                with organization_context(tenant_a.organization.id):
                    barrier.wait(timeout=5)
                    _reconcile(tenant_a, [_draft(tenant_a)])
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors, errors
        with organization_context(tenant_a.organization.id):
            assert Insight.objects.filter(status__in=("new", "seen")).count() == 1
