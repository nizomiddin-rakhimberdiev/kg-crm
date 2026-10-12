"""Rasm bilan ishlash: begona bolalar yuzini xiralashtirish (maxfiylik)."""

from __future__ import annotations

import cv2
import numpy as np

__all__ = ["blur_regions"]


def blur_regions(image_bytes: bytes, boxes: list[list[float]]) -> bytes:
    """
    `boxes` (x, y, w, h; 0..1) ichini kuchli xiralashtirib, JPEG qaytaradi.

    Ota-onaga uning bolasi bor rasm yuboriladi, lekin boshqa oilalarning
    bolalari rasmda tanib bo'ladigan holda emas. Chiqishda EXIF yo'q
    (qayta kodlash uni olib tashlaydi — joylashuv sizmaydi).
    """
    img = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("invalid_image")
    h, w = img.shape[:2]
    for x, y, bw, bh in boxes:
        pad_x, pad_y = bw * 0.15, bh * 0.15
        x0, y0 = max(int((x - pad_x) * w), 0), max(int((y - pad_y) * h), 0)
        x1, y1 = min(int((x + bw + pad_x) * w), w), min(int((y + bh + pad_y) * h), h)
        if x1 <= x0 or y1 <= y0:
            continue
        region = img[y0:y1, x0:x1]
        k = max((x1 - x0) // 3 | 1, 3)
        img[y0:y1, x0:x1] = cv2.GaussianBlur(region, (k, k), 0)
    ok, out = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise ValueError("encode_failed")
    return out.tobytes()
