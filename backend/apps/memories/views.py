"""Radix AI endpointlari (docs/08 §6). Mantiq `services.py` da."""

from __future__ import annotations

import logging
import re
from typing import Any

from django.http import FileResponse, Http404, HttpResponse
from django.utils import timezone
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser, FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.audit import services as audit
from apps.branches.selectors import resolve_branch
from apps.children.models import ChildGuardian
from apps.core.exceptions import BusinessRuleViolation
from apps.core.typing import request_user
from apps.core.viewsets import BranchCreateMixin, BranchScopedMixin, TenantViewSet
from apps.memories import services
from apps.memories.models import (
    Camera,
    CameraEvent,
    ChatKind,
    DayScheduleItem,
    EventKind,
    EventSeverity,
    EventStatus,
    FaceConsent,
    MemoryPhoto,
    PhotoSource,
    PhotoTag,
    TagStatus,
    TelegramChat,
)
from apps.memories.serializers import (
    CameraEventSerializer,
    CameraSerializer,
    CameraSignalSerializer,
    CameraTokenRequestSerializer,
    DayScheduleItemSerializer,
    FaceConsentSerializer,
    ImageUploadSerializer,
    ManualTagSerializer,
    MemoryPhotoSerializer,
    PairingRequestSerializer,
    PhotoTagSerializer,
    TelegramChatSerializer,
)
from apps.memories.tasks import alert_event_task, process_photo_task

logger = logging.getLogger(__name__)

__all__ = [
    "MemoryPhotoViewSet",
    "PhotoTagViewSet",
    "FaceConsentViewSet",
    "DayScheduleItemViewSet",
    "CameraViewSet",
    "CameraEventViewSet",
    "CameraIngestView",
    "TelegramChatViewSet",
    "TelegramWebhookView",
]


def _audit(request: Request, action_name: str, entity: str, entity_id: Any, **changes: Any) -> None:
    audit.record(
        action=action_name,
        request=request._request,
        actor=request_user(request),
        entity_type=entity,
        entity_id=entity_id,
        changes=changes,
    )


def _file_response(field: Any) -> FileResponse:
    if not field:
        raise Http404
    response = FileResponse(field.open("rb"), content_type="image/jpeg")
    # Bola rasmi proksi/brauzer keshida qolmasin.
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _bytes_response(field: Any) -> HttpResponse:
    """Kichik fayl (kuzatuv kadri): xotiraga o'qiladi, fayl dastagi ochiq qolmaydi."""
    if not field:
        raise Http404
    with field.open("rb") as handle:
        data = handle.read()
    response = HttpResponse(data, content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


class MemoryPhotoViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "memories"
    permission_action_map = {"image": "read", "reprocess": "update", "tag": "update"}
    model = MemoryPhoto
    serializer_class = MemoryPhotoSerializer
    filterset_fields = ["status", "source"]
    ordering_fields = ["taken_at", "created_at"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self) -> Any:
        return super().get_queryset().prefetch_related("tags__child")

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """`POST /memory-photos` (multipart: image, caption, branch_id) — qo'lda yuklash."""
        form = ImageUploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        user = request_user(request)
        branch = resolve_branch(user, request.data.get("branch_id"))
        upload = form.validated_data["image"]
        photo = services.store_photo(
            branch=branch,
            data=upload.read(),
            source=PhotoSource.UPLOAD,
            user=user,
            caption=form.validated_data.get("caption", ""),
        )
        process_photo_task.delay(str(user.organization_id), str(photo.id))
        photo.refresh_from_db()
        return Response(MemoryPhotoSerializer(photo).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def image(self, request: Request, pk: str | None = None) -> FileResponse:
        return _file_response(self.get_object().image)

    @action(detail=True, methods=["post"])
    def reprocess(self, request: Request, pk: str | None = None) -> Response:
        photo = self.get_object()
        result = services.process_photo(photo)
        return Response(result)

    @action(detail=True, methods=["post"])
    def tag(self, request: Request, pk: str | None = None) -> Response:
        """O'qituvchi bolani qo'lda belgilaydi (rozilik bo'lsa)."""
        photo = self.get_object()
        form = ManualTagSerializer(data=request.data, context=self.get_serializer_context())
        form.is_valid(raise_exception=True)
        tag = services.tag_manually(photo=photo, child=form.validated_data["child"])
        _audit(request, "update", "memory_photo", photo.id, tagged=str(tag.child_id))
        return Response(PhotoTagSerializer(tag).data, status=status.HTTP_201_CREATED)


class PhotoTagViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "memories"
    permission_action_map = {"confirm": "update", "reject": "update"}
    model = PhotoTag
    serializer_class = PhotoTagSerializer
    select_related_fields = ("child", "photo")
    filterset_fields = ["photo", "child", "status"]
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True, methods=["post"])
    def confirm(self, request: Request, pk: str | None = None) -> Response:
        tag = services.set_tag_status(tag=self.get_object(), status=TagStatus.CONFIRMED)
        _audit(request, "update", "photo_tag", tag.id, status="confirmed")
        return Response(PhotoTagSerializer(tag).data)

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        tag = services.set_tag_status(tag=self.get_object(), status=TagStatus.REJECTED)
        _audit(request, "update", "photo_tag", tag.id, status="rejected")
        return Response(PhotoTagSerializer(tag).data)


class FaceConsentViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "memories"
    permission_action_map = {"revoke": "update", "enroll": "create"}
    model = FaceConsent
    serializer_class = FaceConsentSerializer
    select_related_fields = ("child", "guardian")
    filterset_fields = ["child", "guardian"]
    http_method_names = ["get", "post", "head", "options"]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consent = services.grant_consent(
            child=serializer.validated_data["child"], guardian=serializer.validated_data["guardian"]
        )
        _audit(request, "create", "face_consent", consent.id, child=str(consent.child_id))
        return Response(FaceConsentSerializer(consent).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def revoke(self, request: Request, pk: str | None = None) -> Response:
        consent = self.get_object()
        if consent.revoked_at is not None:
            raise BusinessRuleViolation(gettext("Rozilik allaqachon bekor qilingan."))
        deleted = services.revoke_consent(child=consent.child)
        consent.refresh_from_db()
        _audit(request, "update", "face_consent", consent.id, revoked=True, samples_deleted=deleted)
        return Response(FaceConsentSerializer(consent).data)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def enroll(self, request: Request, pk: str | None = None) -> Response:
        consent = self.get_object()
        if consent.revoked_at is not None:
            raise BusinessRuleViolation(gettext("Rozilik bekor qilingan."))
        form = ImageUploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        services.enroll_face(child=consent.child, image_bytes=form.validated_data["image"].read())
        _audit(request, "create", "face_sample", consent.id, child=str(consent.child_id))
        return Response(FaceConsentSerializer(consent).data, status=status.HTTP_201_CREATED)


class DayScheduleItemViewSet(BranchScopedMixin, BranchCreateMixin, TenantViewSet):
    permission_module = "memories"
    model = DayScheduleItem
    serializer_class = DayScheduleItemSerializer
    filterset_fields = {"kind": ["exact"], "on_date": ["exact", "gte", "lte"]}
    ordering_fields = ["on_date", "at_time"]


class CameraViewSet(BranchScopedMixin, BranchCreateMixin, TenantViewSet):
    permission_module = "memories"
    permission_action_map = {
        "issue_token": "update",
        "revoke_token": "update",
        "preview": "read",
    }
    model = Camera
    serializer_class = CameraSerializer
    filterset_fields = ["is_active"]

    @action(detail=True, methods=["post"], url_path="token")
    def issue_token(self, request: Request, pk: str | None = None) -> Response:
        """Yangi ulanish tokeni. Ochiq matn faqat shu javobda; eskisi bekor bo'ladi."""
        camera = self.get_object()
        form = CameraTokenRequestSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        connection = form.validated_data["connection"]
        token = services.issue_camera_token(camera, connection)
        _audit(request, "update", "camera", camera.id, token_issued=True, connection=connection)
        return Response({"token": token, "connection": connection})

    def perform_update(self, serializer: Any) -> None:
        was = serializer.instance.preview_enabled
        super().perform_update(serializer)
        camera = serializer.instance
        if was != camera.preview_enabled:
            # Kadr saqlanishi/o'chirilishi bolalar tasviriga tegadi — izsiz qolmasin.
            services.set_preview_enabled(camera, camera.preview_enabled)
            _audit(
                self.request, "update", "camera", camera.id, preview_enabled=camera.preview_enabled
            )

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request: Request, pk: str | None = None) -> HttpResponse:
        """So'nggi kadr. Faqat kuzatuv yoqilgan bo'lsa; brauzer keshida qolmaydi."""
        camera = self.get_object()
        if not camera.preview_enabled:
            raise Http404
        return _bytes_response(camera.preview)

    @action(detail=True, methods=["post"], url_path="revoke-token")
    def revoke_token(self, request: Request, pk: str | None = None) -> Response:
        camera = self.get_object()
        services.revoke_camera_token(camera)
        _audit(request, "update", "camera", camera.id, token_revoked=True)
        return Response(CameraSerializer(camera).data)


class CameraEventViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "memories"
    permission_action_map = {"acknowledge": "update", "dismiss": "update", "snapshot": "read"}
    model = CameraEvent
    serializer_class = CameraEventSerializer
    select_related_fields = ("camera",)
    filterset_fields = ["kind", "severity", "status", "camera"]
    ordering_fields = ["occurred_at"]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def perform_create(self, serializer: Any) -> None:
        user = request_user(self.request)
        camera = serializer.validated_data.get("camera")
        branch = (
            camera.branch if camera else resolve_branch(user, self.request.data.get("branch_id"))
        )
        event = serializer.save(
            organization=user.organization,
            branch=branch,
            occurred_at=serializer.validated_data.get("occurred_at") or timezone.now(),
        )
        alert_event_task.delay(str(user.organization_id), str(event.id))

    def _set_status(self, request: Request, new: str) -> Response:
        event = self.get_object()
        event.status = new
        event.save(update_fields=["status", "updated_at"])
        _audit(request, "update", "camera_event", event.id, status=new)
        return Response(CameraEventSerializer(event).data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request: Request, pk: str | None = None) -> Response:
        return self._set_status(request, EventStatus.ACKNOWLEDGED)

    @action(detail=True, methods=["post"])
    def dismiss(self, request: Request, pk: str | None = None) -> Response:
        return self._set_status(request, EventStatus.DISMISSED)

    @action(detail=True, methods=["get"])
    def snapshot(self, request: Request, pk: str | None = None) -> FileResponse:
        return _file_response(self.get_object().snapshot)


class TelegramChatViewSet(BranchScopedMixin, TenantViewSet):
    permission_module = "memories"
    permission_action_map = {"pairing": "create"}
    model = TelegramChat
    serializer_class = TelegramChatSerializer
    select_related_fields = ("guardian",)
    filterset_fields = ["kind", "guardian"]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=["post"])
    def pairing(self, request: Request) -> Response:
        """Bir martalik ulash havolasi: guruh / ota-ona / rahbar."""
        form = PairingRequestSerializer(data=request.data, context=self.get_serializer_context())
        form.is_valid(raise_exception=True)
        user = request_user(request)
        kind = form.validated_data["kind"]
        guardian = form.validated_data.get("guardian")
        if kind == ChatKind.STAFF:
            branch, target_user = user.branch or resolve_branch(user, None), user
        else:
            branch = (
                guardian.branch
                if guardian
                else resolve_branch(user, form.validated_data.get("branch_id"))
            )
            target_user = None
        if guardian and not ChildGuardian.objects.filter(guardian=guardian).exists():
            raise BusinessRuleViolation(gettext("Bu vasiyning farzandi yo'q."))
        result = services.issue_pairing(
            organization=user.organization,
            branch=branch,
            kind=kind,
            guardian=guardian,
            user=target_user,
        )
        _audit(request, "create", "telegram_pairing", None, kind=kind)
        return Response(result, status=status.HTTP_201_CREATED)


class WebhookThrottle(AnonRateThrottle):
    scope = "telegram_webhook"


class CameraIngestThrottle(AnonRateThrottle):
    scope = "camera_ingest"


class RawBodyParser(BaseParser):
    """Webhook'lar JPEG yoki XML'ni xom tanada yuboradi (`*/*`). Hajmi cheklangan."""

    media_type = "*/*"

    def parse(self, stream: Any, media_type: Any = None, parser_context: Any = None) -> bytes:
        data = stream.read(services.MAX_SNAPSHOT_BYTES + 1)
        if len(data) > services.MAX_SNAPSHOT_BYTES:
            raise ParseError(gettext("So'rov juda katta."))
        return bytes(data)


_EVENT_TYPE_RE = re.compile(rb"<eventType>([\w .\-]{1,60})</eventType>")
_NOTE_KEYS = ("note", "message", "event", "eventType", "event_type", "type", "description")


def _clean_note(value: Any) -> str:
    text = value if isinstance(value, str) else ""
    return "".join(ch for ch in text if ch.isprintable())[:400]


def _webhook_fields(request: Request) -> tuple[str, str, str, bytes | None]:
    """Turli NVR/bulut formatlaridan (kind, severity, note, rasm) ajratadi. XML PARSE QILINMAYDI."""
    data = request.data
    if isinstance(data, bytes):
        content_type = (request.content_type or "").lower()
        if content_type.startswith(("image/jpeg", "image/png")):
            return EventKind.SAFETY, EventSeverity.WARNING, "", data
        match = _EVENT_TYPE_RE.search(data[:8000])
        note = match.group(1).decode("ascii", "ignore") if match else ""
        return EventKind.SAFETY, EventSeverity.WARNING, note, None
    fields = data if hasattr(data, "get") else {}
    kind = fields.get("kind")
    severity = fields.get("severity")
    note = next((_clean_note(fields.get(k)) for k in _NOTE_KEYS if fields.get(k)), "")
    upload = next(iter(request.FILES.values()), None)
    return (
        kind if kind in EventKind.values else EventKind.SAFETY,
        severity if severity in EventSeverity.values else EventSeverity.WARNING,
        note,
        upload.read() if upload else None,
    )


class CameraWebhookView(APIView):
    """
    `POST /camera-webhook[/<token>]` — NVR yoki bulut tizimi hodisa yuboradi.

    Token `Authorization: Bearer` da (afzal) yoki URL'da (faqat shu sarlavhani
    sozlay olmaydigan NVR'lar uchun; kamera `webhook` rejimida bo'lishi shart).
    URL'dagi token proksi/NVR loglariga tushadi, shuning uchun u faqat hodisa
    yozadi — kuzatuv kadrini yoza olmaydi.
    """

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    throttle_classes = [CameraIngestThrottle]
    parser_classes = [JSONParser, MultiPartParser, FormParser, RawBodyParser]

    def post(self, request: Request, token: str | None = None) -> Response:
        header = request.headers.get("Authorization", "")
        bearer = header[7:].strip() if header.lower().startswith("bearer ") else ""
        kind, severity, note, snapshot = _webhook_fields(request)
        result = services.ingest_camera_signal(
            token=bearer or token or "",
            kind=kind,
            severity=severity,
            note=note,
            snapshot=snapshot,
            via_url=not bearer,
        )
        if result is None:
            return Response(
                {"detail": gettext("Kamera tokeni noto'g'ri yoki faol emas.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(result)


class CameraIngestView(APIView):
    """
    `POST /camera-ingest` — edge-worker chaqiradi (JWT yo'q, kamera tokeni bor).

    `Authorization: Bearer <org>.<camera>.<secret>`. Token noto'g'ri bo'lsa
    sabab oshkor qilinmaydi (bitta umumiy 401). Tenant tokenning ichidagi
    tashkilotdan aniqlanadi va RLS kontekstida ishlaydi.
    """

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    throttle_classes = [CameraIngestThrottle]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request: Request) -> Response:
        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        form = CameraSignalSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data
        upload = data.get("snapshot")
        result = services.ingest_camera_signal(
            token=token,
            kind=data.get("kind"),
            severity=data["severity"],
            note=data["note"],
            snapshot=upload.read() if upload else None,
        )
        if result is None:
            return Response(
                {"detail": gettext("Kamera tokeni noto'g'ri yoki faol emas.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(result)


class TelegramWebhookView(APIView):
    """
    `POST /telegram/webhook` — Telegram chaqiradi.

    Himoya: `X-Telegram-Bot-Api-Secret-Token` doimiy-vaqt solishtiruvi.
    Sir sozlanmagan bo'lsa — endpoint yopiq (fail-closed). Tenant bu yerda
    HALI noma'lum: uni `telegram_chat` yo'nalish jadvali aniqlaydi.
    """

    permission_classes = [AllowAny]
    authentication_classes: list[Any] = []
    throttle_classes = [WebhookThrottle]

    def post(self, request: Request) -> Response:
        if not services.verify_webhook_secret(
            request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)
        payload = request.data if isinstance(request.data, dict) else {}
        try:
            services.handle_update(payload)
        except Exception:  # noqa: BLE001 — Telegram qayta-qayta yubormasligi uchun 200 qaytariladi
            logger.exception("Telegram update qayta ishlanmadi")
        return Response({"ok": True})
