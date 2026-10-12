"""
Radix AI edge-worker — bog'chadagi kameradan serverga signal yuboradi.

Nima qiladi
-----------
1. Kameraning RTSP oqimini BOG'CHA ICHIDA o'qiydi (parol tarmoqdan chiqmaydi).
2. Har ``--heartbeat`` soniyada serverga "kamera tirik" signalini yuboradi
   (Radix AI sahifasida kamera "Online" bo'ladi).
3. Tungi/dam olish soatlarida (``--quiet-hours``) kadrda harakat bo'lsa,
   bitta rasm bilan "Xavfsizlik" hodisasi yuboradi — rahbarga Telegram'da
   ogohlantirish ketadi.

Nima QILMAYDI (halol cheklov)
-----------------------------
Xodim qoidabuzarligi va bolaning yig'lashini aniqlash uchun o'qitilgan
model kerak; bu fayl uni o'z ichiga OLMAYDI. ``Detector`` interfeysi shu
uchun ajratilgan: tayyor model qo'shilganda ``detectors`` ro'yxatiga
qo'shiladi, server tomoni (token, hodisa, Telegram, cooldown) o'zgarmaydi.

Ishga tushirish
---------------
    pip install opencv-python-headless requests numpy defusedxml

    # Maxfiy qiymatlar muhit o'zgaruvchisida (buyruq satrida emas — `ps` ko'rsatib qo'yadi)
    set RADIX_SERVER=https://radix-crm.uz/api/v1
    set RADIX_CAMERA_TOKEN=<Radix AI -> Kameralar -> "Token berish">
    set RADIX_RTSP_URL=rtsp://login:parol@192.168.1.20:554/stream1

    python -m edge.camera_worker --test                       # ulanishni tekshirish
    python -m edge.camera_worker --quiet-hours 20:00-07:00    # doimiy ishlash

Xavfsizlik
----------
* Server manzili https bo'lishi shart (faqat localhost uchun http ruxsat).
* Token faqat ``Authorization`` sarlavhasida ketadi, logga yozilmaydi.
* RTSP manzili logga yozilmaydi (login/parol bor); log'da faqat host.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import os
import re
import secrets
import signal
import stat
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from datetime import time as dtime
from typing import Any, Protocol
from urllib.parse import quote, urlparse

import numpy as np

logger = logging.getLogger("radix.edge")

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
ANALYSIS_SIZE = (160, 90)  # kichik kulrang kadr: tez va shovqinga chidamli


# --------------------------------------------------------------------------
# Sof funksiyalar (kamera va tarmoqsiz sinanadi)
# --------------------------------------------------------------------------


def validate_server_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("RADIX_SERVER to'liq manzil bo'lishi kerak (https://...).")
    if parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        raise ValueError("Token ochiq tarmoqda ketmasligi uchun faqat https ruxsat etiladi.")
    return url.rstrip("/")


def parse_quiet_hours(value: str | None) -> tuple[dtime, dtime] | None:
    """'20:00-07:00' -> (20:00, 07:00). Bo'sh qiymat — cheklov yo'q (signal yubormaydi)."""
    if not value:
        return None
    try:
        start_s, end_s = value.split("-")
        start = datetime.strptime(start_s.strip(), "%H:%M").time()
        end = datetime.strptime(end_s.strip(), "%H:%M").time()
    except ValueError as exc:
        raise ValueError("--quiet-hours '20:00-07:00' ko'rinishida bo'lishi kerak.") from exc
    return start, end


def in_quiet_hours(now: dtime, window: tuple[dtime, dtime] | None) -> bool:
    """Yarim tundan o'tadigan oynani ham to'g'ri hal qiladi (20:00-07:00)."""
    if window is None:
        return False
    start, end = window
    if start <= end:
        return start <= now < end
    return now >= start or now < end


def motion_ratio(previous: np.ndarray, current: np.ndarray, pixel_threshold: int = 25) -> float:
    """Ikki kulrang kadr orasida o'zgargan piksellar ulushi (0..1)."""
    if previous.shape != current.shape:
        return 0.0
    diff = np.abs(previous.astype(np.int16) - current.astype(np.int16))
    return float((diff > pixel_threshold).mean())


# --------------------------------------------------------------------------
# Aniqlagichlar
# --------------------------------------------------------------------------


@dataclass
class Detection:
    kind: str  # server: staff_violation | child_distress | safety | other
    severity: str  # info | warning | critical
    note: str


class Detector(Protocol):
    """Yangi model qo'shish nuqtasi: kadr beriladi, hodisa yoki None qaytadi."""

    def update(self, frame: Any, now: datetime) -> Detection | None: ...


@dataclass
class AfterHoursMotion:
    quiet_hours: tuple[dtime, dtime] | None
    threshold: float = 0.02  # kadrning 2% i o'zgarsa
    _previous: np.ndarray | None = field(default=None, repr=False)

    def update(self, frame: Any, now: datetime) -> Detection | None:
        gray = _to_gray_small(frame)
        previous, self._previous = self._previous, gray
        if previous is None or not in_quiet_hours(now.time(), self.quiet_hours):
            return None
        ratio = motion_ratio(previous, gray)
        if ratio < self.threshold:
            return None
        return Detection("safety", "warning", f"After-hours motion: {ratio * 100:.1f}% of frame")


def _cv2() -> Any:
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "opencv-python-headless o'rnatilmagan: pip install opencv-python-headless"
        ) from exc
    return cv2


def _to_gray_small(frame: Any) -> np.ndarray:
    cv2 = _cv2()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(cv2.resize(gray, ANALYSIS_SIZE), (5, 5), 0)  # type: ignore[no-any-return]


def encode_jpeg(frame: Any, quality: int = 80) -> bytes:
    cv2 = _cv2()
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Kadrni JPEG ga o'tkazib bo'lmadi.")
    return bytes(buf.tobytes())


def encode_preview(frame: Any, max_width: int = 960, quality: int = 70) -> bytes:
    """Kuzatuv kadri: kichraytirilgan va siqilgan (trafik va saqlash uchun)."""
    cv2 = _cv2()
    height, width = frame.shape[:2]
    if width > max_width:
        frame = cv2.resize(frame, (max_width, max(1, int(height * max_width / width))))
    return encode_jpeg(frame, quality)


MAX_CAMERAS = 32
_HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.\-]{0,251}[A-Za-z0-9])?$")


@dataclass(frozen=True)
class CameraConfig:
    token: str = field(repr=False)  # logga/repr'ga tushmasin
    rtsp: str = field(repr=False)
    name: str = "camera"


def load_config(path: str) -> tuple[str, list[CameraConfig]]:
    """
    Ko'p kamerali sozlama fayli (NVR). Fayl ichida tokenlar bor, shuning uchun
    POSIX'da boshqalar o'qiy oladigan fayl rad etiladi (Windows'da ACL'ni o'zingiz tekshiring).
    """
    mode = os.stat(path).st_mode
    if os.name == "posix" and mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ValueError(f"{path}: ruxsatlar juda keng. `chmod 600` qiling.")
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict) or not isinstance(raw.get("cameras"), list):
        raise ValueError("Sozlama {'server': ..., 'cameras': [...]} ko'rinishida bo'lishi kerak.")
    server = validate_server_url(str(raw.get("server", "")))
    if not 0 < len(raw["cameras"]) <= MAX_CAMERAS:
        raise ValueError(f"Kameralar soni 1..{MAX_CAMERAS} bo'lishi kerak.")
    cameras: list[CameraConfig] = []
    for index, item in enumerate(raw["cameras"], start=1):
        token, rtsp = str(item.get("token", "")), str(item.get("rtsp", ""))
        if token.startswith("PASTE") or not token or "PAROL" in rtsp:
            raise ValueError(f"{index}-kamera: token va RTSP manzilini to'ldiring.")
        if urlparse(rtsp).scheme not in {"rtsp", "rtsps"}:
            raise ValueError(f"{index}-kamera: rtsp:// manzil kerak.")
        cameras.append(CameraConfig(token, rtsp, str(item.get("name") or f"camera-{index}")[:40]))
    return server, cameras


NVR_PATHS = {
    "hikvision": "/Streaming/Channels/{ch}01",
    "dahua": "/cam/realmonitor?channel={ch}&subtype=0",
}


def nvr_template(brand: str, host: str, user: str, channels: int, server: str) -> dict[str, Any]:
    """NVR kanallari uchun sozlama SKELETI. Parol va tokenlar qo'lda to'ldiriladi."""
    if brand not in NVR_PATHS:
        raise ValueError(f"Brend: {', '.join(NVR_PATHS)}")
    if not _HOST_RE.match(host):
        raise ValueError("NVR manzili noto'g'ri.")
    if not 1 <= channels <= MAX_CAMERAS:
        raise ValueError(f"Kanallar soni 1..{MAX_CAMERAS}.")
    base = f"rtsp://{quote(user, safe='')}:PAROL@{host}:554"
    return {
        "server": server,
        "cameras": [
            {
                "name": f"{brand}-ch{ch}",
                "token": f"PASTE_TOKEN_{ch}",
                "rtsp": base + NVR_PATHS[brand].format(ch=ch),
            }
            for ch in range(1, channels + 1)
        ],
    }


# --- ONVIF (kameralarni topish; faqat LAN'da, parol tarmoqdan chiqmaydi) ---------

_SOAP = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">'
    "<s:Header>{security}</s:Header><s:Body>{body}</s:Body></s:Envelope>"
)
_WSSE = (
    '<Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">'
    "<UsernameToken><Username>{user}</Username>"
    '<Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</Password>'
    "<Nonce>{nonce}</Nonce>"
    '<Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>'
    "</UsernameToken></Security>"
)
_GET_PROFILES = '<GetProfiles xmlns="http://www.onvif.org/ver10/media/wsdl"/>'
_GET_URI = (
    '<GetStreamUri xmlns="http://www.onvif.org/ver10/media/wsdl">'
    '<StreamSetup><Stream xmlns="http://www.onvif.org/ver10/schema">RTP-Unicast</Stream>'
    '<Transport xmlns="http://www.onvif.org/ver10/schema"><Protocol>RTSP</Protocol></Transport>'
    "</StreamSetup><ProfileToken>{token}</ProfileToken></GetStreamUri>"
)


def _xml_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def onvif_envelope(user: str, password: str, body: str, *, nonce: bytes | None = None) -> str:
    nonce = nonce or secrets.token_bytes(16)
    created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    digest = base64.b64encode(
        hashlib.sha1(nonce + created.encode() + password.encode()).digest()  # noqa: S324 — ONVIF talabi
    ).decode()
    security = _WSSE.format(
        user=_xml_escape(user),
        digest=digest,
        nonce=base64.b64encode(nonce).decode(),
        created=created,
    )
    return _SOAP.format(security=security, body=body)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def onvif_stream_uris(
    host: str, user: str, password: str, transport: Any = None
) -> list[tuple[str, str]]:
    """[(profil nomi, rtsp manzil)] — ONVIF'ni qo'llaydigan kamera/NVR'dan. Manzillar parolsiz."""
    if not _HOST_RE.match(host.split(":")[0]):
        raise ValueError("ONVIF manzili noto'g'ri.")
    try:
        from defusedxml import ElementTree  # XML tashqi qurilmadan keladi — ishonchsiz
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("pip install defusedxml") from exc
    if transport is None:

        def transport(url: str, xml: str) -> bytes:
            import requests

            reply = requests.post(
                url,
                data=xml.encode(),
                headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                timeout=8,
            )
            reply.raise_for_status()
            return reply.content

    url = f"http://{host}/onvif/device_service"
    root = ElementTree.fromstring(transport(url, onvif_envelope(user, password, _GET_PROFILES)))
    profiles = [
        (node.get("token", ""), next((c.text or "" for c in node if _local(c.tag) == "Name"), ""))
        for node in root.iter()
        if _local(node.tag) == "Profiles" and node.get("token")
    ]
    found: list[tuple[str, str]] = []
    for token, name in profiles[:MAX_CAMERAS]:
        reply = ElementTree.fromstring(
            transport(
                url, onvif_envelope(user, password, _GET_URI.format(token=_xml_escape(token)))
            )
        )
        uri = next((n.text or "" for n in reply.iter() if _local(n.tag) == "Uri"), "")
        if urlparse(uri).scheme == "rtsp":
            found.append((name or token, uri))
    return found


# --------------------------------------------------------------------------
# Server bilan aloqa
# --------------------------------------------------------------------------


class Uploader:
    def __init__(self, server: str, token: str, timeout: float = 15.0) -> None:
        import requests

        self._session = requests.Session()
        self._session.headers["Authorization"] = f"Bearer {token}"
        self._url = f"{validate_server_url(server)}/camera-ingest"
        self._timeout = timeout

    def heartbeat(self) -> dict[str, Any] | None:
        """Javobda `preview_wanted` bor: server kuzatuv kadrini kutyaptimi."""
        return self._post({})

    def preview(self, jpeg: bytes) -> bool:
        return self._post({}, {"snapshot": ("preview.jpg", jpeg, "image/jpeg")}) is not None

    def event(self, detection: Detection, jpeg: bytes | None) -> bool:
        data = {"kind": detection.kind, "severity": detection.severity, "note": detection.note}
        files = {"snapshot": ("event.jpg", jpeg, "image/jpeg")} if jpeg else None
        return self._post(data, files) is not None

    def _post(self, data: dict[str, str], files: Any = None) -> dict[str, Any] | None:
        import requests

        try:
            response = self._session.post(self._url, data=data, files=files, timeout=self._timeout)
        except requests.RequestException as exc:
            logger.warning("Serverga ulanib bo'lmadi: %s", type(exc).__name__)
            return None
        if response.status_code == 401:
            logger.error("Token noto'g'ri yoki bekor qilingan: Radix AI'da yangi token oling.")
            return None
        if not response.ok:
            logger.warning("Server javobi: %s", response.status_code)
            return None
        try:
            body = response.json().get("data")
        except ValueError:
            body = None
        return body if isinstance(body, dict) else {}


# --------------------------------------------------------------------------
# Asosiy sikl
# --------------------------------------------------------------------------


def _host_of(rtsp: str) -> str:
    return urlparse(rtsp).hostname or "?"  # login/parolsiz — logga xavfsiz


def open_stream(rtsp: str) -> Any:
    cv2 = _cv2()
    capture = cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)
    if not capture.isOpened():
        capture.release()
        raise ConnectionError(f"Kameraga ulanib bo'lmadi: {_host_of(rtsp)}")
    return capture


def run(
    *,
    rtsp: str,
    uploader: Uploader,
    detectors: list[Detector],
    fps: float = 1.0,
    heartbeat_every: float = 30.0,
    preview_every: float = 15.0,
    stop: Any = None,
    stop_event: threading.Event | None = None,
) -> None:
    stopping = {"flag": False}

    def _stop(*_: Any) -> None:
        stopping["flag"] = True

    if stop_event is None and threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, _stop)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _stop)
    if stop_event is not None:
        stop = stop_event.is_set

    backoff, last_beat, last_preview, wants_preview = 1.0, 0.0, 0.0, False
    while not stopping["flag"] and not (stop and stop()):
        try:
            capture = open_stream(rtsp)
        except ConnectionError as exc:
            logger.warning("%s; %.0f s dan keyin qayta uriniladi", exc, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
            continue
        backoff = 1.0
        logger.info("Kameraga ulandi: %s", _host_of(rtsp))
        try:
            while not stopping["flag"] and not (stop and stop()):
                ok, frame = capture.read()
                if not ok:
                    logger.warning("Kadr o'qilmadi, qayta ulanadi")
                    break
                now = datetime.now()
                if time.monotonic() - last_beat >= heartbeat_every:
                    reply = uploader.heartbeat()
                    wants_preview = bool(reply and reply.get("preview_wanted"))
                    last_beat = time.monotonic()
                if (
                    wants_preview
                    and preview_every > 0
                    and time.monotonic() - last_preview >= preview_every
                ):
                    uploader.preview(encode_preview(frame))
                    last_preview = time.monotonic()
                for detector in detectors:
                    detection = detector.update(frame, now)
                    if detection:
                        uploader.event(detection, encode_jpeg(frame))
                time.sleep(max(0.0, 1.0 / fps))
        finally:
            capture.release()


def run_many(
    cameras: list[CameraConfig], server: str, *, window: Any, args: argparse.Namespace
) -> None:
    """Har kamera uchun alohida oqim (NVR). Ctrl+C hammasini to'xtatadi."""
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
    threads = []
    for cam in cameras:
        thread = threading.Thread(
            target=run,
            kwargs={
                "rtsp": cam.rtsp,
                "uploader": Uploader(server, cam.token),
                "detectors": [AfterHoursMotion(window, args.motion_threshold)],
                "fps": args.fps,
                "heartbeat_every": args.heartbeat,
                "preview_every": args.preview_every,
                "stop_event": stop,
            },
            name=cam.name,
            daemon=True,
        )
        thread.start()
        threads.append(thread)
    logger.info("%d ta kamera ishga tushdi. To'xtatish: Ctrl+C", len(threads))
    while not stop.is_set() and any(t.is_alive() for t in threads):
        stop.wait(1.0)
    for thread in threads:
        thread.join(timeout=5)


def self_test(rtsp: str, uploader: Uploader) -> int:
    try:
        capture = open_stream(rtsp)
    except ConnectionError as exc:
        print(f"XATO: {exc}")
        return 1
    try:
        ok, frame = capture.read()
    finally:
        capture.release()
    if not ok:
        print("XATO: ulanildi, lekin kadr o'qilmadi.")
        return 1
    height, width = frame.shape[:2]
    print(f"Kamera: OK ({width}x{height})")
    if uploader.heartbeat() is None:
        print("XATO: server signalni qabul qilmadi (token yoki manzilni tekshiring).")
        return 1
    print("Server: OK (kamera Radix AI'da Online bo'ldi)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Radix AI edge-worker")
    parser.add_argument("--test", action="store_true", help="Ulanishni tekshirib chiqadi")
    parser.add_argument(
        "--quiet-hours", help="Masalan 20:00-07:00 (shu soatlarda harakat = signal)"
    )
    parser.add_argument(
        "--motion-threshold", type=float, default=0.02, help="Kadrning ulushi, 0..1"
    )
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--heartbeat", type=float, default=30.0, help="soniya")
    parser.add_argument(
        "--preview-every",
        type=float,
        default=15.0,
        help="Kuzatuv kadri oralig'i, soniya (0 = yubormaydi). Faqat CRM'da yoqilsa ketadi.",
    )
    parser.add_argument("--config", help="Ko'p kamerali (NVR) sozlama fayli (JSON)")
    parser.add_argument("--nvr-template", choices=sorted(NVR_PATHS), help="NVR sozlama skeleti")
    parser.add_argument("--nvr-host")
    parser.add_argument("--nvr-user", default="admin")
    parser.add_argument("--channels", type=int, default=4)
    parser.add_argument("--onvif", metavar="HOST[:PORT]", help="ONVIF orqali oqimlarni topish")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.nvr_template:
        if not args.nvr_host:
            print("--nvr-host kerak.")
            return 2
        try:
            skeleton = nvr_template(
                args.nvr_template,
                args.nvr_host,
                args.nvr_user,
                args.channels,
                os.environ.get("RADIX_SERVER", "https://radix-crm.uz/api/v1"),
            )
        except ValueError as exc:
            print(f"XATO: {exc}")
            return 2
        print(json.dumps(skeleton, indent=2, ensure_ascii=False))
        return 0

    if args.onvif:
        import getpass

        user = os.environ.get("RADIX_ONVIF_USER") or input("ONVIF login: ")
        password = os.environ.get("RADIX_ONVIF_PASSWORD") or getpass.getpass("ONVIF parol: ")
        try:
            uris = onvif_stream_uris(args.onvif, user, password)
        except Exception as exc:  # noqa: BLE001 — foydalanuvchiga tushunarli xabar
            print(f"XATO: ONVIF javob bermadi ({type(exc).__name__}).")
            return 1
        if not uris:
            print("Oqim topilmadi. Kamerada ONVIF yoqilganini va loginni tekshiring.")
            return 1
        for name, uri in uris:
            print(f"{name}: {uri}   (login/parolni manzilga o'zingiz qo'shing)")
        return 0

    if args.config:
        try:
            server, cameras = load_config(args.config)
            window = parse_quiet_hours(args.quiet_hours)
        except (OSError, ValueError) as exc:
            print(f"XATO: {exc}")
            return 2
        run_many(cameras, server, window=window, args=args)
        return 0

    server = os.environ.get("RADIX_SERVER", "")
    token = os.environ.get("RADIX_CAMERA_TOKEN", "")
    rtsp = os.environ.get("RADIX_RTSP_URL", "")
    if not (server and token and rtsp):
        print("RADIX_SERVER, RADIX_CAMERA_TOKEN va RADIX_RTSP_URL muhit o'zgaruvchilari kerak.")
        return 2
    try:
        uploader = Uploader(server, token)
        window = parse_quiet_hours(args.quiet_hours)
    except ValueError as exc:
        print(f"XATO: {exc}")
        return 2

    if args.test:
        return self_test(rtsp, uploader)
    detectors: list[Detector] = [AfterHoursMotion(window, args.motion_threshold)]
    run(
        rtsp=rtsp,
        uploader=uploader,
        detectors=detectors,
        fps=args.fps,
        heartbeat_every=args.heartbeat,
        preview_every=args.preview_every,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
