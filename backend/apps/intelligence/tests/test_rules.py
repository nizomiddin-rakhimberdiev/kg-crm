"""Qoidalar — sof, bazasiz. Chegaralar eng xavfli joy (docs/07 Appendix B)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from apps.intelligence.rules import GroupAttendance, OverdueChild, attendance_drop, payment_delay
from apps.intelligence.thresholds import AttendanceDropThresholds, PaymentDelayThresholds

AS_OF = date(2026, 9, 17)
BRANCH = uuid4()


def _overdue(days: int, amount: str = "1500000.00") -> OverdueChild:
    return OverdueChild(
        child_id=uuid4(),
        group_id=uuid4(),
        overdue_amount=Decimal(amount),
        days_overdue=days,
        invoices=1,
    )


class TestPaymentDelay:
    @pytest.mark.parametrize(("days", "fires"), [(14, False), (15, False), (16, True)])
    def test_payment_delay_boundary_14_15_16_days(self, days, fires):
        # Chegara `>`: 15 kun — hali emas, 16 — ha. `due_date < as_of - 15`
        # bilan bir xil ma'no.
        draft = payment_delay(
            branch_id=BRANCH, as_of=AS_OF, active_children=100, overdue=[_overdue(days)]
        )
        assert (draft is not None) is fires

    def test_no_overdue_means_no_insight(self):
        assert payment_delay(branch_id=BRANCH, as_of=AS_OF, active_children=50, overdue=[]) is None

    def test_payment_delay_severity_critical_by_days(self):
        draft = payment_delay(
            branch_id=BRANCH, as_of=AS_OF, active_children=100, overdue=[_overdue(45)]
        )
        assert draft is not None and draft.severity == "critical"
        draft = payment_delay(
            branch_id=BRANCH, as_of=AS_OF, active_children=100, overdue=[_overdue(44)]
        )
        assert draft is not None and draft.severity == "warning"

    def test_payment_delay_severity_critical_by_share(self):
        # 100 bola → 10 % = 10 bola. 9 → warning, 10 → critical.
        nine = [_overdue(20) for _ in range(9)]
        assert (
            payment_delay(branch_id=BRANCH, as_of=AS_OF, active_children=100, overdue=nine).severity
            == "warning"
        )  # type: ignore[union-attr]
        ten = [_overdue(20) for _ in range(10)]
        assert (
            payment_delay(branch_id=BRANCH, as_of=AS_OF, active_children=100, overdue=ten).severity
            == "critical"
        )  # type: ignore[union-attr]

    def test_payment_delay_severity_min_subjects_floor(self):
        # 12 bolali bog'cha: 10 % = 1.2 → pol 3. Bitta bola critical qilmaydi.
        one = [_overdue(20)]
        assert (
            payment_delay(branch_id=BRANCH, as_of=AS_OF, active_children=12, overdue=one).severity
            == "warning"
        )  # type: ignore[union-attr]
        three = [_overdue(20) for _ in range(3)]
        assert (
            payment_delay(branch_id=BRANCH, as_of=AS_OF, active_children=12, overdue=three).severity
            == "critical"
        )  # type: ignore[union-attr]

    def test_evidence_is_numbers_and_ids_only(self):
        draft = payment_delay(
            branch_id=BRANCH, as_of=AS_OF, active_children=100, overdue=[_overdue(30, "600000.00")]
        )
        assert draft is not None
        ev = draft.evidence
        assert ev["children_count"] == 1
        assert ev["total_overdue"] == "600000.00"
        assert ev["max_days_overdue"] == 30
        assert ev["critical_days_threshold"] == 45 and ev["critical_children_threshold"] == 10
        assert set(ev["children"][0]) == {
            "child_id",
            "group_id",
            "overdue_amount",
            "days_overdue",
            "invoices",
        }
        assert "name" not in str(ev).lower() and "phone" not in str(ev).lower()
        assert draft.subject_type == "branch" and draft.subject_id == BRANCH
        assert draft.deep_link == "/debtors?overdue_days=15"

    def test_evidence_rows_capped_but_count_true(self):
        many = [_overdue(20 + i) for i in range(60)]
        draft = payment_delay(branch_id=BRANCH, as_of=AS_OF, active_children=500, overdue=many)
        assert draft is not None
        assert draft.evidence["children_count"] == 60
        assert len(draft.evidence["children"]) == 50
        # Eng eskisi birinchi.
        assert draft.evidence["children"][0]["days_overdue"] == 79

    def test_thresholds_are_parameters_not_constants(self):
        loose = PaymentDelayThresholds(overdue_days=30)
        assert (
            payment_delay(
                branch_id=BRANCH,
                as_of=AS_OF,
                active_children=100,
                overdue=[_overdue(20)],
                thresholds=loose,
            )
            is None
        )


def _group(**overrides) -> GroupAttendance:
    base = {
        "group_id": uuid4(),
        "active_children": 18,
        "recent_days": 7,
        "recent_present": 88,
        "recent_absent": 10,
        "recent_excused": 2,  # 88 %
        "baseline_days": 30,
        "baseline_present": 460,
        "baseline_absent": 30,
        "baseline_excused": 10,  # 92 %
    }
    base.update(overrides)
    return GroupAttendance(**base)


class TestAttendanceDrop:
    @pytest.mark.parametrize(
        ("recent_present", "fires"),
        # baza 92.0; recent 100 ta yozuvdan: 83 → drop 9.0 (yo'q); 82 → 10.0 (ha); 81 → 11.0 (ha)
        [(83, False), (82, True), (81, True)],
    )
    def test_attendance_drop_boundary_9_9_10_0_10_1_points(self, recent_present, fires):
        group = _group(
            recent_present=recent_present, recent_absent=100 - recent_present, recent_excused=0
        )
        assert (attendance_drop(as_of=AS_OF, group=group) is not None) is fires

    def test_attendance_drop_severity(self):
        warning = _group(recent_present=80, recent_absent=20, recent_excused=0)  # 80 → drop 12
        critical = _group(recent_present=70, recent_absent=30, recent_excused=0)  # 70 → drop 22
        assert attendance_drop(as_of=AS_OF, group=warning).severity == "warning"  # type: ignore[union-attr]
        assert attendance_drop(as_of=AS_OF, group=critical).severity == "critical"  # type: ignore[union-attr]

    def test_attendance_drop_skips_group_below_min_baseline_days(self):
        assert (
            attendance_drop(
                as_of=AS_OF, group=_group(baseline_days=14, recent_present=60, recent_absent=40)
            )
            is None
        )

    def test_attendance_drop_skips_group_below_min_group_size(self):
        assert (
            attendance_drop(
                as_of=AS_OF, group=_group(active_children=4, recent_present=60, recent_absent=40)
            )
            is None
        )

    def test_attendance_days_without_records_are_not_absent(self):
        # Yozuvsiz oyna: hech narsa bo'linmaydi, insight yo'q — "yo'q" deb hisoblanmaydi.
        assert (
            attendance_drop(
                as_of=AS_OF, group=_group(recent_present=0, recent_absent=0, recent_excused=0)
            )
            is None
        )

    def test_thresholds_are_parameters(self):
        strict = AttendanceDropThresholds(drop_warning=3.0)
        assert attendance_drop(as_of=AS_OF, group=_group(), thresholds=strict) is not None  # drop 4
