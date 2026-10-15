"""
Bitta tashkilotning ishchi maʼlumotini NOLGA qaytaradi.

**Nima uchun.** Mijoz tizimni sinab koʻrish uchun kiritilgan
maʼlumotni tozalab, hammasini oʻzi boshidan kiritmoqchi. Bu —
"tashkilotni oʻchirish" EMAS: hisob qoladi, odam oʻsha parol bilan
kiradi va boʻsh tizimni koʻradi.

**Nima qoladi** (ataylab):

* tashkilot, filial(lar), foydalanuvchilar va rollar — kirish uzilmaydi;
* obuna va sinov muddati — hisob-kitob buzilmaydi;
* kassa QOPLARI (harakatlari emas) — ular roʻyxatdan oʻtishda ochilgan;
* xabar shablonlari, tizim sozlamalari, shartnoma shabloni — bular
  sozlama, mijoz kiritgan maʼlumot emas;
* ochiq seanslar — odam tizimdan chiqib ketmaydi.

**Nima ketadi:** bolalar, vasiylar, guruhlar, tariflar, hisob-fakturalar,
toʻlovlar, ledger, qarz, davomat, xodimlar, oylik, avanslar, ombor,
chiqimlar, kassa harakatlari, onlayn toʻlovlar, shartnomalar, signallar,
yuborilgan xabarlar, eksportlar va audit jurnali.

**Qaytarib boʻlmaydi.** Shuning uchun uchta himoya:

1. sukut boʻyicha **dry-run** — `--apply` boʻlmasa hech narsa oʻchmaydi;
2. `--confirm <slug>` tashkilot slugʻi bilan aynan mos kelishi shart;
3. har bir jadval alohida sanaladi va natija ekranga chiqadi.

Ishlatish::

    python manage.py reset_organization_data --slug orientalkinderland
    python manage.py reset_organization_data --slug orientalkinderland \\
        --confirm orientalkinderland --apply
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from apps.core.tenancy import organization_context, platform_context
from apps.platform.purge import DERIVED_PURGE, PURGE_ORDER, _model

#: Tozalashda TEGILMAYDIGAN jadvallar.
#:
#: Roʻyxat `PURGE_ORDER` dan ayiriladi, ya'ni yangi jadval qoʻshilsa u
#: avtomatik tozalanadigan tomonga tushadi — bu ataylab: unutilgan
#: jadval "tozalandi" deb koʻrsatilgandan koʻra, tozalanib ketgani
#: xavfsizroq, chunki buyruq nolga qaytarish uchun.
KEEP: frozenset[str] = frozenset(
    {
        # Obuna — sinov muddati va hisob-kitob davom etadi.
        "apps.subscriptions.SubscriptionOnlineTransaction",
        "apps.subscriptions.SubscriptionPayment",
        "apps.subscriptions.SubscriptionInvoice",
        "apps.subscriptions.UsageSnapshot",
        "apps.subscriptions.Subscription",
        # Kirish — odam oʻsha parol bilan kiradi.
        "apps.accounts.User",
        "apps.accounts.Role",
        "apps.branches.Branch",
        # Roʻyxatdan oʻtishda ochilgan qoplar (harakatlari tozalanadi).
        "apps.cash.CashAccount",
        # Ochiq seanslar — tozalash odamni tizimdan CHIQARIB
        # yubormasligi kerak: u boʻsh tizimni oʻsha oynada koʻrishi
        # kerak, qaytadan parol terib emas.
        "apps.accounts.RefreshToken",
        # Sozlama — mijoz kiritgan maʼlumot emas.
        "apps.notifications.NotificationTemplate",
        # Qayta hisob turlari — pul siyosati sozlamasi (Bosqich 12.3).
        "apps.attendance.AbsenceKind",
        "apps.settings_app.SystemSetting",
        "apps.contracts.ContractTemplate",
    }
)

RESET_ORDER: tuple[str, ...] = tuple(path for path in PURGE_ORDER if path not in KEEP)


class Command(BaseCommand):
    help = "Bitta tashkilotning ishchi maʼlumotini nolga qaytaradi (dry-run sukut boʻyicha)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--slug", required=True, help="Tashkilot slugʻi")
        parser.add_argument("--confirm", default="", help="Slugʻni AYNAN qayta yozing")
        parser.add_argument("--apply", action="store_true", help="Haqiqatan oʻchirish")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.audit.models import AuditLog
        from apps.organizations.models import Organization

        slug = options["slug"]
        apply_it = options["apply"]

        with platform_context():
            organization = Organization.objects.filter(slug=slug).first()
            if organization is None:
                raise CommandError(f"Tashkilot topilmadi: {slug}")
            name = organization.name

        if apply_it and options["confirm"] != slug:
            raise CommandError(
                "Tasdiq mos kelmadi. Oʻchirish uchun --confirm bilan slugʻni aynan kiriting."
            )

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{name} ({slug})"))
        mode = self.style.ERROR("OʻCHIRISH") if apply_it else self.style.WARNING("dry-run")
        self.stdout.write(f"Rejim: {mode}")

        counts: dict[str, int] = {}
        with organization_context(organization.id), transaction.atomic():
            for path, lookup in DERIVED_PURGE.items():
                if path in KEEP:
                    continue
                counts[path] = self._wipe(_model(path), {lookup: organization.id}, apply_it)
            for path in RESET_ORDER:
                counts[path] = self._wipe(
                    _model(path), {"organization_id": organization.id}, apply_it
                )
            # Audit jurnali — mijoz kontekstida (ADR-10 izohi `purge.py` da).
            counts["audit_log"] = self._wipe(
                AuditLog, {"organization_id": organization.id}, apply_it
            )
            if not apply_it:
                # Dry-run: sanoq olindi, yozuv yoʻq.
                transaction.set_rollback(True)

        total = 0
        self.stdout.write("")
        for path, count in counts.items():
            if count:
                self.stdout.write(f"  {path.rsplit('.', 1)[-1]:<32} {count:>8}")
                total += count

        self.stdout.write("")
        self.stdout.write(f"  {'JAMI':<32} {total:>8}")
        self.stdout.write("")
        self.stdout.write("Qoladi: tashkilot, filial, foydalanuvchilar, rollar, obuna,")
        self.stdout.write(
            "        kassa qoplari, xabar shablonlari, sozlamalar, shartnoma shabloni."
        )
        if not apply_it:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    f"Hech narsa oʻchirilmadi. Bajarish uchun:\n"
                    f"  python manage.py reset_organization_data "
                    f"--slug {slug} --confirm {slug} --apply"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("\nTOZALANDI"))

    @staticmethod
    def _wipe(model: Any, lookup: dict[str, Any], apply_it: bool) -> int:
        manager = getattr(model, "all_objects", None) or model._default_manager
        queryset = manager.filter(**lookup)
        if not apply_it:
            return queryset.count()

        # Fayllar QATORDAN oldin: Django `queryset.delete()` `FileField`
        # blobini oʻchirmaydi, yaʼni "toza varaq" diskda qarzdorlar
        # roʻyxatini qoldirib ketardi. Productionda aynan shunday
        # boʻlgan — qator oʻchgan, CSV qolgan (PLAN 11.9).
        file_fields = [f.name for f in model._meta.fields if isinstance(f, models.FileField)]
        if file_fields:
            for row in queryset.only("pk", *file_fields):
                for field in file_fields:
                    blob = getattr(row, field, None)
                    if blob:
                        blob.delete(save=False)

        return queryset.delete()[0]
