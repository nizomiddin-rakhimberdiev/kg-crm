"""
Yuz tanish adapteri (docs/08 §3).

`FaceEngine` interfeysi ortida OpenCV YuNet (detektor) + SFace (128-o'lchamli
vektor, Apache-2.0). InsightFace (ArcFace) keyinroq shu interfeys orqali
almashtiriladi — chaqiruvchi kod o'zgarmaydi. Modellar `FACE_MODEL_DIR` da.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from django.conf import settings
from django.utils.module_loading import import_string

__all__ = ["Face", "FaceEngine", "EngineUnavailable", "get_engine", "cosine"]

DETECTOR_FILE = "face_detection_yunet_2023mar.onnx"
RECOGNIZER_FILE = "face_recognition_sface_2021dec.onnx"


class EngineUnavailable(RuntimeError):
    """Model fayllari yo'q yoki yuklanmadi."""


@dataclass(frozen=True)
class Face:
    box: tuple[float, float, float, float]  # x, y, w, h — 0..1 (rasm o'lchamiga nisbatan)
    score: float
    embedding: np.ndarray  # float32, L2-normallashgan


class FaceEngine(Protocol):
    version: str

    def detect(self, image_bytes: bytes) -> list[Face]: ...


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) or 1.0))


def _decode(image_bytes: bytes) -> np.ndarray:
    import cv2

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("invalid_image")
    # Juda katta rasm xotirani to'ldirmasin (DoS): uzun tomoni 1600px gacha.
    h, w = img.shape[:2]
    scale = 1600 / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)))
    return img


class OpenCVEngine:
    version = "opencv-yunet-sface-v1"

    def __init__(self) -> None:
        base = Path(settings.FACE_MODEL_DIR)
        det, rec = base / DETECTOR_FILE, base / RECOGNIZER_FILE
        if not det.is_file() or not rec.is_file():
            raise EngineUnavailable(f"Model fayllari topilmadi: {base}")
        self._det_path, self._rec_path = str(det), str(rec)
        self._recognizer = None

    def detect(self, image_bytes: bytes) -> list[Face]:
        import cv2

        img = _decode(image_bytes)
        h, w = img.shape[:2]
        detector = cv2.FaceDetectorYN.create(self._det_path, "", (w, h), 0.8, 0.3, 50)
        if self._recognizer is None:
            self._recognizer = cv2.FaceRecognizerSF.create(self._rec_path, "")
        _, rows = detector.detect(img)
        faces: list[Face] = []
        for row in rows if rows is not None else []:
            aligned = self._recognizer.alignCrop(img, row)
            vec = self._recognizer.feature(aligned).flatten().astype(np.float32)
            x, y, bw, bh = (float(v) for v in row[:4])
            faces.append(
                Face(
                    box=(max(x / w, 0), max(y / h, 0), min(bw / w, 1), min(bh / h, 1)),
                    score=float(row[14]),
                    embedding=vec / (np.linalg.norm(vec) or 1.0),
                )
            )
        return faces


class FakeEngine:
    """
    Testlar uchun: rasm baytlaridan deterministik vektor.

    Oxirida `\nFACE:<ism>;<ism2>` bo'lgan rasm shu ismlarning har biri
    uchun bitta yuz hosil qiladi — haqiqiy model fayllarisiz butun oqimni
    (rozilik → vektor → tanish → yuborish) sinash mumkin.
    """

    version = "fake-v1"

    @staticmethod
    def vector_for(name: str) -> np.ndarray:
        seed = int.from_bytes(hashlib.sha256(name.encode()).digest()[:4], "big")
        vec = np.random.default_rng(seed).standard_normal(128).astype(np.float32)
        return vec / np.linalg.norm(vec)

    def detect(self, image_bytes: bytes) -> list[Face]:
        marker = image_bytes.rfind(b"\nFACE:")
        if marker < 0:
            return []
        names = image_bytes[marker + 6 :].split(b"\n")[0].decode().split(";")
        out = []
        for i, name in enumerate(n for n in names if n):
            out.append(
                Face(
                    box=(0.1 + 0.2 * i, 0.1, 0.15, 0.2), score=0.99, embedding=self.vector_for(name)
                )
            )
        return out


_engine: FaceEngine | None = None


def get_engine() -> FaceEngine:
    global _engine
    if (
        _engine is None
        or type(_engine).__module__ + "." + type(_engine).__name__ != settings.FACE_ENGINE
    ):
        _engine = import_string(settings.FACE_ENGINE)()
    return _engine
