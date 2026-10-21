"""
Bolaga biriktirilgan hujjat — imzolangan shartnomaning elektron nusxasi
(mijoz so'rovi, 2026-10-21).

Bola qo'shilayotganda yoki keyin PDF, DOC yoki DOCX fayl biriktiriladi;
majburiy emas. Fayl turi kengaytma bilan birga ICHIDAGI imzo bo'yicha ham
tekshiriladi — ".pdf" deb nomlangan boshqa narsa qabul qilinmaydi. Fayl
`/media/` havolasi bilan emas, tenantni biladigan endpoint orqali beriladi.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.children import services
from apps.children.models import Child, ChildDocument
from apps.core.tenancy import organization_context

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.7\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n"
DOCX = b"PK\x03\x04" + b"\x00" * 64
DOC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 64


def _child(tenant: Any) -> Child:
    with organization_context(tenant.organization.id):
        return Child.objects.create(
            organization=tenant.organization,
            branch=tenant.branch,
            first_name="Ali",
            last_name="Valiyev",
            date_of_birth=date(2021, 3, 14),
            gender="male",
        )


def _upload(client: Any, child: Child, name: str, content: bytes) -> Any:
    return client.post(
        f"/api/v1/children/{child.id}/documents",
        {"file": SimpleUploadedFile(name, content)},
        format="multipart",
    )


def _user(tenant: Any, role: str) -> Any:
    from rest_framework.test import APIClient

    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.models import User

    with organization_context(tenant.organization.id):
        user = User.objects.create_user(
            email=f"{role}@alfa.uz",
            password="Juda-Kuchli-Parol-2026",  # noqa: S106
            full_name=role,
            organization=tenant.organization,
            role=tenant.role(role),
            branch=tenant.branch,
        )
        tokens = issue_token_pair(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


@pytest.mark.parametrize(
    ("name", "content"),
    [("shartnoma.pdf", PDF), ("shartnoma.docx", DOCX), ("Shartnoma.DOC", DOC)],
)
def test_a_signed_contract_can_be_attached(tenant_a: Any, name: str, content: bytes):
    child = _child(tenant_a)
    client = tenant_a.client()

    response = _upload(client, child, name, content)

    assert response.status_code == 201, response.content
    data = response.json()["data"]
    assert data["name"] == name
    assert data["size"] == len(content)
    listed = client.get(f"/api/v1/children/{child.id}/documents").json()["data"]
    assert [row["id"] for row in listed] == [data["id"]]

    download = client.get(f"/api/v1/children/{child.id}/documents/{data['id']}/download")
    assert download.status_code == 200
    assert b"".join(download.streaming_content) == content
    assert name in download["Content-Disposition"]


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("rasm.jpg", b"\xff\xd8\xff\xe0" + b"\x00" * 32),
        ("dastur.exe", b"MZ" + b"\x00" * 32),
        ("soxta.pdf", b"MZ" + b"\x00" * 32),
        ("soxta.docx", PDF),
    ],
)
def test_other_files_are_refused(tenant_a: Any, name: str, content: bytes):
    response = _upload(tenant_a.client(), _child(tenant_a), name, content)
    assert response.status_code == 422


def test_a_file_over_ten_megabytes_is_refused(tenant_a: Any):
    big = PDF + b"0" * (10 * 1024 * 1024)
    response = _upload(tenant_a.client(), _child(tenant_a), "katta.pdf", big)
    assert response.status_code == 422


def test_a_document_can_be_removed(tenant_a: Any):
    child = _child(tenant_a)
    client = tenant_a.client()
    document = _upload(client, child, "shartnoma.pdf", PDF).json()["data"]

    response = client.delete(f"/api/v1/children/{child.id}/documents/{document['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/v1/children/{child.id}/documents").json()["data"] == []


def test_a_cashier_reads_but_cannot_attach(tenant_a: Any):
    child = _child(tenant_a)
    _upload(tenant_a.client(), child, "shartnoma.pdf", PDF)
    cashier = _user(tenant_a, "cashier")
    assert cashier.get(f"/api/v1/children/{child.id}/documents").status_code == 200
    assert _upload(cashier, child, "boshqa.pdf", PDF).status_code == 403


def test_deleting_a_mistaken_child_removes_its_documents(tenant_a: Any):
    child = _child(tenant_a)
    _upload(tenant_a.client(), child, "shartnoma.pdf", PDF)
    with organization_context(tenant_a.organization.id):
        stored = ChildDocument.objects.get(child=child)
        storage, path = stored.file.storage, stored.file.name
        services.delete_child(child=child)
        assert not ChildDocument.objects.filter(pk=stored.pk).exists()
    assert not storage.exists(path)


@pytest.mark.tenancy
def test_another_tenant_never_reaches_the_documents(tenant_a: Any, tenant_b: Any):
    child = _child(tenant_a)
    document = _upload(tenant_a.client(), child, "shartnoma.pdf", PDF).json()["data"]
    other = tenant_b.client()

    assert other.get(f"/api/v1/children/{child.id}/documents").status_code == 404
    assert _upload(other, child, "x.pdf", PDF).status_code == 404
    assert (
        other.get(f"/api/v1/children/{child.id}/documents/{document['id']}/download").status_code
        == 404
    )
    assert (
        other.delete(f"/api/v1/children/{child.id}/documents/{document['id']}").status_code == 404
    )


def test_purging_the_organization_removes_the_files_too(tenant_a: Any):
    """
    Tashkilot butunlay o'chirilganda shartnoma fayli diskda qolmasin —
    u oilaning shaxsiy hujjati. Django `queryset.delete()` faylni o'chirmaydi.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.core.tenancy import platform_context
    from apps.organizations.models import Organization
    from apps.platform.purge import purge_organization

    child = _child(tenant_a)
    _upload(tenant_a.client(), child, "shartnoma.pdf", PDF)
    with organization_context(tenant_a.organization.id):
        stored = ChildDocument.objects.get(child=child)
        storage, path = stored.file.storage, stored.file.name
    assert storage.exists(path)
    with platform_context():
        Organization.objects.filter(pk=tenant_a.organization.id).update(
            is_active=False, updated_at=timezone.now() - timedelta(days=45)
        )

    purge_organization(
        organization_id=tenant_a.organization.id, confirm_slug=tenant_a.organization.slug
    )

    assert not storage.exists(path)
