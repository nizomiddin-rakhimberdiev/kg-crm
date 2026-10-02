"""
`create_platform_user` — vendor hisobi va uning 2FA'si (ADR-10, ADR-24).

Bu buyruq vendor konsoliga kirishning YAGONA tiklash yo'li: telefon
ham, zaxira kodlari ham yo'qolsa, qaytish faqat serverdan. Shuning
uchun u ishonchli bo'lishi kerak — chop etilgan kodlar haqiqatan
ishlashi va eskilari haqiqatan o'lishi.
"""

from __future__ import annotations

import re
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.core import backup_codes
from apps.core.tenancy import platform_context
from apps.platform.models import PlatformUser

pytestmark = [pytest.mark.django_db, pytest.mark.big_update]

PASSWORD = "Platforma-Juda-Kuchli-2026"  # noqa: S105 — test ma'lumoti
CODE = re.compile(r"^\s+([a-z0-9]{4}-[a-z0-9]{4})$", re.M)


def _run(*args: str) -> str:
    out = StringIO()
    call_command("create_platform_user", *args, stdout=out)
    return out.getvalue()


def _user(email: str) -> PlatformUser:
    with platform_context():
        return PlatformUser.objects.get(email=email)


def test_a_new_account_gets_a_secret_and_ten_working_backup_codes():
    output = _run("--email", "v@radix.uz", "--name", "Vendor", "--password", PASSWORD)
    printed = CODE.findall(output)
    assert len(printed) == backup_codes.CODE_COUNT

    user = _user("v@radix.uz")
    assert user.has_2fa is True
    # Chop etilgan har bir kod saqlangan xeshga mos keladi — ya'ni
    # odam qog'ozga yozgani haqiqatan ishlaydi.
    assert all(backup_codes.consume(user.totp_backup_codes, code) is not None for code in printed)
    # Kodning o'zi bazada YO'Q.
    assert not set(printed) & set(user.totp_backup_codes)


def test_new_2fa_replaces_the_secret_and_kills_the_old_codes():
    first = CODE.findall(_run("--email", "v@radix.uz", "--name", "V", "--password", PASSWORD))
    old_secret = _user("v@radix.uz").totp_secret

    # `--password` SIZ: 2FA ni tiklash parolni almashtirishga majburlamaydi.
    second = CODE.findall(_run("--email", "v@radix.uz", "--update", "--new-2fa"))

    user = _user("v@radix.uz")
    assert user.totp_secret != old_secret
    assert user.check_password(PASSWORD) is True
    # Telefon yo'qolgan bo'lsa u boshqa birovning qo'lida bo'lishi
    # mumkin — eski kodlar ENDI ishlamasligi shart.
    assert all(backup_codes.consume(user.totp_backup_codes, code) is None for code in first)
    assert all(backup_codes.consume(user.totp_backup_codes, code) is not None for code in second)


def test_a_plain_update_keeps_the_second_factor():
    _run("--email", "v@radix.uz", "--name", "V", "--password", PASSWORD)
    before = _user("v@radix.uz")

    _run("--email", "v@radix.uz", "--update", "--password", "Yangi-Juda-Kuchli-2026")

    after = _user("v@radix.uz")
    assert after.totp_secret == before.totp_secret
    assert after.totp_backup_codes == before.totp_backup_codes


def test_a_new_account_needs_a_password():
    with pytest.raises(CommandError, match="--password"):
        _run("--email", "v@radix.uz", "--name", "V")
