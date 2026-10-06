"""
Bolalar CRM domeni (docs/03 §11).

Bu tizimning markaziy entitesi: davomat, moliya va kelajakdagi ota-ona
portali shunga tayanadi. `tariff_id` Sprint 4 da (finance) qo'shiladi;
`teacher_employee_id` Sprint 6 da (hr).
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy

from apps.core.models import BranchScopedModel

__all__ = ["Child", "Guardian", "ChildGuardian", "Group", "Enrollment"]


class Gender(models.TextChoices):
    MALE = "male", gettext_lazy("Oʻgʻil bola")
    FEMALE = "female", gettext_lazy("Qiz bola")


class EnrollmentStatus(models.TextChoices):
    PROSPECT = "prospect", gettext_lazy("Nomzod")
    ACTIVE = "active", gettext_lazy("Faol")
    PAUSED = "paused", gettext_lazy("Toʻxtatilgan")
    GRADUATED = "graduated", gettext_lazy("Bitirgan")
    WITHDRAWN = "withdrawn", gettext_lazy("Chiqib ketgan")


class Child(BranchScopedModel):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)

    enrollment_status = models.CharField(
        max_length=20, choices=EnrollmentStatus.choices, default=EnrollmentStatus.ACTIVE
    )
    enrolled_on = models.DateField(null=True, blank=True)

    # Bola tizimga o'tishdan OLDIN ham bog'chada bo'lganmi (PLAN 7.8).
    #
    # Ikkita amaliy savolni hal qiladi, va ikkalasi ham pulga tegadi:
    #
    # 1. **Birinchi oy proporsional hisoblanmaydi.** Yangi bola oyning
    #    25-kunida kelsa, undan 4 kunlik pul olinadi (PLAN 7.1). Eski
    #    bola esa allaqachon butun oy qatnab yurgan — unga o'sha hisob
    #    noto'g'ri bo'lardi.
    # 2. **Eski qarzini olib kiradi.** Import paytida `opening_debt`
    #    ledger'ga debet bo'lib tushadi va bola qarzdorlar ro'yxatida
    #    darhol ko'rinadi (4-invariant: qarzdorlar — ledger ustidagi
    #    hosila).
    #
    # Nega alohida bayroq, `enrolled_on` ning o'tgan oyda bo'lishi emas:
    # bog'cha eski bolaning aniq qabul sanasini ko'pincha bilmaydi, va
    # "sanasi yo'q" degan holat (PLAN 7.1 dagi xato) yana jimgina
    # to'liq oyga aylanib ketardi. Bayroq esa niyatni ochiq aytadi.
    is_existing_client = models.BooleanField(default=False)

    # Joriy tarif rejasi (docs/03 §11.1). Sprint 4 da qo'shildi.
    tariff = models.ForeignKey(
        "finance.TariffPlan",
        on_delete=models.RESTRICT,
        related_name="children",
        null=True,
        blank=True,
    )
    # Individual oylik narx — tarifSIZ (docs/03 §11.1, 2026-10).
    #
    # Xususiy bog'chada standart narx bo'lmasligi mumkin: har bir oila
    # bilan alohida kelishiladi. Narx manbai BITTA — yo tarif, yo shu
    # summa (`ck_child_one_price_source`); ikkalasi birga bo'lsa, qaysi
    # biri hisob-fakturaga tushishi noaniq qolardi. Hisob-faktura
    # summani chiqarilgan paytdagi qiymat bilan NUSXALAYDI — keyin narx
    # o'zgarsa, o'tgan oylar o'zgarmaydi (tarif bilan bir xil qoida).
    monthly_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Qidiruv kaliti (Q11, PLAN 2.7) — apostrofsiz, faqat lotin.
    #
    # "Ulug'bek", "Ulugʻbek" va "Улугбек" bitta kalitga keladi, ya'ni
    # mudira qaysi birini yozsa ham bolani topadi. Topa olmasa, u
    # "bu bola tizimda yo'q" deb ikkinchi marta kiritadi — va bitta
    # bola ikkita balansda qoladi.
    search_key = models.CharField(max_length=255, blank=True, db_index=True)

    photo_path = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    # --- Tibbiy ma'lumot (PLAN 2.1) ---
    #
    # Alohida maydonlar, umumiy `notes` ichida emas: allergiya oshxonaga
    # va tarbiyachiga KERAK bo'ladigan ma'lumot, va uni erkin matn
    # ichidan qidirish — xato qilish uchun eng qulay joy.
    allergies = models.CharField(max_length=255, blank=True)
    medical_notes = models.TextField(blank=True)

    # Ledger'dan keshlangan qiymat (docs/03 §8.2). Manba — `child_ledger_entry`;
    # bu ustun faqat ro'yxatlarni tez render qilish uchun va pul harakati
    # bilan bog'liq har qanday qaror ledger'dan qayta hisoblanadi (D3).
    # Sprint 4 (finance) da to'ldiriladi.
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # --- Holat o'zgarishi (Q5, PLAN 2.1) ---
    #
    # Auditda bolani "Chiqib ketgan" holatiga o'tkazganda na sana, na
    # sabab so'ralardi. Keyin "qachondan buyon?" degan savolga javob
    # yo'q edi — va bu savol har safar pul bilan birga keladi:
    # o'sha sanadan keyin hisob-faktura yozilmasligi kerak.
    status_changed_on = models.DateField(null=True, blank=True)
    status_reason = models.CharField(max_length=255, blank=True)

    # --- Arxiv (Q6) ---
    #
    # `is_active` ikki ma'noni ko'tarib yurardi: "o'chirilgan" va
    # "arxivlangan". Ularni ajratib bo'lmasdi, ya'ni "kim, qachon,
    # nega arxivladi?" degan savol javobsiz qolardi.
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="children_archived",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "child"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(date_of_birth__lt=models.functions.Now()),
                name="ck_child_dob_past",
            ),
            models.CheckConstraint(
                condition=models.Q(monthly_fee__isnull=True) | models.Q(monthly_fee__gt=0),
                name="ck_child_monthly_fee_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(tariff__isnull=True) | models.Q(monthly_fee__isnull=True),
                name="ck_child_one_price_source",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"], name="ix_child_org_active"),
            models.Index(
                fields=["organization", "branch", "enrollment_status"],
                name="ix_child_org_br_status",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Qidiruv kaliti HAR SAQLASHDA qayta hisoblanadi (PLAN 2.7)."""
        from apps.core.translit import search_key as _key

        self.search_key = _key(f"{self.last_name} {self.first_name} {self.middle_name}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.full_name

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name]
        return " ".join(p for p in parts if p)

    @property
    def age_years(self) -> int:
        today = timezone.localdate()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class Guardian(BranchScopedModel):
    """Ota-ona/vasiy — xabar oluvchi (docs/03 §11.2)."""

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20)
    # Ikkinchi raqam (PLAN 7.4) — IXTIYORIY.
    #
    # Oilada ko'pincha ikkita raqam bo'ladi: biri onaniki, biri ish
    # raqami yoki ikkinchi SIM. Birinchisi o'chib qolsa, bog'cha
    # ikkinchisiga qo'ng'iroq qiladi — shuning uchun u kartada
    # turishi kerak.
    #
    # Unikal EMAS va asosiy raqam o'rnini bosmaydi: `phone` — vasiyning
    # kimligi (filial ichida unikal), bu esa qo'shimcha aloqa. Lekin
    # botga ulanishda ikkalasi ham ishlaydi (ADR-27), aks holda ota-ona
    # ikkinchi raqamini yuborib "topilmadi" degan javob olardi.
    phone_alt = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    # Xabar tili (PLAN 3.4). Bo'sh = bog'chaning sukut tili. Ruscha
    # gaplashadigan oila o'zbekcha xabar olsa, u matnni o'qimaydi va
    # "xabar kelmadi" deb shikoyat qiladi.
    language = models.CharField(max_length=2, blank=True)

    # --- Telegram (PLAN 3.7, ADR-23) ---
    #
    # Asosiy kanal — Telegram bot: SMS har xabar uchun pul turadi va
    # shlyuz shartnomasini talab qiladi, Telegram esa bepul va
    # O'zbekistonda deyarli har bir ota-onada bor.
    #
    # `telegram_chat_id` — bot bilan suhbat identifikatori. Uni
    # BIZ bera olmaymiz: faqat ota-onaning o'zi botni ishga
    # tushirganda paydo bo'ladi. Shuning uchun u ruxsat DALILI ham:
    # bo'sh bo'lsa, bu odam hali xabar olishga rozilik bermagan.
    telegram_chat_id = models.CharField(max_length=32, blank=True)
    telegram_linked_at = models.DateTimeField(null=True, blank=True)
    # Havoladagi bir martalik kod: `t.me/<bot>?start=<code>`.
    #
    # Kod ichida TASHKILOT bor (`children/telegram.py:build_code`):
    # bot `/start` ni tenantni bilmagan holda oladi, va kod o'zi
    # kerakli kontekstni aytib beradi — RLS chegarasidan chiqishning
    # hojati qolmaydi. Global unikal: mijoz ma'lumoti emas, tasodifiy
    # 32 belgi.
    telegram_code = models.CharField(max_length=48, blank=True)

    # Ism ham, TELEFON ham shu kalitga tushadi (PLAN 2.7): mudira
    # ko'pincha ota-onani raqami bo'yicha qidiradi.
    search_key = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        db_table = "guardian"
        ordering = ["last_name", "first_name"]
        constraints = [
            # Telefon filial ichida takrorlanmaydi — bir oilaning ikkinchi
            # bolasi qo'shilganda vasiy qayta yaratilmasin.
            models.UniqueConstraint(
                fields=["branch", "phone"],
                condition=models.Q(is_active=True),
                name="uq_guardian_branch_phone",
            ),
            # Ulash kodi — tashkilotlar BO'YLAB unikal (yuqoridagi
            # izohga qarang). Qisman: bo'sh qiymat takrorlanadi.
            models.UniqueConstraint(
                fields=["telegram_code"],
                condition=~models.Q(telegram_code=""),
                name="uq_guardian_telegram_code",
            ),
            # Bitta Telegram suhbati — tashkilot ichida bitta vasiy.
            #
            # ATAYLAB global emas: bir ota-onaning farzandlari ikki
            # xil bog'chada bo'lishi mumkin va u ikkalasidan ham xabar
            # olishi KERAK. Global cheklov esa ikkinchi bog'chaga
            # ulanishni "kod ishlamadi" degan tushunarsiz xato bilan
            # to'xtatardi.
            models.UniqueConstraint(
                fields=["organization", "telegram_chat_id"],
                condition=~models.Q(telegram_chat_id=""),
                name="uq_guardian_telegram_chat",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Qidiruv kaliti HAR SAQLASHDA qayta hisoblanadi (PLAN 2.7)."""
        from apps.core.translit import search_key as _key

        self.search_key = _key(f"{self.last_name} {self.first_name} {self.phone} {self.phone_alt}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name}"

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name}"


class Relation(models.TextChoices):
    MOTHER = "mother", gettext_lazy("Onasi")
    FATHER = "father", gettext_lazy("Otasi")
    GRANDPARENT = "grandparent", gettext_lazy("Buvi/bobo")
    SIBLING = "sibling", gettext_lazy("Aka/opa")
    OTHER = "other", gettext_lazy("Boshqa")


class ChildGuardian(BranchScopedModel):
    """Bola ↔ vasiy ko'prigi — munosabat semantikasini olib yuradi."""

    child = models.ForeignKey(
        "children.Child", on_delete=models.CASCADE, related_name="guardian_links"
    )
    guardian = models.ForeignKey(
        "children.Guardian", on_delete=models.RESTRICT, related_name="child_links"
    )
    relation = models.CharField(max_length=20, choices=Relation.choices)
    is_primary = models.BooleanField(default=False)
    can_pickup = models.BooleanField(default=True)

    class Meta:
        db_table = "child_guardian"
        constraints = [
            models.UniqueConstraint(fields=["child", "guardian"], name="uq_child_guardian"),
            # Bolada ko'pi bilan bitta asosiy vasiy bo'ladi. "Kamida bitta"
            # shartini indeks ifodalay olmaydi — u servis qatlamida.
            models.UniqueConstraint(
                fields=["child"],
                condition=models.Q(is_primary=True),
                name="uq_child_primary_guardian",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.child_id} ← {self.guardian_id}"


class Group(BranchScopedModel):
    """Guruh (sinf)."""

    name = models.CharField(max_length=80)
    age_min = models.SmallIntegerField(null=True, blank=True)
    age_max = models.SmallIntegerField(null=True, blank=True)
    capacity = models.SmallIntegerField(default=0)

    # Faol enrollment'lardan keshlangan (docs/03 §8.2).
    enrolled_count = models.SmallIntegerField(default=0)

    # Guruhning tarbiyachisi (PLAN 2.6).
    #
    # `Employee` ga bog'lanadi, `User` ga emas: tarbiyachi avvalo
    # XODIM — uning oyligi, davomati va shartnomasi bor. Tizim hisobi
    # esa ixtiyoriy (hamma tarbiyachi ham tizimga kirmaydi) va u
    # `user.employee` orqali ulanadi.
    teacher = models.ForeignKey(
        "hr.Employee",
        on_delete=models.SET_NULL,
        related_name="groups_led",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "group"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "name"],
                condition=models.Q(is_active=True),
                name="uq_group_branch_name",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=0), name="ck_group_capacity_positive"
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(age_max__isnull=True)
                    | models.Q(age_min__isnull=True)
                    | models.Q(age_max__gte=models.F("age_min"))
                ),
                name="ck_group_age",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class EnrollmentState(models.TextChoices):
    ACTIVE = "active", gettext_lazy("Faol")
    ENDED = "ended", gettext_lazy("Tugagan")
    TRANSFERRED = "transferred", gettext_lazy("Koʻchirilgan")


class Enrollment(BranchScopedModel):
    """Bolaning guruhdagi a'zoligi — TARIX, joriy holat emas."""

    child = models.ForeignKey(
        "children.Child", on_delete=models.CASCADE, related_name="enrollments"
    )
    group = models.ForeignKey(
        "children.Group", on_delete=models.RESTRICT, related_name="enrollments"
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=EnrollmentState.choices, default=EnrollmentState.ACTIVE
    )

    class Meta:
        db_table = "enrollment"
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(end_date__isnull=True) | models.Q(end_date__gte=models.F("start_date"))
                ),
                name="ck_enrollment_dates",
            ),
            # Bolada bir vaqtda ko'pi bilan bitta OCHIQ a'zolik bo'ladi.
            # Bu indeks bo'lmasa, guruhdan guruhga ko'chirishda ikkita faol
            # yozuv qolib ketishi va bola ikki joyda hisoblanishi mumkin.
            models.UniqueConstraint(
                fields=["child"],
                condition=models.Q(end_date__isnull=True, status="active"),
                name="uq_enrollment_current",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "group", "status"], name="ix_enrollment_org_grp"),
        ]

    def __str__(self) -> str:
        return f"{self.child_id} → {self.group_id}"
