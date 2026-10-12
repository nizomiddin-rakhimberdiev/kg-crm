"""
Radix AI biznes mantig'i (docs/08). Hamma yozuv shu yerda; view'lar yupqa.

Maxfiylik invariantlari:
  1. Yuz vektori faqat vasiy roziligi BOR bola uchun yaratiladi.
  2. Rozilik bekor qilinsa — vektorlar o'sha zahoti o'chiriladi.
  3. Ota-onaga faqat O'Z farzandi bor rasm ketadi, boshqa bolalar yuzi xiralashtiriladi.
  4. Bog'lash havolasi bir martalik, qisqa muddatli, bazada faqat xeshi.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context, platform_context
from apps.memories import bot_messages as bm
from apps.memories.crypto import decrypt_bytes, encrypt_bytes
from apps.memories.engine import EngineUnavailable, cosine, get_engine
from apps.memories.imaging import blur_regions
from apps.memories.models import (
    Camera,
    CameraConnection,
    CameraEvent,
    ChatKind,
    DayScheduleItem,
    EventSeverity,
    FaceConsent,
    FaceSample,
    MemoryPhoto,
    PairingToken,
    PhotoSource,
    PhotoStatus,
    PhotoTag,
    TagStatus,
    TelegramChat,
)
from apps.memories.telegram import TelegramError, get_client

logger = logging.getLogger(__name__)

MAX_SAMPLES_PER_CHILD = 8
PAIRING_TTL = timedelta(hours=48)
AUTO_CONFIRM_MARGIN = 0.12  # chegaradan shuncha yuqori bo'lsa — o'zi tasdiqlanadi
MAX_PHOTOS_PER_REQUEST = 10
SCHEDULE_DEFAULT_HOUR = 8
CAMERA_ONLINE_WINDOW = timedelta(minutes=2)
CAMERA_EVENT_COOLDOWN = timedelta(seconds=60)  # bir kameradan bir turdagi signal oralig'i
MAX_SNAPSHOT_BYTES = 5 * 1024 * 1024
CAMERA_PREVIEW_MIN_INTERVAL = timedelta(seconds=5)


# --------------------------------------------------------------------------
# Rozilik va yuz vektorlari
# --------------------------------------------------------------------------


@transaction.atomic
def grant_consent(*, child: Any, guardian: Any) -> FaceConsent:
    from apps.children.models import ChildGuardian

    if not ChildGuardian.objects.filter(child=child, guardian=guardian).exists():
        raise BusinessRuleViolation(gettext("Bu vasiy ushbu bolaning vasiysi emas."))
    existing = FaceConsent.objects.filter(child=child, revoked_at__isnull=True).first()
    if existing:
        return existing
    return FaceConsent.objects.create(
        organization=child.organization,
        branch=child.branch,
        child=child,
        guardian=guardian,
        given_at=timezone.now(),
    )


@transaction.atomic
def revoke_consent(*, child: Any) -> int:
    """Rozilikni bekor qiladi va bolaning BARCHA vektorlarini o'chiradi."""
    FaceConsent.objects.filter(child=child, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )
    PhotoTag.objects.filter(child=child, sent_at__isnull=True).delete()
    deleted, _ = FaceSample.objects.filter(child=child).delete()
    return deleted


def has_consent(child: Any) -> bool:
    return FaceConsent.objects.filter(child=child, revoked_at__isnull=True).exists()


def enroll_face(*, child: Any, image_bytes: bytes) -> FaceSample:
    """Bola yuzini ro'yxatga oladi: rozilik shart, kadrda ANIQ bitta yuz."""
    if not has_consent(child):
        raise BusinessRuleViolation(gettext("Vasiyning roziligisiz yuz vektori saqlanmaydi."))
    if FaceSample.objects.filter(child=child).count() >= MAX_SAMPLES_PER_CHILD:
        raise BusinessRuleViolation(gettext("Bu bola uchun namunalar soni to'ldi."))
    try:
        faces = get_engine().detect(image_bytes)
    except EngineUnavailable as exc:
        raise BusinessRuleViolation(gettext("Yuz tanish xizmati hozir ishlamayapti.")) from exc
    except ValueError as exc:
        raise BusinessRuleViolation(gettext("Rasm yaroqsiz.")) from exc
    if len(faces) != 1:
        raise BusinessRuleViolation(gettext("Rasmda aniq bitta yuz bo'lishi kerak."))
    return FaceSample.objects.create(
        organization=child.organization,
        branch=child.branch,
        child=child,
        embedding=encrypt_bytes(faces[0].embedding.astype(np.float32).tobytes()),
        model_version=get_engine().version,
    )


# --------------------------------------------------------------------------
# Rasmni tanish va yuborish
# --------------------------------------------------------------------------


def _gallery(branch_id: Any) -> dict[Any, list[np.ndarray]]:
    consented = set(
        FaceConsent.objects.filter(revoked_at__isnull=True, branch_id=branch_id).values_list(
            "child_id", flat=True
        )
    )
    gallery: dict[Any, list[np.ndarray]] = {}
    for sample in FaceSample.objects.filter(branch_id=branch_id, child_id__in=consented):
        try:
            vec = np.frombuffer(decrypt_bytes(sample.embedding), dtype=np.float32)
        except ValueError:
            logger.warning("Yuz vektori o'qilmadi: %s", sample.id)
            continue
        gallery.setdefault(sample.child_id, []).append(vec)
    return gallery


def store_photo(
    *,
    branch: Any,
    data: bytes,
    source: str,
    taken_at: datetime | None = None,
    user: Any = None,
    caption: str = "",
    telegram_message_id: int | None = None,
) -> MemoryPhoto:
    if len(data) > settings.MEMORIES_MAX_UPLOAD_BYTES:
        raise BusinessRuleViolation(gettext("Rasm hajmi juda katta."))
    photo = MemoryPhoto(
        organization=branch.organization,
        branch=branch,
        taken_at=taken_at or timezone.now(),
        source=source,
        uploaded_by=user,
        caption=caption[:200],
        telegram_message_id=telegram_message_id,
    )
    photo.image.save("p.jpg", ContentFile(data), save=False)
    photo.save()
    return photo


def recognize_photo(photo: MemoryPhoto) -> tuple[list[PhotoTag], int]:
    """Rasmdagi yuzlarni tanib, `PhotoTag` yozadi. (teglar, nomaʼlum yuzlar soni)."""
    photo.image.open("rb")
    try:
        data = photo.image.read()
    finally:
        photo.image.close()
    try:
        faces = get_engine().detect(data)
    except EngineUnavailable:
        photo.status = PhotoStatus.FAILED
        photo.save(update_fields=["status", "updated_at"])
        raise
    except ValueError:
        photo.status = PhotoStatus.FAILED
        photo.save(update_fields=["status", "updated_at"])
        return [], 0

    gallery = _gallery(photo.branch_id)
    threshold = settings.FACE_MATCH_THRESHOLD
    best: dict[Any, tuple[float, Any]] = {}  # child_id -> (score, face)
    for face in faces:
        for child_id, vectors in gallery.items():
            score = max(cosine(face.embedding, v) for v in vectors)
            if score >= threshold and score > best.get(child_id, (-1.0, None))[0]:
                best[child_id] = (score, face)
    # Bitta yuz faqat bitta bolaga: eng yuqori ballli bola yutadi.
    owner: dict[int, tuple[float, Any]] = {}
    for child_id, (score, face) in best.items():
        key = id(face)
        if key not in owner or score > owner[key][0]:
            owner[key] = (score, child_id)
    winners = {
        child_id: (score, face)
        for child_id, (score, face) in best.items()
        if owner[id(face)][1] == child_id
    }

    tags: list[PhotoTag] = []
    with transaction.atomic():
        PhotoTag.objects.filter(photo=photo, status=TagStatus.SUGGESTED).delete()
        for child_id, (score, face) in winners.items():
            tag, _ = PhotoTag.objects.update_or_create(
                photo=photo,
                child_id=child_id,
                defaults={
                    "organization": photo.organization,
                    "branch": photo.branch,
                    "confidence": min(score, 1.0),
                    "box": [round(v, 4) for v in face.box],
                    "status": TagStatus.CONFIRMED
                    if score >= threshold + AUTO_CONFIRM_MARGIN
                    else TagStatus.SUGGESTED,
                },
            )
            tags.append(tag)
        photo.faces_detected = len(faces)
        photo.face_boxes = [[round(v, 4) for v in f.box] for f in faces]
        photo.status = PhotoStatus.PROCESSED
        photo.save(update_fields=["faces_detected", "face_boxes", "status", "updated_at"])
    return tags, len(faces) - len(winners)


def _parent_chats(child: Any) -> list[TelegramChat]:
    from apps.children.models import ChildGuardian

    guardian_ids = ChildGuardian.objects.filter(child=child).values_list("guardian_id", flat=True)
    return list(TelegramChat.objects.filter(kind=ChatKind.PARENT, guardian_id__in=guardian_ids))


def deliver_tag(tag: PhotoTag) -> int:
    """Tasdiqlangan tegni ota-onalarning Telegram'iga yuboradi. Yuborilgan chatlar soni."""
    if tag.status != TagStatus.CONFIRMED or tag.sent_at is not None:
        return 0
    chats = _parent_chats(tag.child)
    if not chats:
        return 0
    photo = tag.photo
    photo.image.open("rb")
    try:
        original = photo.image.read()
    finally:
        photo.image.close()
    # Tegning o'z yuzi qoladi, qolgan barcha yuzlar xiralashadi. Quti yo'q
    # (o'qituvchi qo'lda tegladi) — o'qituvchi qarori, xiralashtirilmaydi.
    others = [b for b in photo.face_boxes if tag.box and b != tag.box]
    try:
        payload = blur_regions(original, others) if others else original
    except ValueError:
        logger.warning("Rasm xiralashtirilmadi, yuborilmaydi: %s", photo.id)
        return 0
    client = get_client()
    sent = 0
    for chat in chats:
        caption = bm.say(
            chat.language,
            "photo_caption",
            child=tag.child.first_name,
            time=timezone.localtime(photo.taken_at).strftime("%d.%m %H:%M"),
        )
        try:
            client.send_photo(chat.chat_id, payload, caption)
            sent += 1
        except TelegramError:
            logger.warning("Telegram yuborilmadi: chat=%s", chat.id)
    if sent:
        tag.sent_at = timezone.now()
        tag.save(update_fields=["sent_at", "updated_at"])
    return sent


def process_photo(photo: MemoryPhoto, *, report_chat: TelegramChat | None = None) -> dict[str, int]:
    """Tanish → yuborish → (guruh bo'lsa) o'qituvchiga hisobot."""
    client = get_client()
    try:
        tags, unknown = recognize_photo(photo)
    except EngineUnavailable:
        if report_chat:
            client.send_message(
                report_chat.chat_id, bm.say(report_chat.language, "group_engine_down")
            )
        return {"matched": 0, "unknown": 0, "sent": 0}
    sent = sum(deliver_tag(t) for t in tags if t.status == TagStatus.CONFIRMED)
    if report_chat:
        key = "group_report" if photo.faces_detected else "group_no_faces"
        client.send_message(
            report_chat.chat_id,
            bm.say(report_chat.language, key, matched=len(tags), unknown=unknown),
        )
    return {"matched": len(tags), "unknown": unknown, "sent": sent}


@transaction.atomic
def set_tag_status(*, tag: PhotoTag, status: str) -> PhotoTag:
    if status not in {TagStatus.CONFIRMED, TagStatus.REJECTED}:
        raise BusinessRuleViolation(gettext("Noto'g'ri holat."))
    if status == TagStatus.CONFIRMED and not has_consent(tag.child):
        raise BusinessRuleViolation(gettext("Vasiyning roziligisiz bola rasmi yuborilmaydi."))
    tag.status = status
    tag.save(update_fields=["status", "updated_at"])
    if status == TagStatus.CONFIRMED:
        transaction.on_commit(lambda: deliver_tag(tag))
    return tag


@transaction.atomic
def tag_manually(*, photo: MemoryPhoto, child: Any) -> PhotoTag:
    if not has_consent(child):
        raise BusinessRuleViolation(gettext("Vasiyning roziligisiz bola rasmi yuborilmaydi."))
    tag, _ = PhotoTag.objects.update_or_create(
        photo=photo,
        child=child,
        defaults={
            "organization": photo.organization,
            "branch": photo.branch,
            "confidence": 1.0,
            "status": TagStatus.CONFIRMED,
        },
    )
    transaction.on_commit(lambda: deliver_tag(tag))
    return tag


# --------------------------------------------------------------------------
# Telegram: ulash va bot
# --------------------------------------------------------------------------


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_pairing(
    *, organization: Any, branch: Any, kind: str, guardian: Any = None, user: Any = None
) -> dict[str, Any]:
    if kind == ChatKind.PARENT and guardian is None:
        raise BusinessRuleViolation(gettext("Ota-ona uchun vasiy ko'rsatilishi kerak."))
    if kind == ChatKind.STAFF and user is None:
        raise BusinessRuleViolation(gettext("Rahbar uchun foydalanuvchi ko'rsatilishi kerak."))
    if not settings.TELEGRAM_BOT_USERNAME:
        raise BusinessRuleViolation(gettext("Telegram bot sozlanmagan."))
    secret = secrets.token_urlsafe(18)
    token = f"{organization.id.hex}_{secret}"
    expires = timezone.now() + PAIRING_TTL
    PairingToken.objects.create(
        organization=organization,
        token_hash=_hash(token),
        kind=kind,
        branch=branch,
        guardian=guardian,
        user=user,
        expires_at=expires,
    )
    param = "startgroup" if kind == ChatKind.GROUP else "start"
    return {
        "url": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?{param}={token}",
        "expires_at": expires,
    }


def _consume_pairing(token: str, chat: dict[str, Any], language: str) -> str | None:
    """Muvaffaqiyatli bo'lsa — xabar kaliti, aks holda None."""
    try:
        org_hex, _, _secret = token.partition("_")
        import uuid

        org_id = uuid.UUID(hex=org_hex)
    except ValueError:
        return None
    with organization_context(org_id):
        pairing = PairingToken.objects.filter(token_hash=_hash(token), used_at__isnull=True).first()
        if pairing is None or pairing.expires_at < timezone.now():
            return None
        is_private = chat.get("type") == "private"
        if (pairing.kind == ChatKind.GROUP) == is_private:
            return "pair_wrong_chat"
        with platform_context():
            taken = (
                TelegramChat.all_objects.filter(chat_id=chat["id"])
                .exclude(organization_id=org_id)
                .exists()
            )
        if taken:
            return None
        TelegramChat.all_objects.update_or_create(
            chat_id=chat["id"],
            defaults={
                "organization": pairing.organization,
                "branch": pairing.branch,
                "kind": pairing.kind,
                "guardian": pairing.guardian,
                "user": pairing.user,
                "language": language,
                "title": (chat.get("title") or chat.get("first_name") or "")[:120],
            },
        )
        pairing.used_at = timezone.now()
        pairing.save(update_fields=["used_at", "updated_at"])
        return {
            ChatKind.GROUP: "welcome_group",
            ChatKind.PARENT: "welcome_parent",
            ChatKind.STAFF: "welcome_staff",
        }[pairing.kind]


def _lang_of(message: dict[str, Any]) -> str:
    code = ((message.get("from") or {}).get("language_code") or "uz")[:2].lower()
    return code if code in bm.SUPPORTED_LANGUAGES else "uz"


def handle_update(update: dict[str, Any]) -> None:
    """Webhook yuklamasini qayta ishlaydi. Autentifikatsiya view'da bajarilgan."""
    message = update.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("chat"), dict):
        return
    chat = message["chat"]
    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return
    client = get_client()
    text = (message.get("text") or "").strip()

    if text.startswith("/start") and len(text.split()) == 2:
        key = _consume_pairing(text.split()[1], chat, _lang_of(message))
        name = (message.get("from") or {}).get("first_name", "")
        lang = _lang_of(message)
        if key is None:
            client.send_message(chat_id, bm.say(lang, "pair_invalid"))
        else:
            client.send_message(chat_id, bm.say(lang, key, name=name))
        return

    with platform_context():
        route = TelegramChat.all_objects.filter(chat_id=chat_id).first()
    if route is None:
        if chat.get("type") == "private":
            client.send_message(chat_id, bm.say(_lang_of(message), "not_linked"))
        return

    with organization_context(route.organization_id):
        route = TelegramChat.objects.get(pk=route.pk)
        if route.kind == ChatKind.GROUP:
            _handle_group(route, message)
        elif route.kind == ChatKind.PARENT:
            _handle_parent(route, text)


def _handle_group(route: TelegramChat, message: dict[str, Any]) -> None:
    file_id = None
    if message.get("photo"):
        file_id = message["photo"][-1].get("file_id")  # eng katta o'lcham
    elif (message.get("document") or {}).get("mime_type", "").startswith("image/"):
        file_id = message["document"].get("file_id")
    if not file_id:
        return
    try:
        data = get_client().download_file(file_id)
    except (TelegramError, KeyError):
        logger.warning("Telegram fayli olinmadi")
        return
    taken = (
        datetime.fromtimestamp(message.get("date", 0), tz=timezone.get_current_timezone())
        if message.get("date")
        else None
    )
    photo = store_photo(
        branch=route.branch,
        data=data,
        source=PhotoSource.TELEGRAM,
        taken_at=taken,
        caption=message.get("caption") or "",
        telegram_message_id=message.get("message_id"),
    )
    from apps.memories.tasks import process_photo_task

    transaction.on_commit(
        lambda: process_photo_task.delay(str(route.organization_id), str(photo.id), route.chat_id)
    )


def _children_of(guardian: Any) -> list[Any]:
    from apps.children.models import Child, ChildGuardian

    ids = ChildGuardian.objects.filter(guardian=guardian).values_list("child_id", flat=True)
    return list(Child.objects.filter(pk__in=ids, is_active=True))


def _parse_range(arg: str) -> tuple[datetime, datetime] | None:
    tz = timezone.get_current_timezone()
    today = timezone.localdate()
    if arg in {"", "today"}:
        start, end = today, today
    elif arg == "week":
        start, end = today - timedelta(days=6), today
    else:
        try:
            start = end = date.fromisoformat(arg)
        except ValueError:
            return None
    return (
        datetime.combine(start, datetime.min.time(), tzinfo=tz),
        datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=tz),
    )


def _handle_parent(route: TelegramChat, text: str) -> None:
    client = get_client()
    lang = route.language
    cmd, _, arg = text.partition(" ")
    cmd = cmd.split("@")[0].lower()
    arg = arg.strip().lower()

    if cmd in {"/help", "/start"}:
        client.send_message(route.chat_id, bm.say(lang, "help_parent"))
    elif cmd == "/language":
        if arg in bm.SUPPORTED_LANGUAGES:
            route.language = arg
            route.save(update_fields=["language", "updated_at"])
            client.send_message(route.chat_id, bm.say(arg, "language_changed"))
        else:
            client.send_message(route.chat_id, bm.say(lang, "help_parent"))
    elif cmd == "/menu":
        client.send_message(
            route.chat_id, schedule_text(route.branch_id, timezone.localdate(), lang)
        )
    elif cmd == "/photos":
        window = _parse_range(arg)
        if window is None or route.guardian is None:
            client.send_message(route.chat_id, bm.say(lang, "unknown_command"))
            return
        send_album(route, window)
    else:
        client.send_message(route.chat_id, bm.say(lang, "unknown_command"))


def album_tags(children: list[Any], start: datetime, end: datetime) -> Any:
    """Faqat TASDIQLANGAN teglar, vaqt bo'yicha tartiblangan (selector sifatida ham ishlaydi)."""
    return (
        PhotoTag.objects.filter(
            child__in=children,
            status=TagStatus.CONFIRMED,
            photo__taken_at__gte=start,
            photo__taken_at__lt=end,
        )
        .select_related("photo", "child")
        .order_by("photo__taken_at")
    )


def send_album(route: TelegramChat, window: tuple[datetime, datetime]) -> None:
    client = get_client()
    tags = list(album_tags(_children_of(route.guardian), *window)[: MAX_PHOTOS_PER_REQUEST + 1])
    if not tags:
        client.send_message(route.chat_id, bm.say(route.language, "no_photos"))
        return
    shown = tags[:MAX_PHOTOS_PER_REQUEST]
    client.send_message(route.chat_id, bm.say(route.language, "photos_found", count=len(shown)))
    for tag in shown:
        photo = tag.photo
        photo.image.open("rb")
        try:
            original = photo.image.read()
        finally:
            photo.image.close()
        others = [b for b in photo.face_boxes if tag.box and b != tag.box]
        try:
            payload = blur_regions(original, others) if others else original
        except ValueError:
            continue
        caption = bm.say(
            route.language,
            "photo_caption",
            child=tag.child.first_name,
            time=timezone.localtime(photo.taken_at).strftime("%d.%m %H:%M"),
        )
        try:
            client.send_photo(route.chat_id, payload, caption)
        except TelegramError:
            logger.warning("Albom rasmi yuborilmadi")
    if len(tags) > MAX_PHOTOS_PER_REQUEST:
        client.send_message(route.chat_id, bm.say(route.language, "photos_more"))


# --------------------------------------------------------------------------
# Kun tartibi
# --------------------------------------------------------------------------


def schedule_text(branch_id: Any, on_date: date, language: str) -> str:
    items = DayScheduleItem.objects.filter(branch_id=branch_id, on_date=on_date)
    if not items:
        return bm.say(language, "schedule_empty")
    lines = [bm.say(language, "schedule_title")]
    for item in items:
        stamp = item.at_time.strftime("%H:%M") + " " if item.at_time else ""
        label = bm.say(language, f"kind_{item.kind}")
        extra = f" — {item.details}" if item.details else ""
        lines.append(f"{stamp}{label}: {item.title}{extra}")
    return "\n".join(lines)


def dispatch_schedule(now: datetime | None = None) -> int:
    """Vaqti kelgan kun tartibi elementlarini filial ota-onalariga yuboradi (joriy tenant)."""
    now = now or timezone.localtime()
    today, current = now.date(), now.time()
    from datetime import time as dtime

    due = [
        i
        for i in DayScheduleItem.objects.filter(
            on_date=today, notify=True, notified_at__isnull=True
        )
        if (i.at_time or dtime(SCHEDULE_DEFAULT_HOUR, 0)) <= current
    ]
    if not due:
        return 0
    client = get_client()
    sent = 0
    for branch_id in {i.branch_id for i in due}:
        chats = TelegramChat.objects.filter(kind=ChatKind.PARENT, branch_id=branch_id)
        for chat in chats:
            lines = [bm.say(chat.language, "schedule_title")]
            for item in (i for i in due if i.branch_id == branch_id):
                stamp = item.at_time.strftime("%H:%M") + " " if item.at_time else ""
                extra = f" — {item.details}" if item.details else ""
                lines.append(
                    f"{stamp}{bm.say(chat.language, 'kind_' + item.kind)}: {item.title}{extra}"
                )
            try:
                client.send_message(chat.chat_id, "\n".join(lines))
                sent += 1
            except TelegramError:
                logger.warning("Kun tartibi yuborilmadi: chat=%s", chat.id)
    DayScheduleItem.objects.filter(pk__in=[i.pk for i in due]).update(notified_at=timezone.now())
    return sent


# --------------------------------------------------------------------------
# Kamera hodisalari
# --------------------------------------------------------------------------


def report_camera_event(*, event: CameraEvent) -> int:
    """Rahbarlarga Telegram'da ogohlantirish (rasm dalili bilan). Yuborilganlar soni."""
    if event.severity == EventSeverity.INFO or event.alerted_at is not None:
        return 0
    chats = [
        c
        for c in TelegramChat.objects.filter(kind=ChatKind.STAFF).select_related("user")
        if c.branch_id == event.branch_id or (c.user and c.user.is_org_owner)
    ]
    client = get_client()
    evidence = None
    if event.snapshot:
        event.snapshot.open("rb")
        try:
            evidence = event.snapshot.read()
        finally:
            event.snapshot.close()
    sent = 0
    for chat in chats:
        # Tur/daraja yorliqlari ham CHATNING tilida (so'rov tilida emas).
        with translation.override(
            chat.language if chat.language in bm.SUPPORTED_LANGUAGES else "uz"
        ):
            kind, severity = str(event.get_kind_display()), str(event.get_severity_display())
        text = (
            bm.say(chat.language, "alert_title")
            + "\n"
            + bm.say(
                chat.language, "alert_line", kind=kind, severity=severity, note=event.note or "-"
            )
        )
        try:
            if evidence:
                client.send_photo(chat.chat_id, evidence, text)
            else:
                client.send_message(chat.chat_id, text)
            sent += 1
        except TelegramError:
            logger.warning("Ogohlantirish yuborilmadi: chat=%s", chat.id)
    if sent:
        event.alerted_at = timezone.now()
        event.save(update_fields=["alerted_at", "updated_at"])
    return sent


def verify_webhook_secret(provided: str | None) -> bool:
    expected = settings.TELEGRAM_WEBHOOK_SECRET
    if not expected or not provided:
        return False
    return hmac.compare_digest(provided.encode(), expected.encode())


# --------------------------------------------------------------------------
# Kamera ulanishi (edge-worker -> server)
# --------------------------------------------------------------------------
#
# Kamera oqimi (RTSP) bog'cha ichki tarmog'ida qoladi: uni bog'chadagi kichik
# kompyuterda ishlaydigan `edge/camera_worker.py` o'qiydi va serverga faqat
# signal (heartbeat, hodisa + bitta rasm) yuboradi. Server kamera
# parolini ko'rmaydi. Har kameraga alohida token: u sizib chiqsa, faqat shu
# kamera o'chiriladi (token qayta beriladi), butun tashkilot emas.


def camera_is_online(camera: Camera) -> bool:
    last = camera.last_seen_at
    return last is not None and timezone.now() - last <= CAMERA_ONLINE_WINDOW


def issue_camera_token(camera: Camera, connection: str | None = None) -> str:
    """Yangi token beradi (eskisi bekor bo'ladi). Ochiq matn FAQAT shu yerda qaytadi."""
    secret = secrets.token_urlsafe(32)
    camera.ingest_token_hash = _hash(secret)
    fields = ["ingest_token_hash", "updated_at"]
    if connection in CameraConnection.values:
        camera.connection = connection
        fields.append("connection")
    camera.save(update_fields=fields)
    return f"{camera.organization_id.hex}.{camera.id.hex}.{secret}"


def _delete_file(field: Any) -> None:
    """Faylni o'chiradi; band bo'lsa (masalan Windows'da hali yuborilayotgan) 500 bermaydi."""
    try:
        field.delete(save=False)
    except OSError:
        logger.warning("Kuzatuv kadri faylini hozir o'chirib bo'lmadi; keyingi yozishda almashadi.")
        field.name = ""


def set_preview_enabled(camera: Camera, enabled: bool) -> None:
    """Kuzatuvni yoqadi/o'chiradi. O'chirilganda saqlangan kadr DARHOL o'chadi."""
    camera.preview_enabled = enabled
    if not enabled:
        _delete_file(camera.preview)
        camera.preview_at = None
    camera.save(update_fields=["preview_enabled", "preview", "preview_at", "updated_at"])


def _store_preview(camera: Camera, data: bytes, now: datetime) -> bool:
    """So'nggi kadrni saqlaydi (faqat bittasi; eskisi o'chadi). Juda tez-tez yozmaydi."""
    if camera.preview_at and now - camera.preview_at < CAMERA_PREVIEW_MIN_INTERVAL:
        return False
    _delete_file(camera.preview)
    camera.preview.save("preview.jpg", ContentFile(data), save=False)
    camera.preview_at = now
    return True


def revoke_camera_token(camera: Camera) -> None:
    camera.ingest_token_hash = ""
    camera.save(update_fields=["ingest_token_hash", "updated_at"])


def _parse_camera_token(token: str) -> tuple[Any, Any, str] | None:
    import uuid

    parts = (token or "").split(".")
    if len(parts) != 3 or len(token) > 200:
        return None
    try:
        return uuid.UUID(hex=parts[0]), uuid.UUID(hex=parts[1]), parts[2]
    except ValueError:
        return None


def _snapshot_ok(data: bytes) -> bool:
    if not data or len(data) > MAX_SNAPSHOT_BYTES:
        return False
    return data[:3] == b"\xff\xd8\xff" or data[:8] == b"\x89PNG\r\n\x1a\n"


def ingest_camera_signal(
    *,
    token: str,
    kind: str | None = None,
    severity: str = EventSeverity.WARNING,
    note: str = "",
    snapshot: bytes | None = None,
    via_url: bool = False,
) -> dict[str, Any] | None:
    """
    Kameradan signal qabul qiladi. Token noto'g'ri bo'lsa — `None` (view 401 beradi).

    `kind` yo'q bo'lsa — faqat heartbeat (hodisa yaratilmaydi). Hodisa
    kamera bo'yicha `CAMERA_EVENT_COOLDOWN` bilan cheklanadi, aks holda
    harakatlanuvchi soya rahbarning Telegram'ini to'ldirib yuborardi.

    `kind` yo'q, lekin rasm bor va kamerada kuzatuv yoqilgan bo'lsa — rasm
    "so'nggi kadr" sifatida saqlanadi. `via_url=True` (token URL ichida,
    webhook) bo'lsa: faqat webhook kameralariga ruxsat va faqat HODISA —
    URL'dagi token loglarga tushadi, shuning uchun kadr yozolmaydi.
    """
    parsed = _parse_camera_token(token)
    if parsed is None:
        return None
    org_id, camera_id, secret = parsed
    with organization_context(org_id):
        camera = Camera.objects.filter(pk=camera_id, is_active=True).first()
        # Doimiy-vaqt solishtiruvi; kamera yo'q bo'lsa ham xesh hisoblanadi.
        expected = camera.ingest_token_hash if camera else _hash("-")
        if not hmac.compare_digest(_hash(secret), expected) or camera is None:
            return None
        if not camera.ingest_token_hash:
            return None
        if via_url and camera.connection != CameraConnection.WEBHOOK:
            return None
        now = timezone.now()
        camera.last_seen_at = now
        wants_preview = camera.preview_enabled and not via_url
        result: dict[str, Any] = {
            "accepted": True,
            "event_id": None,
            "preview_wanted": wants_preview,
        }
        if kind is None:
            if snapshot is not None and wants_preview:
                if not _snapshot_ok(snapshot):
                    raise BusinessRuleViolation(
                        gettext("Rasm JPEG yoki PNG bo'lishi va 5 MB dan oshmasligi kerak.")
                    )
                result["preview_saved"] = _store_preview(camera, snapshot, now)
            camera.save(update_fields=["last_seen_at", "preview", "preview_at", "updated_at"])
            return result
        camera.save(update_fields=["last_seen_at", "updated_at"])
        if snapshot is not None and not _snapshot_ok(snapshot):
            raise BusinessRuleViolation(
                gettext("Rasm JPEG yoki PNG bo'lishi va 5 MB dan oshmasligi kerak.")
            )
        recent = CameraEvent.objects.filter(
            camera=camera, kind=kind, occurred_at__gte=now - CAMERA_EVENT_COOLDOWN
        ).exists()
        if recent:
            result.update(accepted=False, reason="cooldown")
            return result
        event = CameraEvent(
            organization=camera.organization,
            branch=camera.branch,
            camera=camera,
            kind=kind,
            severity=severity,
            note=(note or "")[:400],
            occurred_at=now,
        )
        if snapshot is not None:
            event.snapshot.save("event.jpg", ContentFile(snapshot), save=False)
        event.save()
        from apps.memories.tasks import alert_event_task

        organization_id, event_id = str(org_id), str(event.id)
        transaction.on_commit(lambda: alert_event_task.delay(organization_id, event_id))
        result["event_id"] = str(event.id)
        return result
