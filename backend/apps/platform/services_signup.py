"""
Self-signup with a 14-day trial (PLAN 6.7, ADR-28).

The open `/auth/signup` was removed on purpose (docs/04 §5): a random visit
created a tenant that stayed in the database forever. This brings signup
back with that reason closed:

1. The form creates only a `SignupRequest` (platform plane) and sends a
   24-hour link. No tenant yet; unconfirmed rows go after 7 days.
2. Opening the link with a chosen password runs the SAME
   `register_organization()` the vendor console uses — one way to create a
   tenant — with a 14-day trial.
3. One self-signup trial per e-mail: the free trial is not a renewable
   resource. A second kindergarten for the same owner goes through sales.

Every request is also a `Lead` (source `self_signup`), so sales sees it.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.platform.models import SignupRequest

logger = logging.getLogger(__name__)

__all__ = ["LINK_TTL", "PENDING_TTL", "request_signup", "confirm_signup"]

LINK_TTL = timedelta(hours=24)
#: Unconfirmed requests are removed after this (purge_unconverted_trials).
PENDING_TTL = timedelta(days=7)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _link(token: str) -> str:
    base = str(getattr(settings, "FRONTEND_URL", "")).rstrip("/")
    return f"{base}/signup/confirm?token={token}"


def _send(request: SignupRequest, token: str) -> None:
    subject = gettext("Radix CRM — bogʻchangizni ochish")
    body = gettext(
        "Assalomu alaykum, {name}!\n\n"
        "«{kindergarten}» uchun Radix CRM sinovini ochish uchun havolani bosing "
        "va parolingizni oʻrnating:\n\n"
        "{link}\n\n"
        "Havola 24 soat ishlaydi. Agar siz soʻramagan boʻlsangiz, bu xatni "
        "eʼtiborsiz qoldiring — hech narsa yaratilmaydi."
    ).format(name=request.full_name, kindergarten=request.kindergarten_name, link=_link(token))
    try:
        send_mail(subject=subject, message=body, from_email=None, recipient_list=[request.email])
    except Exception:  # noqa: BLE001 — the request stays; the visitor can ask again
        logger.exception("Signup e-mail not sent: %s", request.pk)


@transaction.atomic
def request_signup(*, data: dict[str, Any]) -> SignupRequest:
    """
    Records the request and mails the link. The caller answers the same
    thing whatever happens here — the response never says whether an
    e-mail is known.
    """
    from apps.platform.services_leads import create_lead

    email = data["email"].strip().lower()
    # One open request per e-mail: asking again replaces the link.
    SignupRequest.objects.filter(email=email, confirmed_at__isnull=True).delete()

    token = secrets.token_urlsafe(32)
    request = SignupRequest.objects.create(
        email=email,
        full_name=data["name"],
        kindergarten_name=data["kindergarten_name"],
        phone=data["phone"],
        language=data.get("language", "uz"),
        token_hash=_hash(token),
        expires_at=timezone.now() + LINK_TTL,
    )
    create_lead(
        data={
            **{key: data[key] for key in ("name", "phone", "kindergarten_name", "city")},
            "children_count": data["children_count"],
            "language": data.get("language", "uz"),
            "message": f"Self-signup: {email}",
            "privacy_policy_version": data["privacy_policy_version"],
            "submission_id": data.get("submission_id") or uuid.uuid4(),
            "source": "self_signup",
        }
    )
    transaction.on_commit(lambda: _send(request, token))
    return request


@transaction.atomic
def confirm_signup(*, token: str, password: str) -> Any:
    """Creates the tenant. Returns the organization."""
    from apps.accounts.services import register_organization
    from apps.subscriptions.models import SELF_SIGNUP_TRIAL_DAYS

    request = (
        SignupRequest.objects.select_for_update()
        .filter(token_hash=_hash(token or ""), confirmed_at__isnull=True)
        .first()
    )
    if request is None or request.expires_at < timezone.now():
        raise BusinessRuleViolation(
            gettext("Havola eskirgan yoki ishlatilgan. Roʻyxatdan oʻtishni qaytadan boshlang.")
        )
    if SignupRequest.objects.filter(email=request.email, confirmed_at__isnull=False).exists():
        raise BusinessRuleViolation(
            gettext(
                "Bu email bilan sinov allaqachon ochilgan. Kirish sahifasidan kiring "
                "yoki ikkinchi bogʻcha uchun biz bilan bogʻlaning."
            )
        )
    validate_password(password)

    result = register_organization(
        organization_name=request.kindergarten_name,
        contact_email=request.email,
        full_name=request.full_name,
        password=password,
        contact_phone=request.phone,
        trial_days=SELF_SIGNUP_TRIAL_DAYS,
    )
    request.confirmed_at = timezone.now()
    request.organization = result.organization
    request.save(update_fields=["confirmed_at", "organization", "updated_at"])
    return result.organization
