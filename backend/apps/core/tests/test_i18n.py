"""
Backend xabarlari uch tilda (docs/02 ADR-16).

Ikki savol: (1) `Accept-Language` haqiqatan javob tilini o'zgartiradimi;
(2) koddagi HAR BIR `gettext("…")` manbasi ru/en lug'atida bormi — aks
holda o'sha xabar ruscha ilovada o'zbekcha chiqib, buni hech kim
sezmasdi. Ekstraktor `makemessages` emas (xgettext talab qiladi) —
oddiy regex; shuning uchun u faqat literal manbalarni ko'radi, kodda
dinamik `gettext(o'zgaruvchi)` ishlatilmaydi.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.utils import translation

from apps.core import exceptions as core_exceptions

pytestmark = pytest.mark.django_db

BASE_DIR = Path(settings.BASE_DIR)
APPS_DIR = BASE_DIR / "apps"
LOCALE_DIR = BASE_DIR / "locale"
SKIP = ("/tests/", "/migrations/", "/platform/", "/management/", "intelligence/content")
CALL = re.compile(r"\bgettext(?:_lazy)?\(\s*((?:\"(?:[^\"\\]|\\.)*\"\s*)+)\)", re.S)


def _sources() -> set[str]:
    found: set[str] = set()
    for path in APPS_DIR.rglob("*.py"):
        text = str(path)
        if any(part in text for part in SKIP):
            continue
        for match in CALL.finditer(path.read_text()):
            parts = re.findall(r"\"((?:[^\"\\]|\\.)*)\"", match.group(1))
            found.add("".join(parts).replace('\\"', '"'))
    return found


def _po_entries(lang: str) -> dict[str, str]:
    text = (LOCALE_DIR / lang / "LC_MESSAGES" / "django.po").read_text()
    entries: dict[str, str] = {}
    for block in re.finditer(
        r"msgid ((?:\"(?:[^\"\\]|\\.)*\"\n)+)msgstr ((?:\"(?:[^\"\\]|\\.)*\"\n?)+)", text
    ):
        msgid = "".join(re.findall(r"\"((?:[^\"\\]|\\.)*)\"", block.group(1)))
        msgstr = "".join(re.findall(r"\"((?:[^\"\\]|\\.)*)\"", block.group(2)))
        if msgid:
            entries[msgid.replace('\\"', '"')] = msgstr.replace('\\"', '"')
    return entries


def test_sources_are_found():
    assert len(_sources()) > 150


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_every_source_is_translated(lang: str):
    entries = _po_entries(lang)
    missing = sorted(s for s in _sources() if s not in entries)
    assert missing == [], f"{lang} lugʻatida yoʻq: {missing[:5]}"
    empty = sorted(s for s in _sources() if entries.get(s) == "")
    assert empty == [], f"{lang} lugʻatida boʻsh: {empty[:5]}"


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_placeholders_match(lang: str):
    holes = lambda s: sorted(re.findall(r"\{[^}]+\}", s))  # noqa: E731
    broken = [k for k, v in _po_entries(lang).items() if v and holes(k) != holes(v)]
    assert broken == []


def test_compiled_catalog_is_used():
    """`.mo` yigʻilgan boʻlsa (Docker/compilemessages), tarjima ishlaydi."""
    if not (LOCALE_DIR / "ru" / "LC_MESSAGES" / "django.mo").exists():
        pytest.skip("compilemessages bajarilmagan")
    with translation.override("ru"):
        assert str(core_exceptions.BusinessRuleViolation.default_detail) != (
            "Bu amal biznes qoidasini buzadi."
        )


def test_accept_language_switches_error_message(api_client):
    """Login xatosi — soʻralgan tilda; sarlavhasiz — oʻzbekcha (LANGUAGE_CODE)."""
    if not (LOCALE_DIR / "ru" / "LC_MESSAGES" / "django.mo").exists():
        pytest.skip("compilemessages bajarilmagan")
    payload = {"email": "nobody@example.com", "password": "x"}
    uz = api_client.post("/api/v1/auth/login", payload, format="json")
    ru = api_client.post("/api/v1/auth/login", payload, format="json", HTTP_ACCEPT_LANGUAGE="ru")
    en = api_client.post("/api/v1/auth/login", payload, format="json", HTTP_ACCEPT_LANGUAGE="en")
    assert uz.status_code == ru.status_code == en.status_code == 401
    assert uz.json()["error"]["message"] == "Email yoki parol notoʻgʻri."
    assert ru.json()["error"]["message"] == "Неверный email или пароль."
    assert en.json()["error"]["message"] == "Incorrect email or password."


# --- Uchinchi tomon xabarlari (DRF, Django auth) ---
#
# DRF'da o'zbek tili yo'q, Django'da qisman. Ularsiz ilovaning ASOSIY tili
# o'zbekcha bo'la turib, maydon xatolari inglizcha chiqardi — bog'cha xodimi
# sanani xato kiritsa javobni tushunmasdi. Tarjima `vendor_i18n/locale/uz` da.

VENDOR_UZ = [
    "This field may not be blank.",
    "This field must be unique.",
    "A valid integer is required.",
    "A valid number is required.",
    "Date has wrong format. Use one of these formats instead: {format}.",
    '"{input}" is not a valid choice.',
    "Ensure this field has no more than {max_length} characters.",
    "Ensure this value is less than or equal to {max_value}.",
    "Not found.",
    "You do not have permission to perform this action.",
    "Authentication credentials were not provided.",
    "Request was throttled.",
    "This password is too common.",
    "This password is entirely numeric.",
]


@pytest.mark.parametrize("message", VENDOR_UZ)
def test_thirdparty_messages_are_uzbek(message: str):
    if not (BASE_DIR / "vendor_i18n" / "locale" / "uz" / "LC_MESSAGES" / "django.mo").exists():
        pytest.skip("compilemessages bajarilmagan")
    with translation.override("uz"):
        assert translation.gettext(message) != message, message


def test_password_length_message_is_uzbek():
    """Koʻplik shakli: msgid Django versiyasiga bogʻliq (`%d` va nomlangan)."""
    if not (BASE_DIR / "vendor_i18n" / "locale" / "uz" / "LC_MESSAGES" / "django.mo").exists():
        pytest.skip("compilemessages bajarilmagan")
    with translation.override("uz"):
        text = translation.ngettext(
            "This password is too short. It must contain at least %d character.",
            "This password is too short. It must contain at least %d characters.",
            8,
        )
    assert "qisqa" in text, text


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_no_fuzzy_entries(lang: str):
    """
    `#, fuzzy` — `msgmerge` ning TAXMINI, tarjima emas.

    Yangi matn eskisiga o'xshasa, gettext eski tarjimani nusxalab, uni
    fuzzy deb belgilaydi. Belgini shunchaki olib tashlash noto'g'ri
    tarjimani qotirib qo'yadi — aynan shunday bo'lgan: "Yangi parol
    ko'rsatilmagan." xabari ruschada "В токене не указана организация"
    bo'lib chiqardi. Har fuzzy yozuv QO'LDA tekshirilishi kerak.
    """
    text = (LOCALE_DIR / lang / "LC_MESSAGES" / "django.po").read_text()
    fuzzy = [line for line in text.splitlines() if line.startswith("#, fuzzy")]
    assert fuzzy == [], f"{lang}: {len(fuzzy)} ta tekshirilmagan tarjima"


# --- Q11: apostroflar (PLAN 4.1) ---

#: Harf—ASCII apostrof—harf. Aynan shu ketma-ketlik normallashtirilishi
#: kerak: `oʻ`/`gʻ` uchun U+02BB, tutuq uchun U+02BC.
RAW_APOSTROPHE = re.compile(r"[^\W\d_]['‘’`´][^\W\d_]", re.UNICODE)


def test_gettext_sources_use_the_uzbek_apostrophe():
    """
    Nega test kerak: bu farq KO'ZGA KO'RINMAYDI.

    ASCII `'` bilan yozilgan "to'lov" ekranda deyarli bir xil
    ko'rinadi, lekin u boshqa satr — ya'ni `.po` kaliti mos kelmaydi
    va xabar ruscha ilovada o'zbekcha chiqib qoladi. Bir marta
    normallashtirib, keyin qo'riqlash — yagona ishlaydigan yo'l.

    SMS matni ALOHIDA: u yerda apostrof ataylab ASCII'ga
    almashtiriladi (`segments.sms_safe`), chunki `ʻ` GSM-7 da yo'q va
    narxni ikki baravar qiladi. Bu almashtirish YUBORISHDA bo'ladi,
    manbada emas — shuning uchun bu test unga tegishli emas.
    """
    offenders = sorted(source for source in _sources() if RAW_APOSTROPHE.search(source))
    assert offenders == [], f"ASCII apostrof: {offenders[:5]}"


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_po_sources_use_the_uzbek_apostrophe(lang: str):
    offenders = sorted(key for key in _po_entries(lang) if RAW_APOSTROPHE.search(key))
    assert offenders == [], f"{lang}: {offenders[:5]}"


def test_catalogs_compile_without_duplicates():
    """
    `.po` fayllar msgfmt'dan oʻtishi SHART.

    Takrorlangan `msgid` msgfmt uchun fatal xato, lekin testlar uni
    sezmasdi: kataloglar faqat Docker tasvirini yigʻishda kompilyatsiya
    qilinadi. Natijada xato ishlab chiqarishga deploy paytida chiqdi —
    yaʼni eng kech va eng qimmat joyda.
    """
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "locale"
    for po in sorted(root.glob("*/LC_MESSAGES/django.po")):
        result = subprocess.run(  # noqa: S603 — buyruq ham, argumentlar ham literal
            ["msgfmt", "--check", "-o", "/dev/null", str(po)],  # noqa: S607 — PATH dagi gettext
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"{po.parent.parent.name}: {result.stderr.strip()}"
