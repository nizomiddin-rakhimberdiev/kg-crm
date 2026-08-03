"""
Bolalar ro'yxatini Excel/CSV dan import qilish (docs/06 Sprint 2).

Nega bu MVP uchun majburiy: bog'cha 150 bolani kiritmaguncha tizimning
qiymatini sezmaydi. Agar bunga 10 kun ketsa, 15 kunlik sinov mahsulot
sifatidan qat'i nazar churn bilan tugaydi. Import — sinovning muvaffaqiyat
sharti (docs/01 §3.1, maqsad 13).

Uch xususiyat majburiy:
1. **Dry-run** — foydalanuvchi natijani saqlashdan OLDIN ko'radi.
2. **Har qator uchun xato hisoboti** — "10-qatorda sana noto'g'ri", umumiy
   "import muvaffaqiyatsiz" emas. Aks holda 200 qatorli faylni tuzatish
   imkonsiz bo'ladi.
3. **Idempotent** — xatolarni tuzatib faylni QAYTA yuborish takroriy bola
   yaratmasligi kerak. Bu eng ko'p uchraydigan real stsenariy.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from django.db import transaction

from apps.children.models import Child, EnrollmentStatus, Gender, Group
from apps.children.services import attach_guardian, enroll_child, upsert_guardian

__all__ = ["ImportReport", "RowError", "parse_rows", "import_children", "COLUMNS"]

# Kutilayotgan ustunlar. Kalit — ichki nom, qiymat — sarlavhaning
# mumkin bo'lgan variantlari (bog'chalar turli xil yozadi).
COLUMNS: dict[str, tuple[str, ...]] = {
    "last_name": ("familiya", "familiyasi", "last_name", "surname"),
    "first_name": ("ism", "ismi", "first_name", "name"),
    "middle_name": ("otasining ismi", "sharifi", "middle_name", "otchestvo"),
    "date_of_birth": ("tug'ilgan sana", "tugilgan sana", "date_of_birth", "dob", "sana"),
    "gender": ("jinsi", "jins", "gender"),
    "group": ("guruh", "guruhi", "group"),
    "guardian_name": ("ota-ona", "vasiy", "guardian", "ota ona"),
    "guardian_phone": ("telefon", "tel", "phone", "guardian_phone"),
}

_GENDER_WORDS: dict[str, str] = {
    "o'g'il": Gender.MALE,
    "ogil": Gender.MALE,
    "o‘g‘il": Gender.MALE,
    "erkak": Gender.MALE,
    "m": Gender.MALE,
    "male": Gender.MALE,
    "male ": Gender.MALE,
    "qiz": Gender.FEMALE,
    "ayol": Gender.FEMALE,
    "f": Gender.FEMALE,
    "female": Gender.FEMALE,
    "j": Gender.FEMALE,
}

_DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y")


@dataclass
class RowError:
    row: int
    field: str
    message: str


@dataclass
class ImportReport:
    total_rows: int = 0
    created: int = 0
    skipped_duplicates: int = 0
    errors: list[RowError] = field(default_factory=list)
    dry_run: bool = True

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "created": self.created,
            "skipped_duplicates": self.skipped_duplicates,
            "dry_run": self.dry_run,
            "errors": [{"row": e.row, "field": e.field, "message": e.message} for e in self.errors],
        }


def _normalize_header(raw: str) -> str | None:
    cleaned = raw.strip().lower().replace("ʼ", "'").replace("‘", "'")
    for internal, variants in COLUMNS.items():
        if cleaned in variants:
            return internal
    return None


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def parse_rows(file_bytes: bytes) -> tuple[list[dict[str, str]], list[RowError]]:
    """
    CSV baytlarini lug'atlar ro'yxatiga aylantiradi.

    Excel `.xlsx` ni o'qish uchun `openpyxl` kerak; MVP CSV bilan cheklanadi
    va foydalanuvchiga "Excel'da 'CSV sifatida saqlash'" deb ko'rsatiladi —
    bitta bog'liqlikni kechiktirish uchun ongli murosa.
    """
    errors: list[RowError] = []
    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("cp1251")  # Windows'dagi eski fayllar
        except UnicodeDecodeError:
            return [], [RowError(0, "file", "Faylni o'qib bo'lmadi (kodlash noma'lum).")]

    # Ajratgichni aniqlaymiz: bog'chalar `,` ham, `;` ham ishlatadi.
    sample = text[:2048]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        return [], [RowError(0, "file", "Fayl bo'sh.")]

    mapping: dict[int, str] = {}
    for index, column in enumerate(header):
        internal = _normalize_header(column)
        if internal:
            mapping[index] = internal

    missing = {"last_name", "first_name", "date_of_birth"} - set(mapping.values())
    if missing:
        return [], [
            RowError(0, "header", f"Majburiy ustunlar topilmadi: {', '.join(sorted(missing))}")
        ]

    rows: list[dict[str, str]] = []
    for line_number, raw_row in enumerate(reader, start=2):
        if not any(cell.strip() for cell in raw_row):
            continue  # bo'sh qator — jimgina o'tkazamiz
        row = dict.fromkeys(COLUMNS, "")
        for index, value in enumerate(raw_row):
            if index in mapping:
                row[mapping[index]] = value.strip()
        row["_row"] = str(line_number)
        rows.append(row)

    return rows, errors


def _validate(row: dict[str, str], line: int) -> tuple[dict[str, Any] | None, list[RowError]]:
    errors: list[RowError] = []

    last_name = row.get("last_name", "").strip()
    first_name = row.get("first_name", "").strip()
    if not last_name:
        errors.append(RowError(line, "last_name", "Familiya bo'sh."))
    if not first_name:
        errors.append(RowError(line, "first_name", "Ism bo'sh."))

    dob = _parse_date(row.get("date_of_birth", ""))
    if dob is None:
        errors.append(
            RowError(
                line, "date_of_birth", "Sana o'qilmadi (kutilgan: 2020-05-14 yoki 14.05.2020)."
            )
        )
    elif dob >= date.today():
        errors.append(
            RowError(line, "date_of_birth", "Tug'ilgan sana kelajakda bo'lishi mumkin emas.")
        )

    gender_raw = row.get("gender", "").strip().lower()
    gender = _GENDER_WORDS.get(gender_raw)
    if gender_raw and gender is None:
        errors.append(RowError(line, "gender", f"Jinsni tushunmadim: '{row.get('gender')}'."))
    gender = gender or Gender.MALE

    phone = row.get("guardian_phone", "").strip()
    guardian_name = row.get("guardian_name", "").strip()
    if phone and not guardian_name:
        errors.append(RowError(line, "guardian_name", "Telefon bor, lekin ota-ona ismi yo'q."))

    if errors:
        return None, errors

    return {
        "last_name": last_name,
        "first_name": first_name,
        "middle_name": row.get("middle_name", "").strip(),
        "date_of_birth": dob,
        "gender": gender,
        "group_name": row.get("group", "").strip(),
        "guardian_name": guardian_name,
        "guardian_phone": phone,
    }, []


@transaction.atomic
def import_children(
    *,
    organization: Any,
    branch: Any,
    file_bytes: bytes,
    dry_run: bool = True,
) -> ImportReport:
    """
    Faylni tekshiradi va (dry_run=False bo'lsa) yozadi.

    `dry_run=True` da ham to'liq validatsiya bajariladi — foydalanuvchi
    "saqlash" bosgandan keyin yangi xato chiqmasligi kerak.
    """
    report = ImportReport(dry_run=dry_run)
    rows, parse_errors = parse_rows(file_bytes)
    report.errors.extend(parse_errors)
    report.total_rows = len(rows)

    if parse_errors:
        return report

    prepared: list[dict[str, Any]] = []
    for row in rows:
        line = int(row["_row"])
        data, row_errors = _validate(row, line)
        if row_errors:
            report.errors.extend(row_errors)
        elif data:
            data["_row"] = line
            prepared.append(data)

    if report.errors:
        # Xatolar bor — hech narsa yozilmaydi. Yarim import qilingan fayl
        # eng yomon holat: foydalanuvchi qaysi qator o'tganini bilmaydi va
        # qayta yuborsa dublikat oladi.
        return report

    groups: dict[str, Group] = {}

    for data in prepared:
        # Idempotentlik: bir xil ism + tug'ilgan sana + filial = bir xil bola.
        # Bu mukammal emas (bir xil ismli egizaklar), lekin xatolarni
        # tuzatib faylni qayta yuborish — eng ko'p uchraydigan stsenariy,
        # va u dublikat yaratmasligi kerak.
        duplicate = Child.objects.filter(
            branch=branch,
            first_name__iexact=data["first_name"],
            last_name__iexact=data["last_name"],
            date_of_birth=data["date_of_birth"],
            is_active=True,
        ).exists()

        if duplicate:
            report.skipped_duplicates += 1
            continue

        report.created += 1
        if dry_run:
            continue

        child = Child.objects.create(
            organization=organization,
            branch=branch,
            first_name=data["first_name"],
            last_name=data["last_name"],
            middle_name=data["middle_name"],
            date_of_birth=data["date_of_birth"],
            gender=data["gender"],
            enrollment_status=EnrollmentStatus.ACTIVE,
        )

        if data["guardian_phone"]:
            parts = data["guardian_name"].split(maxsplit=1)
            guardian = upsert_guardian(
                organization=organization,
                branch=branch,
                phone=data["guardian_phone"],
                last_name=parts[0],
                first_name=parts[1] if len(parts) > 1 else "",
            )
            attach_guardian(child=child, guardian=guardian, relation="other", is_primary=True)

        if data["group_name"]:
            name = data["group_name"]
            if name not in groups:
                group, _ = Group.objects.get_or_create(
                    branch=branch,
                    name=name,
                    is_active=True,
                    defaults={"organization": organization, "capacity": 0},
                )
                groups[name] = group
            enroll_child(child=child, group=groups[name])

    if dry_run:
        # Dry-run hech narsa qoldirmaydi. `transaction.atomic` ichida
        # ataylab rollback qilamiz — validatsiya haqiqiy bazaga qarshi
        # ishlagan bo'lsin, lekin iz qolmasin.
        transaction.set_rollback(True)

    return report
