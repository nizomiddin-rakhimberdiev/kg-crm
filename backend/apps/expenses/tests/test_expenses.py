"""Chiqim tasdiqlash oqimi testlari (docs/03 §16.2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.expenses import services
from apps.expenses.models import Expense, ExpenseCategory, ExpenseStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def category(tenant_a) -> ExpenseCategory:
    # Bogʻchada pul avval tushadi, keyin chiqadi (ADR-29): boʻsh
    # kassadan chiqim ataylab toʻxtaydi, shuning uchun oqim testlari
    # avval qopni toʻldiradi. Qoʻriqchining oʻzi `apps/cash` da.
    tenant_a.fund()
    with organization_context(tenant_a.organization.id):
        return ExpenseCategory.objects.create(
            organization=tenant_a.organization, branch=tenant_a.branch, name="Kommunal"
        )


@pytest.fixture
def expense(tenant_a, category) -> Expense:
    with organization_context(tenant_a.organization.id):
        return Expense.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            category=category,
            amount=Decimal("500000"),
            expense_date=date(2026, 7, 15),
            description="Iyul oyi elektr",
        )


class TestApprovalWorkflow:
    def test_approve_records_who_and_when(self, tenant_a, expense):
        with organization_context(tenant_a.organization.id):
            services.approve_expense(expense=expense, approved_by=tenant_a.owner, note="OK")
            expense.refresh_from_db()
        assert expense.status == ExpenseStatus.APPROVED
        assert expense.approved_by_id == tenant_a.owner.id
        assert expense.decided_at is not None

    def test_reject_keeps_the_record(self, tenant_a, expense):
        """
        Rad etilgan chiqim O'CHIRILMAYDI.

        U nima so'ralgani va nega rad etilgani haqidagi yozuv bo'lib
        qoladi — aks holda "men buni soʻragan edim" bahsiga javob
        bo'lmasdi.
        """
        with organization_context(tenant_a.organization.id):
            services.reject_expense(
                expense=expense, approved_by=tenant_a.owner, note="Byudjetda yoʻq"
            )
            expense.refresh_from_db()
            assert Expense.objects.filter(pk=expense.pk).exists()
        assert expense.status == ExpenseStatus.REJECTED
        assert expense.decision_note == "Byudjetda yoʻq"

    def test_double_decision_is_rejected(self, tenant_a, expense):
        with organization_context(tenant_a.organization.id):
            services.approve_expense(expense=expense, approved_by=tenant_a.owner)
            with pytest.raises(BusinessRuleViolation, match="holatida"):
                services.approve_expense(expense=expense, approved_by=tenant_a.owner)

    def test_mark_paid_requires_approval(self, tenant_a, expense):
        with organization_context(tenant_a.organization.id):
            with pytest.raises(BusinessRuleViolation, match="tasdiqlangan"):
                services.mark_expense_paid(expense=expense)

            services.approve_expense(expense=expense, approved_by=tenant_a.owner)
            services.mark_expense_paid(expense=expense)
            expense.refresh_from_db()
        assert expense.status == ExpenseStatus.PAID


class TestSummary:
    def test_only_approved_and_paid_are_counted(self, tenant_a, category):
        """
        Kutilayotgan so'rov hali xarajat emas.

        Uni P&L ga qo'shish sarfni oshirib ko'rsatardi va byudjet
        qarorlarini buzardi.
        """
        with organization_context(tenant_a.organization.id):
            base = {
                "organization": tenant_a.organization,
                "branch": tenant_a.branch,
                "category": category,
                "expense_date": date(2026, 7, 10),
            }
            Expense.objects.create(**base, amount=Decimal("100000"), status="pending")
            Expense.objects.create(**base, amount=Decimal("200000"), status="approved")
            Expense.objects.create(**base, amount=Decimal("300000"), status="paid")
            Expense.objects.create(**base, amount=Decimal("900000"), status="rejected")

            summary = services.expense_summary(
                organization_id=tenant_a.organization.id,
                date_from=date(2026, 7, 1),
                date_to=date(2026, 7, 31),
            )
        assert summary["total"] == "500000.00"  # 200k + 300k


class TestEndpoints:
    def test_create_and_approve(self, tenant_a, category):
        client = tenant_a.client()
        created = client.post(
            reverse("v1:expense-list"),
            {
                "category_id": str(category.id),
                "amount": "750000",
                "expense_date": "2026-07-20",
                "description": "Taʼmirlash",
            },
            format="json",
        )
        assert created.status_code == 201
        # Chiqim yaratilgan zahoti tasdiqlangan (PLAN 7.2): alohida
        # "Tasdiqlash" qadami yo'q, shuning uchun uni qayta tasdiqlab
        # bo'lmaydi ham.
        assert created.json()["data"]["status"] == "approved"
        expense_id = created.json()["data"]["id"]

        again = client.post(reverse("v1:expense-approve", args=[expense_id]))
        assert again.status_code == 422

    def test_status_cannot_be_set_directly(self, tenant_a, category):
        """
        Mijoz `status` ni yozolmaydi — uni server qo'yadi.

        PLAN 7.2 dan keyin yangi chiqim baribir `approved` bo'ladi, lekin
        maydonning o'zi mijozdan OLINMAYDI: aks holda ertaga
        "rad etilgan" yoki "to'langan" deb kiritib yuborish mumkin bo'lardi.
        """
        response = tenant_a.client().post(
            reverse("v1:expense-list"),
            {
                "category_id": str(category.id),
                "amount": "100000",
                "expense_date": "2026-07-20",
                "status": "approved",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["data"]["status"] == "approved"

    def test_approved_expense_cannot_be_edited(self, tenant_a, expense):
        client = tenant_a.client()
        client.post(reverse("v1:expense-approve", args=[expense.id]))
        response = client.patch(
            reverse("v1:expense-detail", args=[expense.id]),
            {"amount": "1"},
            format="json",
        )
        assert response.status_code == 422

    def test_summary_endpoint(self, tenant_a, expense):
        client = tenant_a.client()
        client.post(reverse("v1:expense-approve", args=[expense.id]))
        response = client.get(
            reverse("v1:expense-summary"), {"from": "2026-07-01", "to": "2026-07-31"}
        )
        assert response.status_code == 200
        assert response.json()["data"]["total"] == "500000.00"

    def test_manager_can_read_but_not_approve(self, tenant_a, expense):
        """Menejer chiqimni yoza oladi, lekin tasdiqlay olmaydi (docs/02 §11.2)."""
        from rest_framework.test import APIClient

        from apps.accounts.authentication import issue_token_pair
        from apps.accounts.models import User

        with organization_context(tenant_a.organization.id):
            cashier = User.objects.create_user(
                email="kassir@alfa.uz",
                password="Juda-Kuchli-Parol-2026",  # noqa: S106
                full_name="Menejer",
                organization=tenant_a.organization,
                role=tenant_a.role("manager"),
                branch=tenant_a.branch,
            )
            tokens = issue_token_pair(cashier)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert client.get(reverse("v1:expense-list")).status_code == 200
        assert client.post(reverse("v1:expense-approve", args=[expense.id])).status_code == 403
