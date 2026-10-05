"""
Kod ishlatadigan har bir tashqi kutubxona `requirements` da e'lon qilingan.

Nega kerak bo'ldi: `requests` besh joyda ishlatilardi (Telegram provayderi,
Eskiz SMS, sotuvga xabar, ikkita boshqaruv buyrug'i) — lekin
`requirements` da YO'Q edi. Lokalda u `djangorestframework-stubs` orqali
tasodifan o'rnatilgan, ya'ni hamma narsa ishlardi; production image'ida
esa u yo'q va har bir xabar yuborish `ModuleNotFoundError` bilan
yiqilardi. Buni deploy paytida bilib qoldik.

Test modul darajasidagi importlarni emas, FUNKSIYA ichidagilarni ham
ko'radi: `providers.py` da `import requests` funksiya ichida turadi va
shu sababli hech qanday import xatosi chiqmagan.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
APPS = BACKEND / "apps"
REQUIREMENTS = BACKEND / "requirements"

#: Import nomi → `requirements` dagi paket nomi (farq qilganda).
PACKAGE_OF = {
    "PIL": "pillow",
    "environ": "django-environ",
    "jwt": "djangorestframework-simplejwt",
    "psycopg": "psycopg",
    "rest_framework": "djangorestframework",
    "rest_framework_simplejwt": "djangorestframework-simplejwt",
    "django_filters": "django-filter",
    "corsheaders": "django-cors-headers",
    "django_celery_beat": "django-celery-beat",
    "openpyxl": "openpyxl",
    "cryptography": "cryptography",
    "requests": "requests",
    "celery": "celery",
    "redis": "redis",
    "django_redis": "django-redis",
}

#: Loyihaning o'z kodi va standart kutubxona tekshirilmaydi.
LOCAL = {"apps", "api", "config", "django"}


def _declared() -> set[str]:
    names: set[str] = set()
    for path in REQUIREMENTS.glob("*.txt"):
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-")):
                continue
            name = line.split("==")[0].split(">=")[0].split("[")[0].strip()
            names.add(name.lower())
    return names


def _imported() -> set[str]:
    found: set[str] = set()
    for path in APPS.rglob("*.py"):
        if "/tests/" in str(path) or "/migrations/" in str(path):
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):  # funksiya ichidagi importlar ham
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return {
        name
        for name in found
        if name not in LOCAL
        and name not in sys.stdlib_module_names
        and not name.startswith("_")
    }


def test_every_third_party_import_is_declared():
    declared = _declared()
    missing = sorted(
        name
        for name in _imported()
        if PACKAGE_OF.get(name, name).lower() not in declared
    )
    assert not missing, (
        f"Bu kutubxonalar kodda ishlatiladi, lekin requirements da yo'q: {missing}. "
        f"Lokalda ular boshqa paketning bog'liqligi sifatida o'rnatilgan bo'lishi "
        f"mumkin — production image'ida esa yo'q."
    )


def test_the_extractor_actually_sees_something():
    """Ekstraktor ishlamay qolsa, yuqoridagi test jimgina o'tib ketardi."""
    assert "requests" in _imported()
    assert len(_imported()) >= 5
