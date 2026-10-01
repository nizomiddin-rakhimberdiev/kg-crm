"""
Telefon normalizatsiyasi — Q7, PLAN 2.4.

Auditda vasiy telefoni "12345", tizim hisobiniki "45" bo'lib qabul
qilingan. Bu chiroyli bo'lmagan ma'lumot emas, **jimgina yo'qoladigan
SMS**: bildirishnoma "yuborildi" bo'lib turadi, ota-ona esa hech narsa
olmaydi va buni hech kim sezmaydi.
"""

from __future__ import annotations

import pytest

from apps.core.phone import PhoneFormatError, is_valid_phone, normalise_phone


class TestNormalisation:
    @pytest.mark.parametrize(
        "typed",
        [
            "+998 90 123 45 67",
            "998901234567",
            "90 123 45 67",
            "(90) 123-45-67",
            "901234567",
            "+998-90-123-45-67",
            "  90 123 45 67  ",
            # Eski odat: shaharlararo 8 bilan.
            "8 90 123 45 67",
        ],
    )
    def test_every_spelling_lands_on_one_form(self, typed):
        """Bazada bitta ko'rinish bo'lishi SHART — aks holda dublikat topilmaydi."""
        assert normalise_phone(typed) == "+998901234567"

    def test_an_empty_value_stays_empty(self):
        """Telefon hamma joyda majburiy emas: import qilingan bola vasiysiz bo'lishi mumkin."""
        assert normalise_phone("") == ""
        assert normalise_phone("   ") == ""


class TestRejection:
    @pytest.mark.parametrize(
        "bad",
        [
            "12345",  # auditdagi vasiy
            "45",  # auditdagi tizim hisobi
            "+1 555 0100",  # boshqa mamlakat
            "998901234567890",  # juda uzun
            "9012345",  # juda qisqa
            "abc",
            "+998",
        ],
    )
    def test_a_wrong_number_is_refused(self, bad):
        with pytest.raises(PhoneFormatError):
            normalise_phone(bad)
        assert not is_valid_phone(bad)

    def test_the_message_shows_the_expected_shape(self):
        """Xato "noto'g'ri" demaydi — qanday yozish kerakligini aytadi."""
        with pytest.raises(PhoneFormatError, match=r"\+998"):
            normalise_phone("12345")


@pytest.mark.django_db
class TestReportCommand:
    """
    `report_bad_phones` — mavjud ma'lumot uchun (PLAN 2.4).

    Nega tuzatmaydi: "12345" ning o'rniga nima yozish kerakligini tizim
    bilmaydi, taxmin qilib yozish esa ota-onaning SMS'ini butunlay
    boshqa odamga yuborardi.
    """

    def test_it_lists_bad_numbers_without_changing_them(self, tenant_a):
        from io import StringIO

        from django.core.management import call_command

        from apps.children.models import Guardian
        from apps.core.tenancy import organization_context

        with organization_context(tenant_a.organization.id):
            # Serializerni chetlab o'tamiz — bu aynan ESKI, allaqachon
            # bazada yotgan ma'lumotni taqlid qiladi.
            bad = Guardian.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Eski",
                last_name="Yozuv",
                phone="12345",
            )
            Guardian.objects.create(
                organization=tenant_a.organization,
                branch=tenant_a.branch,
                first_name="Yaxshi",
                last_name="Yozuv",
                phone="+998901234567",
            )

        out = StringIO()
        call_command("report_bad_phones", "--tenant", tenant_a.organization.slug, stdout=out)
        report = out.getvalue()

        assert "12345" in report
        assert "Yozuv Eski" in report
        assert "+998901234567" not in report, "to'g'ri raqam ro'yxatga tushmasligi kerak"

        with organization_context(tenant_a.organization.id):
            bad.refresh_from_db()
            assert bad.phone == "12345", "buyruq hech narsani o'zgartirmasligi kerak"

    def test_a_clean_tenant_reports_nothing(self, tenant_a):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("report_bad_phones", "--tenant", tenant_a.organization.slug, stdout=out)
        assert "formatga mos" in out.getvalue()
