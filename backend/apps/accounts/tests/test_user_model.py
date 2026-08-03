"""
`User` modeli va tenant qo'riqchilarining testlari.

Bu yerdagi testlar ilova qatlamini emas, **bazadagi** kafolatlarni sinaydi
(D1): ular service qatlami chetlab o'tilganda ham amal qilishi kerak.
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


class TestEmailUniqueness:
    def test_same_email_allowed_in_different_organizations(self, organization, other_organization):
        """
        Bir odam ikki bog'chada ishlashi mumkin — bu haqiqiy stsenariy.

        Global unikallik buni jimgina bloklardi va ro'yxatdan o'tishda
        "bu email boshqa tenant'da bor" faktini oshkor qilardi (docs/03 §10.6).
        """
        User.objects.create_user(
            email="ustoz@example.uz", password="x", full_name="A", organization=organization
        )
        User.objects.create_user(
            email="ustoz@example.uz",
            password="x",
            full_name="A",
            organization=other_organization,
        )
        assert User.objects.filter(email="ustoz@example.uz").count() == 2

    def test_same_email_rejected_within_one_organization(self, organization):
        User.objects.create_user(
            email="kassir@example.uz", password="x", full_name="B", organization=organization
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create_user(
                email="kassir@example.uz",
                password="x",
                full_name="C",
                organization=organization,
            )

    def test_platform_email_is_globally_unique(self):
        """Tashkilotsiz (platforma) foydalanuvchilarda email global unikal."""
        User.objects.create_user(email="admin@kg.uz", password="x", full_name="Platform")
        with pytest.raises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="admin@kg.uz", password="x", full_name="Platform 2")


class TestOrganizationImmutabilityTrigger:
    @pytest.mark.tenancy
    def test_database_rejects_moving_a_row_between_tenants(self, organization, other_organization):
        """
        `organization_id` ni UPDATE qilish bazada bloklanadi.

        Bu ilova qatlamidagi `editable=False` ning takrori emas: trigger shell
        sessiyasi, ma'lumot tuzatuvchi skript va service qatlamini chetlab
        o'tgan har qanday kod uchun ham ishlaydi — aynan o'sha holatlar xavfli.
        """
        user = User.objects.create_user(
            email="a@example.uz", password="x", full_name="A", organization=organization
        )
        # Trigger `check_violation` ERRCODE bilan ko'tariladi → psycopg uni
        # IntegrityError ga o'giradi, ya'ni exception handler'da 409 CONFLICT.
        with pytest.raises(IntegrityError, match="organization_id"), transaction.atomic():
            User.objects.filter(pk=user.pk).update(organization=other_organization)

    def test_other_field_updates_still_work(self, organization):
        """Trigger faqat organization_id ni qo'riqlaydi, qolganini to'smaydi."""
        user = User.objects.create_user(
            email="b@example.uz", password="x", full_name="B", organization=organization
        )
        User.objects.filter(pk=user.pk).update(full_name="B yangilangan")
        user.refresh_from_db()
        assert user.full_name == "B yangilangan"
