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
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.utils.translation import gettext

from apps.children.models import Child, EnrollmentStatus, Gender, Group
from apps.children.services import attach_guardian, enroll_child, upsert_guardian

__all__ = [
    "ImportReport",
    "RowError",
    "parse_rows",
    "import_children",
    "build_template",
    "COLUMNS",
]

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
    # PLAN 7.8 — tizimga o'tayotgan bog'cha uchun.
    "tariff": ("tarif", "tarif rejasi", "tariff", "narx"),
    "client_kind": ("mijoz", "mijoz turi", "holat", "client"),
    "opening_debt": ("qarzdorlik", "qarz", "eski qarz", "debt"),
}

#: "Mijoz" ustunining qiymatlari. Shablonda sukut — MAVJUD: import
#: bog'cha tizimga o'tayotganda ishlatiladi, ya'ni undagi bolalarning
#: deyarli hammasi allaqachon qatnab yuradi (PLAN 7.8).
_CLIENT_KIND_WORDS: dict[str, bool] = {
    "mavjud": True,
    "eski": True,
    "existing": True,
    "ha": True,
    "yangi": False,
    "new": False,
    "yo'q": False,
    "yoq": False,
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


# `.xlsx` — bu ZIP arxiv, ya'ni har doim shu ikki bayt bilan boshlanadi.
# Kengaytmaga ishonmaymiz: foydalanuvchi faylni `.csv` deb nomlashi
# mumkin, va aksincha.
_XLSX_SIGNATURE = b"PK\x03\x04"

# Import chegaralari (P2-003). Ikkalasi ham KENG: ular normal ishlashga
# xalaqit bermasligi, faqat tizimni yiqitadigan hajmni to'xtatishi kerak.
MAX_FILE_BYTES = 10 * 1_048_576  # 10 MB
MAX_ROWS = 2000


def _rows_from_xlsx(file_bytes: bytes) -> tuple[list[list[str]], list[RowError]]:
    """
    Excel faylining BIRINCHI varag'ini matn qatorlariga aylantiradi.

    Sana yacheykalari Excel'da `datetime` bo'lib keladi — ularni
    `dd.mm.yyyy` ga aylantiramiz, chunki `_parse_date` shu shaklni
    biladi va foydalanuvchi ham xuddi shunday yozadi.
    """
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    except Exception:  # noqa: BLE001
        # Bu yerda ATAYLAB keng ushlanadi: fayl foydalanuvchidan keladi
        # va u har qanday holatda bo'lishi mumkin — yarim yuklangan,
        # parol bilan himoyalangan, boshqa dastur yozgan. `openpyxl`
        # bunday hollarda turli xil istisno ko'taradi (`BadZipFile`,
        # `InvalidFileException`, `KeyError`…), va ularni sanab chiqishga
        # urinish ertami-kechmi bittasini o'tkazib yuboradi — o'shanda
        # mijoz tushunarli xabar o'rniga `500` ko'radi.
        return [], [
            RowError(
                0,
                "file",
                gettext(
                    "Excel faylini oʻqib boʻlmadi. Fayl toʻliq yuklanganini va "
                    "parol bilan himoyalanmaganini tekshiring."
                ),
            )
        ]

    sheet = workbook.worksheets[0]
    rows: list[list[str]] = []
    for raw_row in sheet.iter_rows(values_only=True):
        cells: list[str] = []
        for value in raw_row:
            if value is None:
                cells.append("")
            elif isinstance(value, (datetime, date)):
                cells.append(value.strftime("%d.%m.%Y"))
            elif isinstance(value, float) and value.is_integer():
                # Excel raqamlarni float qilib beradi: telefon yoki
                # yil "2021.0" bo'lib ko'rinmasligi kerak.
                cells.append(str(int(value)))
            else:
                cells.append(str(value).strip())
        # To'liq bo'sh qatorlar tashlab yuboriladi — Excel faylining
        # oxirida ular yuzlab bo'lishi mumkin.
        if any(cell for cell in cells):
            rows.append(cells)
    workbook.close()
    return rows, []


def parse_rows(file_bytes: bytes) -> tuple[list[dict[str, str]], list[RowError]]:
    """
    Excel (`.xlsx`) yoki CSV baytlarini lug'atlar ro'yxatiga aylantiradi.

    Format MAZMUNIDAN aniqlanadi, kengaytmadan emas.
    """
    if file_bytes.startswith(_XLSX_SIGNATURE):
        table, read_errors = _rows_from_xlsx(file_bytes)
        if read_errors:
            return [], read_errors
        return _rows_from_table(table)

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = file_bytes.decode("cp1251")  # Windows'dagi eski fayllar
        except UnicodeDecodeError:
            return [], [RowError(0, "file", gettext("Faylni oʻqib boʻlmadi (kodlash nomaʼlum)."))]

    # Ajratgichni aniqlaymiz: bog'chalar `,` ham, `;` ham ishlatadi.
    sample = text[:2048]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","

    table = [list(row) for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    return _rows_from_table(table)


def _rows_from_table(table: list[list[str]]) -> tuple[list[dict[str, str]], list[RowError]]:
    """
    Sarlavha + qatorlar jadvalini ichki lug'atlarga aylantiradi.

    CSV ham, Excel ham SHU yerga keladi — ustun tanish va tekshirish
    mantiqini ikki marta yozmaslik uchun.
    """
    errors: list[RowError] = []
    if not table:
        return [], [RowError(0, "file", gettext("Fayl boʻsh."))]

    header = table[0]

    mapping: dict[int, str] = {}
    for index, column in enumerate(header):
        internal = _normalize_header(column)
        if internal:
            mapping[index] = internal

    missing = {"last_name", "first_name", "date_of_birth"} - set(mapping.values())
    if missing:
        return [], [
            RowError(
                0,
                "header",
                gettext("Majburiy ustunlar topilmadi: {join}").format(
                    join=", ".join(sorted(missing))
                ),
            )
        ]

    rows: list[dict[str, str]] = []
    for line_number, raw_row in enumerate(table[1:], start=2):
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
        errors.append(RowError(line, "last_name", gettext("Familiya boʻsh.")))
    if not first_name:
        errors.append(RowError(line, "first_name", gettext("Ism boʻsh.")))

    dob = _parse_date(row.get("date_of_birth", ""))
    if dob is None:
        errors.append(
            RowError(
                line,
                "date_of_birth",
                gettext("Sana oʻqilmadi (kutilgan: 2020-05-14 yoki 14.05.2020)."),
            )
        )
    elif dob >= date.today():
        errors.append(
            RowError(
                line, "date_of_birth", gettext("Tugʻilgan sana kelajakda boʻlishi mumkin emas.")
            )
        )

    gender_raw = row.get("gender", "").strip().lower()
    gender = _GENDER_WORDS.get(gender_raw)
    if gender_raw and gender is None:
        errors.append(
            RowError(
                line,
                "gender",
                gettext("Jinsni tushunmadim: '{get}'.").format(get=row.get("gender")),
            )
        )
    gender = gender or Gender.MALE

    phone = row.get("guardian_phone", "").strip()
    guardian_name = row.get("guardian_name", "").strip()
    if phone and not guardian_name:
        errors.append(
            RowError(line, "guardian_name", gettext("Telefon bor, lekin ota-ona ismi yoʻq."))
        )

    # Mijoz turi: bo'sh bo'lsa MAVJUD (shablondagi sukut bilan bir xil).
    raw_kind = row.get("client_kind", "").strip().lower()
    is_existing = _CLIENT_KIND_WORDS.get(raw_kind, True) if raw_kind else True

    # Eski qarz. Bo'sh yoki 0 — qarz yo'q; manfiy qiymat qabul
    # qilinmaydi (avansni import qilish alohida ish va u so'ralmagan).
    opening_debt = Decimal("0")
    raw_debt = row.get("opening_debt", "").strip().replace(" ", "").replace("\u00a0", "")
    if raw_debt:
        try:
            opening_debt = Decimal(raw_debt.replace(",", "."))
        except InvalidOperation:
            errors.append(RowError(line, "opening_debt", gettext("Qarzdorlik raqam emas.")))
        else:
            if opening_debt < 0:
                errors.append(
                    RowError(
                        line, "opening_debt", gettext("Qarzdorlik manfiy boʻlishi mumkin emas.")
                    )
                )

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
        "tariff_name": row.get("tariff", "").strip(),
        "is_existing_client": is_existing,
        "opening_debt": opening_debt,
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

    # Fayl hajmi — birinchi to'siq (P2-003).
    #
    # Nega bu yerda va nega `MAX_ROWS` dan oldin: qatorlarni sanash uchun
    # avval butun faylni XOTIRAGA o'qish kerak. 200 MB lik fayl shu
    # yerdayoq so'rovni ham, ishchini ham yiqitardi — qator soniga
    # yetib borilmasdan.
    if len(file_bytes) > MAX_FILE_BYTES:
        report.errors.append(
            RowError(
                row=0,
                field="file",
                message=(
                    f"Fayl juda katta ({len(file_bytes) // 1_048_576} MB). "
                    f"Chegara — {MAX_FILE_BYTES // 1_048_576} MB. Ro'yxatni bo'lib yuboring."
                ),
            )
        )
        return report

    rows, parse_errors = parse_rows(file_bytes)
    report.errors.extend(parse_errors)
    report.total_rows = len(rows)

    if parse_errors:
        return report

    # Qator soni — ikkinchi to'siq.
    #
    # Import SO'ROV ICHIDA bajariladi, ya'ni uzun ro'yxat brauzerni
    # kutdirib qo'yadi va gunicorn timeout'iga uriladi. Chegara ataylab
    # keng: eng katta bog'cha ham 300 boladan oshmaydi, 2000 esa bir
    # necha filialni birga import qilishga ham yetadi.
    if len(rows) > MAX_ROWS:
        report.errors.append(
            RowError(
                row=0,
                field="file",
                message=(
                    f"Juda ko'p qator ({len(rows)}). "
                    f"Bir martada {MAX_ROWS} tagacha import qilinadi."
                ),
            )
        )
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
    # Tariflar nomi bo'yicha — katta-kichik harf farqi bo'lmasin
    # (kotib "Full" deb ham, "full" deb ham yozadi).
    from apps.finance.models import TariffPlan

    tariffs: dict[str, Any] = {
        plan.name.casefold(): plan
        for plan in TariffPlan.objects.filter(branch=branch, is_active=True)
    }

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
            # Import — tizimga O'TISH quroli, shuning uchun sukut
            # "mavjud mijoz": bunday bola butun oy qatnagan va uning
            # birinchi oyi proporsional hisoblanmaydi (PLAN 7.8).
            is_existing_client=data["is_existing_client"],
            tariff=tariffs.get(data["tariff_name"].casefold()) if data["tariff_name"] else None,
        )

        # Eski qarz — ledger'ga debet, ya'ni bola darhol qarzdorlar
        # ro'yxatida ko'rinadi (4-invariant).
        if data["opening_debt"] > 0:
            from apps.finance.services import record_opening_debt

            record_opening_debt(child=child, amount=data["opening_debt"])

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


# --- Shablon ---

# Shablondagi ustunlar va ularning izohi. Tartib muhim: majburiylari
# oldinda, shunda ekranga sig'may qolgan ustunlar ixtiyoriylari bo'ladi.
_TEMPLATE_COLUMNS: tuple[tuple[str, str, bool], ...] = (
    ("Familiya", "Bolaning familiyasi", True),
    ("Ism", "Bolaning ismi", True),
    ("Tug'ilgan sana", "kun.oy.yil — masalan 14.03.2021", True),
    ("Jinsi", "o'g'il yoki qiz", False),
    ("Otasining ismi", "Ixtiyoriy", False),
    ("Guruh", "Ro'yxatdan tanlang — bog'chadagi mavjud guruhlar", False),
    ("Tarif", "Ro'yxatdan tanlang — oylik to'lov rejasi", False),
    (
        "Mijoz",
        "mavjud — allaqachon qatnab yuradi (sukut); yangi — endi keladi va "
        "birinchi oyi ish kunlari bo'yicha hisoblanadi",
        False,
    ),
    ("Qarzdorlik", "Eski qarz so'mda. Qarz yo'q bo'lsa 0 qoldiring", False),
    ("Ota-ona", "Familiya va ism, masalan: Valiyeva Nodira", False),
    ("Telefon", "+998901234567 — xabar shu raqamga ketadi", False),
)

_TEMPLATE_EXAMPLES: tuple[tuple[str, ...], ...] = (
    (
        "Valiyev",
        "Ali",
        "14.03.2021",
        "o'g'il",
        "Rustamovich",
        "Quyoshcha",
        "Full",
        "mavjud",
        "0",
        "Valiyeva Nodira",
        "+998901112233",
    ),
    (
        "Karimova",
        "Zilola",
        "02.11.2020",
        "qiz",
        "",
        "Kamalak",
        "Yarim kun",
        "mavjud",
        "1200000",
        "Karimov Bahodir",
        "+998939874455",
    ),
)


def build_template(*, groups: list[str] | None = None, tariffs: list[str] | None = None) -> bytes:
    """
    To'ldirish uchun Excel shabloni.

    Nega CSV emas: bog'cha kotibi Excel'da ishlaydi, va undan "CSV
    sifatida saqlash" so'ralganda Windows'dagi Excel ajratgichni tizim
    tiliga qarab tanlaydi hamda kodlashni buzadi. Bu import oqimidagi
    eng ko'p muammo keltiradigan qadam edi — endi u umuman yo'q.

    Shablonda ikkita namuna qator bor. Ular ataylab: bo'sh jadval
    "sanani qanday yozay?" degan savolni ochiq qoldiradi, namuna esa
    javobni ko'rsatib turadi. Import ularni tanib, o'tkazib yuboradi.
    """
    from openpyxl import Workbook
    from openpyxl.comments import Comment
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Bolalar"

    header_fill = PatternFill("solid", fgColor="0E6B5B")
    required_font = Font(bold=True, color="FFFFFF")
    optional_font = Font(bold=True, color="D9EDE8")

    for index, (title, hint, required) in enumerate(_TEMPLATE_COLUMNS, start=1):
        cell = sheet.cell(row=1, column=index, value=title)
        cell.fill = header_fill
        cell.font = required_font if required else optional_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        # Izoh yacheyka IZOHI sifatida qo'yiladi, alohida qator emas:
        # qo'shimcha qatorni import ma'lumot deb o'qib qolardi.
        cell.comment = Comment(hint, "KG-CRM")
        sheet.column_dimensions[get_column_letter(index)].width = max(len(title) + 4, 18)

    for row_offset, example in enumerate(_TEMPLATE_EXAMPLES, start=2):
        for index, value in enumerate(example, start=1):
            sheet.cell(row=row_offset, column=index, value=value)

    # Sarlavhani muzlatamiz — 150 qator kiritayotgan odam ustun
    # nomlarini yo'qotmasin.
    sheet.freeze_panes = "A2"

    def dropdown(column_index: int, values: list[str], message: str) -> None:
        """
        Ustunga ro'yxat biriktiradi.

        Excel ro'yxatni formulaga QO'SHTIRNOQ ichida oladi va uning
        uzunligi 255 belgi bilan cheklangan. Bog'chada guruh ko'p
        bo'lsa (yoki nomlari uzun bo'lsa) ro'yxat sig'maydi — o'shanda
        ustun oddiy matn bo'lib qoladi: import nom bo'yicha baribir
        topadi, shunchaki oldindan tanlash qulayligi bo'lmaydi.
        Yarim ishlaydigan ro'yxatdan ko'ra shunisi yaxshi.
        """
        cleaned = [value.replace('"', "").replace(",", " ") for value in values if value.strip()]
        if not cleaned:
            return
        formula = ",".join(cleaned)
        if len(formula) > 250:
            return
        rule = DataValidation(
            type="list", formula1=f'"{formula}"', allow_blank=True, showDropDown=False
        )
        rule.error = message
        rule.errorTitle = "Noto'g'ri qiymat"
        sheet.add_data_validation(rule)
        letter = get_column_letter(column_index)
        rule.add(f"{letter}2:{letter}1000")

    # Jins: xato yozilgan qiymat importda ogohlantirish beradi, lekin
    # uni oldindan to'sish arzonroq.
    dropdown(4, ["o'g'il", "qiz"], 'Faqat "o\'g\'il" yoki "qiz" yozing.')
    # Guruh va tarif — BOG'CHANING O'ZINIKI (PLAN 7.6). Shablon
    # yuklanayotgan paytdagi ro'yxat olinadi, shuning uchun kotib nom
    # o'ylab topmaydi va xato yozmaydi.
    dropdown(6, groups or [], "Bog'chadagi guruhlardan birini tanlang.")
    dropdown(7, tariffs or [], "Bog'chadagi tariflardan birini tanlang.")
    # Mijoz turi: sukut — MAVJUD, chunki import tizimga o'tish quroli.
    dropdown(8, ["mavjud", "yangi"], 'Faqat "mavjud" yoki "yangi".')

    # Ikkinchi varaq — yo'riqnoma. Import faqat BIRINCHI varaqni o'qiydi,
    # shuning uchun bu yerdagi matn hech narsaga xalaqit bermaydi.
    guide = workbook.create_sheet("Yo'riqnoma")
    guide.column_dimensions["A"].width = 26
    guide.column_dimensions["B"].width = 68

    lines: list[tuple[str, str]] = [
        ("Qanday to'ldiriladi", ""),
        ("", ""),
        ("1-varaq", "Ma'lumotni faqat \"Bolalar\" varag'iga yozing."),
        ("Namuna qatorlar", "Ikkita namuna qator bor — ularni o'chirib, o'rniga yozing."),
        ("Majburiy ustunlar", "Familiya, Ism, Tug'ilgan sana. Qolgani ixtiyoriy."),
        ("Sana", "kun.oy.yil — masalan 14.03.2021"),
        ("Telefon", "+998901234567. SMS eslatmalar shu raqamga ketadi."),
        ("Guruh", "Nomi tizimdagi guruh bilan mos kelsa, bola avtomatik yoziladi."),
        ("", ""),
        ("Takroriy yuborish", "Xatolarni tuzatib, AYNAN shu faylni qayta yuborsangiz"),
        ("", "takroriy bola yaratilmaydi — mavjudlari yangilanadi."),
        ("", ""),
        ("Saqlash", "Faylni .xlsx holida saqlang. CSV ga aylantirish shart emas."),
    ]
    for row_index, (label, text) in enumerate(lines, start=1):
        label_cell = guide.cell(row=row_index, column=1, value=label)
        label_cell.font = Font(bold=True)
        guide.cell(row=row_index, column=2, value=text)
    guide["A1"].font = Font(bold=True, size=14, color="0E6B5B")

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
