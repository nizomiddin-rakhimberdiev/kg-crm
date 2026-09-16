"""
Platforma konsoli endpointlari (docs/04 §19).

**Bu yerda birorta ham endpoint bola, vasiy, to'lov, oylik yoki davomat
qatorini qaytarmaydi.** Faqat agregat sonlar.

Sabab hujjatda aniq yozilgan: cross-tenant ma'lumot endpointi paydo
bo'lishi bilan u hujumchining nishoniga va xatoning yo'liga aylanadi.
Konsolni metama'lumot bilan cheklash buzilgan vendor akkauntining
ta'sir doirasini "mijozlar kimligini biladi" darajasida ushlab turadi —
"mamlakatdagi har bir bolaning yozuvini o'qiydi" emas.
"""

from __future__ import annotations

from typing import Any

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import BusinessRuleViolation
from apps.core.tenancy import organization_context, platform_context
from apps.platform import services
from apps.platform.authentication import (
    PlatformTokenAuthentication,
    authenticate_platform_user,
    issue_platform_token,
)
from apps.platform.models import Lead, PlatformUser, SupportGrant
from apps.platform.permissions import IsPlatformAdmin, IsPlatformStaff
from apps.platform.serializers import (
    ExtendTrialSerializer,
    LeadSerializer,
    OrganizationCreateSerializer,
    PlatformLoginSerializer,
    ReasonSerializer,
    RecordPaymentSerializer,
    SupportGrantRequestSerializer,
    SupportGrantSerializer,
)
from apps.subscriptions.models import SubscriptionInvoice, SubscriptionPlan

__all__ = ["PlatformLoginView", "PlatformConsoleViewSet"]


class PlatformLoginView(APIView):
    """
    `POST /platform/auth/login` — email + parol + TOTP.

    Mijoz login yo'lidan butunlay alohida (ADR-10): boshqa jadval,
    boshqa token turi, majburiy ikkinchi omil.
    """

    # Autentifikator ro'yxati BO'SH EMAS, garchi login anonim bo'lsa
    # ham: DRF xato kodini birinchi autentifikatordan oladi va u
    # bo'lmasa `401` o'rniga `403` qaytaradi. `PlatformTokenAuthentication`
    # sarlavha bo'lmaganda `None` qaytaradi, ya'ni login baribir anonim.
    authentication_classes = [PlatformTokenAuthentication]
    permission_classes: list[Any] = []

    def post(self, request: Request) -> Response:
        serializer = PlatformLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_platform_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            code=serializer.validated_data["code"],
        )
        services.record_platform_action(
            actor=user, action="login", entity_type="platform_user", request=request._request
        )
        return Response(
            {
                "access": issue_platform_token(user),
                "user": {"email": user.email, "full_name": user.full_name, "role": user.role},
            }
        )


class PlatformConsoleViewSet(viewsets.ViewSet):
    """`/platform/*` — vendor konsoli."""

    authentication_classes = [PlatformTokenAuthentication]
    permission_classes = [IsPlatformStaff]

    @staticmethod
    def _actor(request: Request) -> PlatformUser:
        """
        `request.user` — bu yerda HAR DOIM `PlatformUser`.

        `IsPlatformStaff` buni allaqachon ta'minlagan; bu yordamchi
        faqat tip tekshiruvchisiga shuni aytadi va kelajakda kimdir
        autentifikatorni almashtirsa, xato shu yerda chiqadi.
        """
        user = request.user
        if not isinstance(user, PlatformUser):  # pragma: no cover — ruxsat sinfi ushlaydi
            raise BusinessRuleViolation("Platforma hisobi talab qilinadi.")
        return user

    def _admin_only(self, request: Request) -> None:
        if not IsPlatformAdmin().has_permission(request, self):
            raise BusinessRuleViolation("Bu amal faqat administrator uchun.")

    # --- Metama'lumot ---

    @action(detail=False, methods=["get"])
    def organizations(self, request: Request) -> Response:
        return Response(
            services.organization_overview(
                search=request.query_params.get("search", ""),
                status=request.query_params.get("status", ""),
            )
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=r"organizations/(?P<organization_id>[0-9a-f-]{36})",
    )
    def organization_detail(self, request: Request, organization_id: str = "") -> Response:
        return Response(services.organization_detail(organization_id=organization_id))

    @action(detail=False, methods=["get"], url_path="subscriptions/expiring")
    def expiring(self, request: Request) -> Response:
        """Kunlik ish ro'yxati: tugayotgan sinovlar, muddati o'tgan hisoblar."""
        return Response(services.expiring_work_list())

    @action(detail=False, methods=["get"])
    def leads(self, request: Request) -> Response:
        """Public zayavkalar — faqat platform admin uchun, tenant emas."""
        self._admin_only(request)
        status_filter = request.query_params.get("status", "")
        queryset = Lead.objects.all()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return Response(LeadSerializer(queryset[:200], many=True).data)

    # --- Mijoz ochish (faqat administrator) ---

    @action(detail=False, methods=["post"], url_path="organizations/create")
    def create_organization(self, request: Request) -> Response:
        """
        `POST /platform/organizations/create` — yangi bog'cha ochadi.

        Ochiq `/auth/signup` ning o'rnini bosadi. Faqat administrator:
        har bir yangi tenant — bu yangi obuna, yangi hisob-kitob va
        o'chirilmaydigan ma'lumot; qo'llab-quvvatlash xodimi buni
        yaratmasligi kerak.
        """
        self._admin_only(request)
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        created = services.create_organization(
            actor=self._actor(request),
            organization_name=data["organization_name"],
            contact_email=data["contact_email"],
            full_name=data["full_name"],
            password=data["password"],
            contact_phone=data.get("contact_phone", ""),
            branch_name=data.get("branch_name", ""),
            slug=data.get("slug", ""),
            request=request._request,
        )
        return Response(created, status=status.HTTP_201_CREATED)

    # --- Tijorat amallari (faqat administrator) ---

    @action(
        detail=False,
        methods=["post"],
        url_path=r"organizations/(?P<organization_id>[0-9a-f-]{36})/suspend",
    )
    def suspend(self, request: Request, organization_id: str = "") -> Response:
        self._admin_only(request)
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = services.suspend_organization(
            actor=self._actor(request),
            organization_id=organization_id,
            reason=serializer.validated_data["reason"],
            request=request._request,
        )
        return Response({"status": subscription.status})

    @action(
        detail=False,
        methods=["post"],
        url_path=r"organizations/(?P<organization_id>[0-9a-f-]{36})/reactivate",
    )
    def reactivate(self, request: Request, organization_id: str = "") -> Response:
        self._admin_only(request)
        subscription = services.reactivate_organization(
            actor=self._actor(request), organization_id=organization_id, request=request._request
        )
        return Response({"status": subscription.status})

    @action(
        detail=False,
        methods=["post"],
        url_path=r"organizations/(?P<organization_id>[0-9a-f-]{36})/extend-trial",
    )
    def extend_trial(self, request: Request, organization_id: str = "") -> Response:
        self._admin_only(request)
        serializer = ExtendTrialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = services.extend_trial(
            actor=self._actor(request),
            organization_id=organization_id,
            days=serializer.validated_data["days"],
            reason=serializer.validated_data["reason"],
            request=request._request,
        )
        return Response({"trial_ends_at": subscription.trial_ends_at})

    # --- Ruxsatlar ---

    @action(
        detail=False,
        methods=["post"],
        url_path=r"organizations/(?P<organization_id>[0-9a-f-]{36})/support-grant",
    )
    def support_grant(self, request: Request, organization_id: str = "") -> Response:
        """
        Vaqt bilan cheklangan operatsion kirish so'raydi.

        Bu ruxsat **alohida kod yo'li ochmaydi**: xodim shundan keyin
        ham oddiy mijoz API'si orqali ishlaydi. Ya'ni audit qilinadigan
        yagona yo'l bor va u allaqachon sinalgan (docs/04 §19).
        """
        serializer = SupportGrantRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        grant = services.create_support_grant(
            actor=self._actor(request),
            organization_id=organization_id,
            reason=serializer.validated_data["reason"],
            hours=serializer.validated_data["hours"],
            request=request._request,
        )
        return Response(SupportGrantSerializer(grant).data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path=r"organizations/(?P<organization_id>[0-9a-f-]{36})/support-session",
    )
    def support_session(self, request: Request, organization_id: str = "") -> Response:
        """
        Amaldagi ruxsat bilan mijoz ilovasiga kirish tokenini oladi.

        Ruxsat berish (`support-grant`) va kirish (`support-session`)
        ATAYLAB ikkita amal: sabab bir marta yoziladi, kirish esa
        ruxsat muddati ichida bir necha marta bo'lishi mumkin — va har
        bir kirish alohida qayd etiladi.
        """
        session = services.start_support_session(
            actor=self._actor(request),
            organization_id=organization_id,
            request=request._request,
        )
        return Response(session)

    @action(detail=False, methods=["get"], url_path="support-grants")
    def support_grants(self, request: Request) -> Response:
        with platform_context():
            grants = SupportGrant.objects.select_related("organization", "platform_user").order_by(
                "-created_at"
            )[:50]
            return Response(SupportGrantSerializer(grants, many=True).data)

    # --- Hisob-kitob ---

    @action(detail=False, methods=["get"])
    def invoices(self, request: Request) -> Response:
        with platform_context():
            queryset = SubscriptionInvoice.all_objects.select_related("organization").order_by(
                "-issued_at"
            )
            invoice_status = request.query_params.get("status")
            if invoice_status:
                queryset = queryset.filter(status=invoice_status)
            return Response(
                [
                    {
                        "id": str(invoice.id),
                        "number": invoice.number,
                        "organization": invoice.organization.name,
                        "organization_id": str(invoice.organization_id),
                        "status": invoice.status,
                        "issued_at": invoice.issued_at.isoformat(),
                        "due_at": invoice.due_at.isoformat(),
                        "total_amount": f"{invoice.total_amount:.2f}",
                    }
                    for invoice in queryset[:200]
                ]
            )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"invoices/(?P<invoice_id>[0-9a-f-]{36})/payments",
    )
    def record_payment(self, request: Request, invoice_id: str = "") -> Response:
        """
        Kelgan bank o'tkazmasini yozadi.

        MVP'da to'lovlar bank orqali keladi va ularni platforma xodimi
        qo'lda kiritadi. Bir necha o'nlab mijozda bu avtomatlashtirishdan
        arzonroq va aniqroq (docs/06 §2).
        """
        self._admin_only(request)
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.subscriptions.services import record_subscription_payment

        with platform_context():
            invoice = SubscriptionInvoice.all_objects.filter(pk=invoice_id).first()
        if invoice is None:
            raise BusinessRuleViolation("Hisob topilmadi.")

        with organization_context(invoice.organization_id):
            payment = record_subscription_payment(
                invoice=invoice,
                amount=serializer.validated_data["amount"],
                method=serializer.validated_data["method"],
                reference=serializer.validated_data.get("reference", ""),
            )
            services.record_platform_action(
                actor=self._actor(request),
                action="create",
                organization=invoice.organization,
                entity_type="subscription_payment",
                entity_id=payment.id,
                changes={"amount": str(payment.amount), "invoice": invoice.number},
                request=request._request,
            )
        return Response({"id": str(payment.id), "amount": f"{payment.amount:.2f}"}, status=201)

    # --- Planlar ---

    @action(detail=False, methods=["get"])
    def plans(self, request: Request) -> Response:
        plans = SubscriptionPlan.objects.all().order_by("code", "-valid_from")
        return Response(
            [
                {
                    "id": str(plan.id),
                    "code": plan.code,
                    "name": plan.name,
                    "base_price": f"{plan.base_price:.2f}",
                    "included_children": plan.included_children,
                    "overage_step_children": plan.overage_step_children,
                    "overage_step_price": f"{plan.overage_step_price:.2f}",
                    "valid_from": plan.valid_from.isoformat(),
                    "valid_to": plan.valid_to.isoformat() if plan.valid_to else None,
                }
                for plan in plans
            ]
        )
