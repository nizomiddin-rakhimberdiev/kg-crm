"""
Obuna hayotiy sikli testlari (docs/03 §20.6, docs/01 §4.4).

Asosiy savollar:
  1. Sinov to'g'ri konvertatsiya bo'ladimi va birinchi hisob SINOV
     boshlangan kundan hisoblanadimi?
  2. To'lamagan mijozning ma'lumoti saqlanib qoladimi?
  3. O'lchovni aldab bo'ladimi?
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.children.models import Child
from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context
from apps.subscriptions import services
from apps.subscriptions.models import (
    MeasurementMethod,
    PaymentTerm,
    Subscription,
    SubscriptionInvoice,
    SubscriptionInvoiceStatus,
    SubscriptionStatus,
    UsageSnapshot,
)

pytestmark = pytest.mark.django_db


def _subscription(tenant) -> Subscription:
    with organization_context(tenant.organization.id):
        return Subscription.objects.get(organization=tenant.organization)


def _backdate(invoice: SubscriptionInvoice, *, days: int) -> None:
    """Hisobni o'tmishga suradi — muddati o'tish stsenariylarini sinash uchun."""
    issued = timezone.localdate() - timedelta(days=days + 7)
    SubscriptionInvoice.objects.filter(pk=invoice.pk).update(
        issued_at=issued, due_at=timezone.localdate() - timedelta(days=days)
    )


def _add_children(tenant, count: int) -> None:
    with organization_context(tenant.organization.id):
        for index in range(count):
            Child.objects.create(
                organization=tenant.organization,
                branch=tenant.branch,
                first_name=f"Bola{index}",
                last_name="Testov",
                date_of_birth=date(2021, 3, 14),
                gender="male",
            )


class TestSignupCreatesTrial:
    def test_every_new_organization_starts_trialing(self, tenant_a):
        """
        Ro'yxatdan o'tish sinov obunasini ochadi.

        Obunasiz tashkilot — hisob-kitobi yo'q mijoz degani, va uni
        keyin qo'lda tuzatish kerak bo'lardi.
        """
        subscription = _subscription(tenant_a)
        assert subscription.status == SubscriptionStatus.TRIALING
        assert subscription.trial_ends_at is not None
        assert (subscription.trial_ends_at - subscription.trial_started_at).days == 15

    def test_no_card_and_no_upfront_invoice(self, tenant_a):
        """Sinov davrida hisob YOZILMAYDI (docs/01 §4.4)."""
        with organization_context(tenant_a.organization.id):
            assert SubscriptionInvoice.objects.count() == 0

    def test_one_live_subscription_per_organization(self, tenant_a):
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="allaqachon"),
        ):
            services.start_trial(organization=tenant_a.organization)


class TestConversion:
    def test_first_invoice_starts_from_the_trial_day(self, tenant_a):
        """
        Birinchi to'langan davr SINOV kunidan boshlanadi.

        Ya'ni to'langan oy sinov davrini o'z ichiga oladi (docs/01 §4.4).
        Bu ro'yxatdan o'tishdagi taklifda aytilishi SHART — sxema
        siyosatni qo'llab-quvvatlaydi, lekin uni halol qiladigan narsa
        faqat ochiq aytilgani.
        """
        subscription = _subscription(tenant_a)
        with organization_context(tenant_a.organization.id):
            invoice = services.accept_trial(subscription=subscription)

        trial_day = timezone.localtime(subscription.trial_started_at).date()
        assert invoice.period_start == trial_day

    def test_monthly_conversion_bills_the_base(self, tenant_a):
        _add_children(tenant_a, 3)
        with organization_context(tenant_a.organization.id):
            invoice = services.accept_trial(subscription=_subscription(tenant_a))

        assert invoice.billable_children == 50  # pol
        assert invoice.total_amount == Decimal("500000.00")
        assert invoice.discount_amount == Decimal("0.00")

    def test_annual_conversion_applies_25_percent(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            invoice = services.accept_trial(
                subscription=_subscription(tenant_a), payment_term=PaymentTerm.ANNUAL
            )
        assert invoice.base_amount == Decimal("6000000.00")
        assert invoice.discount_amount == Decimal("1500000.00")
        assert invoice.total_amount == Decimal("4500000.00")

    def test_discount_is_frozen_on_the_subscription(self, tenant_a):
        """
        Chegirma obunaga nusxa qilinadi.

        Vendor keyin "yillik" nimaga arziyotganini o'zgartirsa, mavjud
        shartnomalarga tegmasligi kerak (docs/03 §20.2).
        """
        with organization_context(tenant_a.organization.id):
            services.accept_trial(
                subscription=_subscription(tenant_a), payment_term=PaymentTerm.SEMIANNUAL
            )
            subscription = _subscription(tenant_a)
        assert subscription.discount_percent == Decimal("15.00")
        assert subscription.status == SubscriptionStatus.PENDING_PAYMENT

    def test_pending_payment_still_has_full_access(self, tenant_a):
        """
        `pending_payment` — TO'LIQ kirish.

        Mijozlar yuridik shaxs va bank o'tkazmasi kunlab ketadi. Kirishni
        o'rtada uzish — o'z pulini yuborayotgan mijozni ishdan
        to'xtatish degani (docs/01 §4.4).
        """
        with organization_context(tenant_a.organization.id):
            services.accept_trial(subscription=_subscription(tenant_a))
            assert _subscription(tenant_a).is_read_only is False

    def test_cannot_convert_twice(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            services.accept_trial(subscription=_subscription(tenant_a))
            with pytest.raises(BusinessRuleViolation, match="sinov davridagi"):
                services.accept_trial(subscription=_subscription(tenant_a))


class TestMetering:
    def test_peak_only_rises_within_an_open_period(self, tenant_a):
        """
        Eng yuqori nuqta faqat O'SADI.

        Oy oxiridagi o'lchovni aldash oson: 30-kuni bolalarni nofaol
        qilib, 1-kuni qaytarish kifoya. Eng yuqori nuqta esa haqiqatda
        iste'mol qilingan xizmatni aks ettiradi (docs/03 §20.3).
        """
        _add_children(tenant_a, 80)
        subscription = _subscription(tenant_a)

        with organization_context(tenant_a.organization.id):
            snapshot = services.record_daily_usage(subscription=subscription)
            assert snapshot.peak_children == 80

            # "Aldash" urinishi: bolalarni nofaol qilamiz.
            Child.objects.all().update(is_active=False)
            snapshot = services.record_daily_usage(subscription=subscription)

        assert snapshot.peak_children == 80, "Eng yuqori nuqta tushib ketdi"

    def test_billable_never_falls_below_the_plan_floor(self, tenant_a):
        _add_children(tenant_a, 5)
        with organization_context(tenant_a.organization.id):
            snapshot = services.record_daily_usage(subscription=_subscription(tenant_a))
        assert snapshot.peak_children == 5
        assert snapshot.billable_children == 50

    def test_a_closed_period_is_frozen(self, tenant_a):
        _add_children(tenant_a, 60)
        subscription = _subscription(tenant_a)

        with organization_context(tenant_a.organization.id):
            snapshot = services.record_daily_usage(subscription=subscription)
            services.close_period(snapshot=snapshot)

            _add_children(tenant_a, 40)  # 100 ga chiqdi
            after = services.record_daily_usage(subscription=subscription)

        assert after.peak_children == 60, "Yopilgan davr o'zgardi"

    def test_correction_is_a_new_row_with_a_note(self, tenant_a):
        """
        Tuzatish — YANGI qator, tahrir emas (D3).

        Dalilni tahrirlash "nega hisob shuncha?" degan savolga javobni
        yo'q qiladi.
        """
        with organization_context(tenant_a.organization.id):
            snapshot = services.record_daily_usage(subscription=_subscription(tenant_a))
            correction = services.adjust_usage(
                snapshot=snapshot, billable_children=70, note="Import xatosi tuzatildi"
            )
            rows = UsageSnapshot.objects.filter(
                period_year=snapshot.period_year, period_month=snapshot.period_month
            )

        assert rows.count() == 2
        assert correction.measurement_method == MeasurementMethod.MANUAL_ADJUSTMENT
        assert correction.note

    def test_correction_without_a_note_is_rejected(self, tenant_a):
        with organization_context(tenant_a.organization.id):
            snapshot = services.record_daily_usage(subscription=_subscription(tenant_a))
            with pytest.raises(BusinessRuleViolation, match="izoh"):
                services.adjust_usage(snapshot=snapshot, billable_children=70, note="   ")

    def test_invoice_requires_a_closed_snapshot(self, tenant_a):
        """
        Ochiq o'lchovdan hisob yozilmaydi.

        Aks holda hisob yozilgandan keyin ham raqam o'zgarishi mumkin
        edi va hujjat o'z asosidan ajralib qolardi.
        """
        subscription = _subscription(tenant_a)
        with organization_context(tenant_a.organization.id):
            snapshot = services.record_daily_usage(subscription=subscription)
            with pytest.raises(BusinessRuleViolation, match="Yopilmagan"):
                services.issue_invoice(
                    subscription=subscription,
                    snapshot=snapshot,
                    period_start=date(2026, 8, 1),
                    period_end=date(2026, 8, 31),
                )


class TestPaymentAndSuspension:
    def _converted(self, tenant) -> SubscriptionInvoice:
        with organization_context(tenant.organization.id):
            return services.accept_trial(subscription=_subscription(tenant))

    def test_payment_activates_the_subscription(self, tenant_a):
        invoice = self._converted(tenant_a)
        with organization_context(tenant_a.organization.id):
            services.record_subscription_payment(
                invoice=invoice, amount=invoice.total_amount, reference="MT-102"
            )
            invoice.refresh_from_db()
            subscription = _subscription(tenant_a)

        assert invoice.status == SubscriptionInvoiceStatus.PAID
        assert subscription.status == SubscriptionStatus.ACTIVE

    def test_partial_payment_leaves_the_invoice_open(self, tenant_a):
        invoice = self._converted(tenant_a)
        with organization_context(tenant_a.organization.id):
            services.record_subscription_payment(invoice=invoice, amount=Decimal("200000"))
            invoice.refresh_from_db()
        assert invoice.status == SubscriptionInvoiceStatus.ISSUED

    def test_overpayment_is_rejected(self, tenant_a):
        """
        Ortiqcha to'lov qabul qilinmaydi.

        `finance` dagi bilan bir xil qoida: ortiqcha pul jimgina
        yo'qolib ketmasligi kerak.
        """
        invoice = self._converted(tenant_a)
        with (
            organization_context(tenant_a.organization.id),
            pytest.raises(BusinessRuleViolation, match="Ortiqcha"),
        ):
            services.record_subscription_payment(
                invoice=invoice, amount=invoice.total_amount + Decimal("1")
            )

    def test_overdue_then_suspended(self, tenant_a):
        invoice = self._converted(tenant_a)
        with organization_context(tenant_a.organization.id):
            # `issued_at` ni ham orqaga suramiz: `ck_sub_invoice_due`
            # `due_at >= issued_at` ni talab qiladi va u to'g'ri qiladi —
            # yozilishidan oldin muddati o'tgan hisob mantiqsiz.
            _backdate(invoice, days=20)
            assert services.mark_past_due() == 1
            assert _subscription(tenant_a).status == SubscriptionStatus.PAST_DUE

            assert services.suspend_unpaid() == 1
            assert _subscription(tenant_a).status == SubscriptionStatus.SUSPENDED

    def test_suspension_keeps_the_data(self, tenant_a):
        """
        To'xtatilgan mijozning ma'lumoti O'CHIRILMAYDI.

        U o'z moliyaviy tarixini ko'rib turadi va istalgan payt to'lab
        qaytishi mumkin. Ma'lumotni o'chirish qaytarib bo'lmaydigan
        qaror, to'lamaslik esa vaqtinchalik holat (docs/03 §20.6).
        """
        _add_children(tenant_a, 12)
        invoice = self._converted(tenant_a)
        with organization_context(tenant_a.organization.id):
            # `issued_at` ni ham orqaga suramiz: `ck_sub_invoice_due`
            # `due_at >= issued_at` ni talab qiladi va u to'g'ri qiladi —
            # yozilishidan oldin muddati o'tgan hisob mantiqsiz.
            _backdate(invoice, days=20)
            services.mark_past_due()
            services.suspend_unpaid()

            assert Child.objects.count() == 12
            assert SubscriptionInvoice.objects.filter(pk=invoice.pk).exists()

    def test_payment_after_suspension_restores_access(self, tenant_a):
        invoice = self._converted(tenant_a)
        with organization_context(tenant_a.organization.id):
            # `issued_at` ni ham orqaga suramiz: `ck_sub_invoice_due`
            # `due_at >= issued_at` ni talab qiladi va u to'g'ri qiladi —
            # yozilishidan oldin muddati o'tgan hisob mantiqsiz.
            _backdate(invoice, days=20)
            services.mark_past_due()
            services.suspend_unpaid()

            invoice.refresh_from_db()
            services.record_subscription_payment(invoice=invoice, amount=invoice.total_amount)
            assert _subscription(tenant_a).status == SubscriptionStatus.ACTIVE


class TestTrialExpiry:
    def test_an_ignored_trial_is_cancelled(self, tenant_a):
        subscription = _subscription(tenant_a)
        with organization_context(tenant_a.organization.id):
            Subscription.objects.filter(pk=subscription.pk).update(
                trial_ends_at=timezone.now() - timedelta(days=1)
            )
            assert services.expire_trials() == 1
            assert _subscription(tenant_a).status == SubscriptionStatus.CANCELLED

    def test_a_declining_customer_pays_nothing(self, tenant_a):
        """Sinovni rad etgan mijozdan HECH NARSA olinmaydi (docs/01 §4.4)."""
        subscription = _subscription(tenant_a)
        with organization_context(tenant_a.organization.id):
            Subscription.objects.filter(pk=subscription.pk).update(
                trial_ends_at=timezone.now() - timedelta(days=1)
            )
            services.expire_trials()
            assert SubscriptionInvoice.objects.count() == 0


class TestInvoiceNumbering:
    def test_numbers_are_sequential_and_global(self, tenant_a, tenant_b):
        """
        Raqam vendor bo'ylab global, mijozlar bo'yicha emas.

        Hujjatni yozayotgan taraf bitta — vendor, va uning raqamlash
        tartibi buxgalteriya uchun uzluksiz bo'lishi kerak.
        """
        with organization_context(tenant_a.organization.id):
            first = services.accept_trial(subscription=_subscription(tenant_a))
        with organization_context(tenant_b.organization.id):
            second = services.accept_trial(subscription=_subscription(tenant_b))

        year = timezone.localdate().year
        assert first.number == f"KG-{year}-00001"
        assert second.number == f"KG-{year}-00002"
