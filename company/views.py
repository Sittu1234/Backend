from datetime import datetime
from io import StringIO

from django.core.management import call_command
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from activity.utils import log_activity
from .models import CareerOpening, CompanyEvent, CompanySettings, PublicPage
from .serializers import (
    CareerOpeningSerializer,
    CompanyEventSerializer,
    CompanySettingsSerializer,
    PublicCompanySerializer,
    PublicPageSerializer,
)
from company.terms import PI_KIND_LABELS, PI_KINDS, terms_text_for_kind


class CompanySettingsView(APIView):
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        obj = CompanySettings.get_solo()
        return Response(CompanySettingsSerializer(obj, context={"request": request}).data)

    def put(self, request):
        if not request.user.is_admin:
            return Response({"detail": "Only admin can update company settings."}, status=403)
        obj = CompanySettings.get_solo()
        serializer = CompanySettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_activity(request.user, "update", "CompanySettings", obj.id, "Updated company settings")
        return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def public_profile(request):
    company = CompanySettings.get_solo()
    page = PublicPage.get_solo()
    jobs = CareerOpening.objects.filter(is_active=True)
    data = dict(PublicCompanySerializer(company).data)
    data["page"] = PublicPageSerializer(page).data
    data["careers"] = CareerOpeningSerializer(jobs, many=True).data
    return Response(data)


class PublicPageView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        obj = PublicPage.get_solo()
        return Response(PublicPageSerializer(obj).data)

    def put(self, request):
        obj = PublicPage.get_solo()
        serializer = PublicPageSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_activity(request.user, "update", "PublicPage", obj.id, "Updated public page")
        return Response(serializer.data)


class CareerOpeningViewSet(viewsets.ModelViewSet):
    serializer_class = CareerOpeningSerializer
    pagination_class = None
    search_fields = ["title", "department", "location", "description"]
    ordering_fields = ["sort_order", "created_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = CareerOpening.objects.all()
        user = self.request.user
        is_admin = bool(user and user.is_authenticated and getattr(user, "is_admin", False))
        if not is_admin:
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        obj = serializer.save()
        log_activity(self.request.user, "create", "CareerOpening", obj.id, f"Added job {obj.title}")

    def perform_update(self, serializer):
        obj = serializer.save()
        log_activity(self.request.user, "update", "CareerOpening", obj.id, f"Updated job {obj.title}")

    def perform_destroy(self, instance):
        log_activity(
            self.request.user, "delete", "CareerOpening", instance.id, f"Deleted job {instance.title}"
        )
        instance.delete()


class CompanyEventViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyEventSerializer
    pagination_class = None
    filterset_fields = ["kind", "is_public", "is_active"]
    search_fields = ["title", "description"]
    ordering_fields = ["date", "created_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdmin()]

    def get_queryset(self):
        qs = CompanyEvent.objects.all()
        user = self.request.user
        is_admin = bool(user and user.is_authenticated and getattr(user, "is_admin", False))
        if not is_admin:
            qs = qs.filter(is_active=True, is_public=True)
        kind = self.request.query_params.get("kind")
        if kind:
            qs = qs.filter(kind=kind)
        upcoming = self.request.query_params.get("upcoming")
        if upcoming in ("1", "true", "yes"):
            qs = qs.filter(date__gte=timezone.localdate())
        return qs

    def perform_create(self, serializer):
        obj = serializer.save()
        log_activity(self.request.user, "create", "CompanyEvent", obj.id, f"Added {obj.title}")

    def perform_update(self, serializer):
        obj = serializer.save()
        log_activity(self.request.user, "update", "CompanyEvent", obj.id, f"Updated {obj.title}")

    def perform_destroy(self, instance):
        log_activity(self.request.user, "delete", "CompanyEvent", instance.id, f"Deleted {instance.title}")
        instance.delete()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pi_terms(request):
    kind = (request.query_params.get("kind") or "").strip().lower()
    templates = {value: terms_text_for_kind(value) for value, _label in PI_KINDS}
    if kind:
        if kind not in templates:
            return Response({"detail": "kind must be battery, ev_scooter or both."}, status=400)
        return Response(
            {
                "kind": kind,
                "label": PI_KIND_LABELS.get(kind, kind),
                "terms": templates[kind],
            }
        )
    return Response(
        {
            "kinds": [
                {"value": value, "label": label, "pdf_label": PI_KIND_LABELS[value]}
                for value, label in PI_KINDS
            ],
            "templates": templates,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdmin])
def backup_database(request):
    buf = StringIO()
    call_command("dumpdata", "--natural-foreign", "--natural-primary", stdout=buf)
    filename = f"spars-backup-{datetime.now().strftime('%Y%m%d-%H%M')}.json"
    log_activity(request.user, "backup", "Database", None, "Downloaded database backup")
    response = HttpResponse(buf.getvalue(), content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
