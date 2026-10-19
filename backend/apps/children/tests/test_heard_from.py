"""
"Bizni qayerdan eshitdingiz?" (Bosqich 14).

Bola qo'shilayotganda admin oilaning bog'cha haqida qayerdan eshitganini
belgilaydi; ega davr va filial bo'yicha statistikani ko'radi. Ro'yxat
qat'iy — oylar va filiallar solishtirilsin. Javobsizlar "Ko'rsatilmagan"
bo'lib sanaladi, taxmin qilinmaydi.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.children.models import Child
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

TODAY = date.today()


def _child(tenant: Any, name: str, source: str = "", enrolled: date = TODAY, **extra: Any) -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name=name,
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
            enrolled_on=enrolled,
            heard_from=source,
            **extra,
        )


def _payload(**extra: Any) -> dict[str, Any]:
    return {
        "first_name": "Ali",
        "last_name": "Valiyev",
        "date_of_birth": "2021-03-14",
        "gender": "male",
        **extra,
    }


# --- Maydon ---


def test_a_new_child_keeps_where_the_family_heard_about_us(tenant_a: Any):
    response = tenant_a.client().post(
        reverse("v1:child-list"),
        _payload(heard_from="instagram", heard_from_note="@bogcha sahifasi"),
        format="json",
    )
    assert response.status_code == 201, response.content
    data = response.json()["data"]
    assert data["heard_from"] == "instagram"
    assert data["heard_from_note"] == "@bogcha sahifasi"


def test_the_answer_is_optional_in_the_api(tenant_a: Any):
    response = tenant_a.client().post(reverse("v1:child-list"), _payload(), format="json")
    assert response.status_code == 201, response.content
    assert response.json()["data"]["heard_from"] == ""


def test_an_unknown_source_is_refused(tenant_a: Any):
    response = tenant_a.client().post(
        reverse("v1:child-list"), _payload(heard_from="tiktok-ads"), format="json"
    )
    assert response.status_code == 400


def test_the_database_refuses_an_unknown_source(tenant_a: Any):
    child = _child(tenant_a, "Ali", "telegram")
    with (
        organization_context(tenant_a.organization.id),
        pytest.raises(IntegrityError),
        transaction.atomic(),
    ):
        Child.objects.filter(pk=child.pk).update(heard_from="radio")


def test_the_answer_can_be_corrected_later(tenant_a: Any):
    child = _child(tenant_a, "Ali")
    response = tenant_a.client().patch(
        reverse("v1:child-detail", args=[child.id]), {"heard_from": "referral"}, format="json"
    )
    assert response.status_code == 200, response.content
    assert response.json()["data"]["heard_from"] == "referral"


def test_the_children_list_filters_by_source(tenant_a: Any):
    _child(tenant_a, "Ali", "instagram")
    _child(tenant_a, "Vali", "telegram")
    response = tenant_a.client().get(reverse("v1:child-list"), {"heard_from": "instagram"})
    names = {row["first_name"] for row in response.json()["data"]}
    assert names == {"Ali"}


# --- Statistika ---


def test_the_report_counts_each_source_and_adds_up(tenant_a: Any):
    for name in ("A", "B", "C"):
        _child(tenant_a, name, "instagram")
    _child(tenant_a, "D", "referral")
    _child(tenant_a, "E")  # javob yo'q
    _child(tenant_a, "F", "referral", is_active=False)  # ketgan
    _child(tenant_a, "Old", "instagram", enrolled=TODAY - timedelta(days=400))  # davrdan tashqari

    data = (
        tenant_a.client()
        .get(
            "/api/v1/reports/sources",
            {"from": (TODAY - timedelta(days=30)).isoformat(), "to": TODAY.isoformat()},
        )
        .json()["data"]
    )
    rows = {row["source"]: row for row in data["rows"]}
    assert data["total"] == 6
    assert data["unanswered"] == 1
    assert rows["instagram"]["count"] == 3
    assert rows["instagram"]["share"] == "50.0"
    assert rows["referral"]["count"] == 2
    assert rows["referral"]["active"] == 1
    assert rows["instagram"]["label"]
    assert sum(row["count"] for row in data["rows"]) + data["unanswered"] == data["total"]


def test_a_child_without_an_enrolment_date_counts_by_when_it_was_added(tenant_a: Any):
    with organization_context(tenant_a.organization.id):
        Child.objects.create(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            first_name="Yangi",
            last_name="Bola",
            date_of_birth=date(2021, 3, 14),
            gender="female",
            heard_from="website",
        )
    data = tenant_a.client().get("/api/v1/reports/sources").json()["data"]
    assert {row["source"]: row["count"] for row in data["rows"]}.get("website") == 1


def test_a_cashier_does_not_see_the_sources_report(tenant_a: Any):
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with organization_context(tenant_a.organization.id):
        user = User.objects.create_user(
            email="kassir@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name="Kassir",
            organization=tenant_a.organization,
            role=tenant_a.role("cashier"),
            branch=tenant_a.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert client.get("/api/v1/reports/sources").status_code == 403


@pytest.mark.tenancy
def test_another_tenants_children_never_count(tenant_a: Any, tenant_b: Any):
    _child(tenant_a, "Ali", "instagram")
    data = tenant_b.client().get("/api/v1/reports/sources").json()["data"]
    assert data["total"] == 0


# --- Excel import ---


def test_the_import_reads_the_source_column(tenant_a: Any):
    from apps.children.importer import import_children

    csv_text = (
        "Familiya;Ism;Tugʻilgan sana;Qayerdan eshitgan\n"
        "Valiyev;Ali;2021-03-14;Instagram\n"
        "Karimova;Malika;2021-05-02;tanish-bilish\n"
        "Sodiqov;Bek;2021-06-01;\n"
    )
    with organization_context(tenant_a.organization.id):
        report = import_children(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            file_bytes=csv_text.encode("utf-8"),
            dry_run=False,
        )
        assert not report.errors, report.errors
        sources = dict(Child.objects.values_list("first_name", "heard_from"))
    assert sources == {"Ali": "instagram", "Malika": "referral", "Bek": ""}


def test_the_import_reports_an_unknown_source(tenant_a: Any):
    from apps.children.importer import import_children

    csv_text = "Familiya;Ism;Tugʻilgan sana;Qayerdan eshitgan\nValiyev;Ali;2021-03-14;Radio\n"
    with organization_context(tenant_a.organization.id):
        report = import_children(
            organization=tenant_a.organization,
            branch=tenant_a.branch,
            file_bytes=csv_text.encode("utf-8"),
            dry_run=True,
        )
    assert report.errors
