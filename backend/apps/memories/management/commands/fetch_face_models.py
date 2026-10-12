"""OpenCV Zoo'dan YuNet + SFace modellarini yuklaydi (Apache-2.0, ~40 MB)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.memories.engine import DETECTOR_FILE, RECOGNIZER_FILE

BASE = "https://github.com/opencv/opencv_zoo/raw/main/models"
FILES = {
    DETECTOR_FILE: f"{BASE}/face_detection_yunet/{DETECTOR_FILE}",
    RECOGNIZER_FILE: f"{BASE}/face_recognition_sface/{RECOGNIZER_FILE}",
}


class Command(BaseCommand):
    help = "Yuz tanish modellarini FACE_MODEL_DIR ga yuklaydi."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument(
            "--sha256",
            nargs=2,
            metavar=("DETECTOR", "RECOGNIZER"),
            help="Kutilgan SHA-256 (ishlab chiqarishda tavsiya etiladi)",
        )

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        target = Path(settings.FACE_MODEL_DIR)
        target.mkdir(parents=True, exist_ok=True)
        expected = dict(zip(FILES, options["sha256"] or [], strict=False))
        for name, url in FILES.items():
            data = requests.get(url, timeout=120).content
            digest = hashlib.sha256(data).hexdigest()
            if name in expected and expected[name].lower() != digest:
                raise CommandError(f"{name}: SHA-256 mos kelmadi ({digest})")
            (target / name).write_bytes(data)
            self.stdout.write(f"{name}: {len(data)} bayt, sha256={digest}")
