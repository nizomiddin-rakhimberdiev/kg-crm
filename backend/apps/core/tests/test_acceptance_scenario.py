"""
Yakuniy qabul ssenariysi — brief §6, to'qqiz qadam, API orqali.

Har bir qadam alohida modul testlarida ham bor; bu fayl ularni BITTA
hikoyada, haqiqiy endpointlar orqali o'tkazadi — modullar orasidagi
tikuvlarni (taqsimot ↔ qarzdorlar ↔ dashboard ↔ bola kartasi) faqat
shunday tekshirish mumkin. Oy va bayramlar test ichida qotirilgan:
2026-yil sentabr — 22 ish kuni, bayramsiz; qabul — chorshanba, 30.09,
oyning oxirgi ish kuni.

Bu ssenariy bitta haqiqiy xatoni topdi: bola kartasidan qo'shilgan
vasiy telefoni tekshirilmasdi (1-qadam, `test_add_guardian_phone.py`).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.core.tenancy import organization_context

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]


@pytest.fixture(autouse=True)
def _commit_per_request(monkeypatch):
    """
    Har bir API so'rovi production'da o'z tranzaksiyasini COMMIT qiladi va
    `on_commit` (dashboard keshini bekor qilish) shunda ishlaydi. Test esa
    bitta tranzaksiya ichida — u yerda callback'lar hech qachon
    chaqirilmasdi. Shu sababli ular darhol bajariladi.
    """
    monkeypatch.setattr(
        "django.db.transaction.on_commit", lambda func, using=None, robust=False: func()
    )


TARIFF = Decimal("1500000")
ADMITTED = date(2026, 9, 30)  # oyning oxirgi ish kuni
PRORATED = Decimal("68182.00")  # 1 500 000 × 1/22, butun so'mgacha
ADVANCE_LEFT = Decimal("131818.00")  # 200 000 − 68 182


def _data(response):
    assert response.status_code < 300, (response.status_code, response.content[:400])
    return response.json()["data"]


@pytest.fixture
def story(tenant_a):
    """1-qadam: tarifi 1 500 000 bo'lgan bola oyning oxirgi ish kunida qabul qilinadi."""
    from apps.children.models import Group
    from apps.finance.models import TariffPlan

    with organization_context(tenant_a.organization.id):
        tariff = TariffPlan.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="T", amount=TARIFF
        )
        group = Group.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Quyosh", capacity=20
        )
    client = tenant_a.client()
    child = _data(
        client.post(
            "/api/v1/children",
            {
                "first_name": "Ali",
                "last_name": "Valiyev",
                "date_of_birth": "2022-01-01",
                "gender": "male",
                "tariff_id": str(tariff.id),
                "enrolled_on": ADMITTED.isoformat(),
            },
            format="json",
        )
    )
    _data(
        client.post(
            f"/api/v1/children/{child['id']}/enroll", {"group_id": str(group.id)}, format="json"
        )
    )
    return {"client": client, "child_id": child["id"], "group": group}


class TestAcceptance:
    def test_the_whole_story(self, tenant_a, tenant_b, story):
        client, child_id = story["client"], story["child_id"]

        # --- 1. Vasiy telefoni: "12345" rad etiladi, "+998 90 123 45 67" qabul qilinadi.
        bad = client.post(
            f"/api/v1/children/{child_id}/guardians",
            {
                "first_name": "Nodira",
                "last_name": "Valiyeva",
                "phone": "12345",
                "relation": "mother",
            },
            format="json",
        )
        assert bad.status_code == 400
        guardian = _data(
            client.post(
                f"/api/v1/children/{child_id}/guardians",
                {
                    "first_name": "Nodira",
                    "last_name": "Valiyeva",
                    "phone": "+998 90 123 45 67",
                    "relation": "mother",
                },
                format="json",
            )
        )["guardian"]
        assert guardian["phone"] == "+998901234567"

        # --- 2. 200 000 naqd to'lov → avans 200 000.
        payment = _data(
            client.post(
                "/api/v1/payments",
                {"child_id": child_id, "amount": "200000", "method": "cash"},
                format="json",
            )
        )
        balance = _data(client.get(f"/api/v1/ledger/balance?child={child_id}"))
        assert Decimal(balance["advance"]) == Decimal("200000")
        assert Decimal(balance["balance"]) == Decimal("-200000")

        # --- 3. Generatsiya: preview 1 bola va proporsional summa; tasdiq.
        preview = _data(
            client.post(
                "/api/v1/invoices/preview-run",
                {"period_year": 2026, "period_month": 9},
                format="json",
            )
        )
        assert preview["will_create"] == 1
        assert Decimal(preview["total_amount"]) == PRORATED
        run = _data(
            client.post(
                "/api/v1/invoices/generate", {"period_year": 2026, "period_month": 9}, format="json"
            )
        )
        assert run["created"] == 1
        invoice = _data(client.get(f"/api/v1/invoices?child={child_id}"))[0]
        assert Decimal(invoice["amount_due"]) == PRORATED
        # Muddat = qabul + 5 kun (Q3).
        assert invoice["due_date"] == (ADMITTED + timedelta(days=5)).isoformat()

        # Avans avtomatik qo'llanadi → qarz 0, avans 131 818.
        balance = _data(client.get(f"/api/v1/ledger/balance?child={child_id}"))
        assert Decimal(balance["outstanding"]) == 0
        assert Decimal(balance["advance"]) == ADVANCE_LEFT

        # --- 4. Har bir ekranda bir xil raqam.
        self._same_everywhere(client, child_id, debt=Decimal("0"), advance=ADVANCE_LEFT)

        # --- 5. Keyingi oyning 1-kunidan "Chiqib ketgan" → o'sha oyga faktura yo'q.
        _data(
            client.post(
                f"/api/v1/children/{child_id}/change-status",
                {
                    "enrollment_status": "withdrawn",
                    "status_changed_on": "2026-10-01",
                    "status_reason": "Oila koʻchib ketdi",
                },
                format="json",
            )
        )
        october = _data(
            client.post(
                "/api/v1/invoices/generate",
                {"period_year": 2026, "period_month": 10},
                format="json",
            )
        )
        assert october["created"] == 0
        assert len(_data(client.get(f"/api/v1/invoices?child={child_id}"))) == 1

        # --- 6. To'lov "Qaytarish" bilan bekor qilinadi → taqsimot bekor,
        # balans hamma joyda qayta hisoblanadi.
        reversed_payment = _data(
            client.post(
                f"/api/v1/payments/{payment['id']}/reverse",
                {"reason": "Xato kiritildi"},
                format="json",
            )
        )
        assert reversed_payment["is_reversed"] is True
        balance = _data(client.get(f"/api/v1/ledger/balance?child={child_id}"))
        assert Decimal(balance["outstanding"]) == PRORATED
        assert Decimal(balance["advance"]) == 0
        self._same_everywhere(client, child_id, debt=PRORATED, advance=Decimal("0"))

        # --- 9. Boshqa tenant foydalanuvchisi shu bola API'siga → 404.
        other = tenant_b.client()
        assert other.get(f"/api/v1/children/{child_id}").status_code == 404
        assert other.get(f"/api/v1/ledger/balance?child={child_id}").status_code == 404
        assert (
            other.post(
                f"/api/v1/children/{child_id}/guardians",
                {"phone": "+998901234567", "relation": "mother"},
                format="json",
            ).status_code
            == 404
        )

    def _same_everywhere(self, client, child_id: str, *, debt: Decimal, advance: Decimal) -> None:
        """To'lovlar doskasi, to'lov oynasi, qarzdorlar, dashboard, brifing, bola kartasi."""
        card = _data(client.get(f"/api/v1/children/{child_id}"))
        assert Decimal(card["balance"]) == debt - advance

        modal = _data(client.get(f"/api/v1/ledger/balance?child={child_id}"))
        assert Decimal(modal["outstanding"]) == debt
        assert Decimal(modal["advance"]) == advance

        # Doska — joriy bolalar ro'yxati: chiqib ketgan bola unda bo'lmasligi
        # mumkin. Bo'lsa — raqami boshqalar bilan BIR XIL bo'lishi shart.
        board = next(
            (
                row
                for row in _data(client.get("/api/v1/payments/board"))
                if row["child_id"] == child_id
            ),
            None,
        )
        if board is not None:
            assert Decimal(board["outstanding"]) == debt
            assert Decimal(board["advance"]) == advance

        # Qarzdorlar esa chiqib ketgan bolani ham ko'rsatadi: pul hamon qarz.
        debtors = _data(client.get("/api/v1/debtors"))["results"]
        listed = {row["child"]["id"]: Decimal(row["balance"]) for row in debtors}
        assert listed.get(child_id, Decimal("0")) == debt

        dashboard = _data(client.get("/api/v1/dashboard"))
        assert Decimal(dashboard["outstanding_debt"]) == debt
        assert dashboard["debtor_count"] == (1 if debt else 0)

        briefing = _data(client.get("/api/v1/insights/briefing"))
        assert Decimal(briefing["totals"]["total_debt"]) == debt

    # --- 7. Tarbiyachi faqat o'z guruhini ko'radi va eski kunni tahrirlay olmaydi.
    def test_teacher_sees_only_their_group(self, tenant_a, story):
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import Permission, Role, RolePermission, User
        from apps.children.models import Child, Group
        from apps.hr.models import Employee

        group = story["group"]
        org, branch = tenant_a.organization, tenant_a.branch
        with organization_context(org.id):
            other = Group.objects.create(
                organization=org, branch=branch, name="Begona", capacity=10
            )
            stranger = Child.objects.create(
                organization=org,
                branch=branch,
                first_name="Begona",
                last_name="Bola",
                date_of_birth=date(2022, 2, 2),
                gender="female",
            )
            from apps.children.services import enroll_child

            enroll_child(child=stranger, group=other)
            role = Role.objects.create(organization=org, name="Tarbiyachi", code="teacher_x")
            for code in (
                "children.read",
                "attendance.read",
                "attendance.create",
                "attendance.update",
            ):
                RolePermission.objects.create(
                    role=role, permission=Permission.objects.get(code=code)
                )
            user = User.objects.create_user(
                email="tarbiyachi@alfa.uz",
                password="Juda-Kuchli-Parol-2026",
                organization=org,
                branch=branch,
                full_name="Dilnoza Ergasheva",
                role=role,
            )
            group.teacher = Employee.objects.create(
                organization=org,
                branch=branch,
                first_name="Dilnoza",
                last_name="Ergasheva",
                hire_date=date(2024, 1, 1),
                base_salary=Decimal("5000000"),
                user=user,
            )
            group.save(update_fields=["teacher"])
            access = issue_token_pair(user)["access"]

        teacher = APIClient()
        teacher.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        names = {row["full_name"] for row in _data(teacher.get("/api/v1/children"))}
        assert names == {"Valiyev Ali"}

        def mark(day: date):
            return teacher.post(
                "/api/v1/attendance/bulk",
                {
                    "group_id": str(group.id),
                    "attendance_date": day.isoformat(),
                    "records": [{"child_id": story["child_id"], "status": "present"}],
                },
                format="json",
            )

        today = timezone.localdate()
        assert mark(today - timedelta(days=1)).status_code < 300
        assert mark(today - timedelta(days=2)).status_code == 422

    # --- 8. Console SMS provayderda holat "test rejimi" va banner.
    def test_console_sms_is_test_mode_with_a_banner(self, tenant_a, story):
        from apps.notifications.models import NotificationTemplate

        client = story["client"]
        guardian = _data(
            client.post(
                f"/api/v1/children/{story['child_id']}/guardians",
                {"first_name": "Nodira", "phone": "+998901234567", "relation": "mother"},
                format="json",
            )
        )["guardian"]
        from apps.settings_app.services import set_setting

        with organization_context(tenant_a.organization.id):
            template = NotificationTemplate.objects.filter(channel="sms").first()
            # Yuborish oynasi (Q9) testni soatga bog'lamasin: tunda ishga
            # tushganda xabar to'g'ri ravishda `queued` bo'lardi.
            set_setting(
                organization=tenant_a.organization, key="notifications.send_from_hour", value=0
            )
            set_setting(
                organization=tenant_a.organization, key="notifications.send_to_hour", value=24
            )
        sent = client.post(
            "/api/v1/notifications/send",
            {
                "template_code": template.code,
                "channel": "sms",
                "guardian_ids": [guardian["id"]],
                "body_override": "Sinov xabari",
            },
            format="json",
        )
        assert sent.status_code < 300, sent.content[:300]
        rows = _data(client.get("/api/v1/notifications"))
        assert rows[0]["status"] == "test_mode"
        banner = _data(client.get("/api/v1/notifications/status"))
        assert banner["test_mode"] is True
