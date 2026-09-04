from io import BytesIO
import os

from django.http import FileResponse, HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import CanManageProducts, IsAdmin
from activity.utils import log_activity
from .models import CatalogPdf, Category, Product
from .serializers import CatalogPdfSerializer, CategorySerializer, ProductSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [CanManageProducts]
    search_fields = ["name"]
    pagination_class = None

    def perform_create(self, serializer):
        obj = serializer.save()
        log_activity(self.request.user, "create", "Category", obj.id, f"Created category {obj.name}")


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category")
    serializer_class = ProductSerializer
    permission_classes = [CanManageProducts]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ["product_name", "product_code", "hsn_code", "description"]
    filterset_fields = ["category", "is_active", "unit"]
    ordering_fields = ["product_name", "price", "created_at"]

    def perform_create(self, serializer):
        obj = serializer.save()
        log_activity(self.request.user, "create", "Product", obj.id, f"Created {obj}")

    def perform_update(self, serializer):
        obj = serializer.save()
        log_activity(self.request.user, "update", "Product", obj.id, f"Updated {obj}")

    def perform_destroy(self, instance):
        log_activity(self.request.user, "delete", "Product", instance.id, f"Deleted {instance}")
        instance.delete()

    @action(detail=False, methods=["get"])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        wb = Workbook()
        ws = wb.active
        ws.title = "Products"
        ws.append(["Name", "Code", "Category", "HSN", "Unit", "GST %", "Price", "Description"])
        for p in qs:
            ws.append(
                [
                    p.product_name,
                    p.product_code,
                    p.category.name if p.category else "",
                    p.hsn_code,
                    p.unit,
                    float(p.gst),
                    float(p.price),
                    p.description,
                ]
            )
        buf = BytesIO()
        wb.save(buf)
        response = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="products.xlsx"'
        return response

    @action(detail=False, methods=["get"])
    def price_list(self, request):
        today = timezone.localdate()
        wanted = ["EV Scooter", "Lithium Battery", "LED Battery"]
        groups = []
        for name in wanted:
            cat = Category.objects.filter(name=name).first()
            if not cat:
                continue
            items = Product.objects.filter(category=cat, is_active=True).order_by("price")
            groups.append(
                {
                    "category": cat.name,
                    "description": cat.description,
                    "items": ProductSerializer(items, many=True, context={"request": request}).data,
                }
            )
        return Response(
            {
                "date": today.isoformat(),
                "title": "Price List",
                "note": "Prices are exclusive of GST. Confirm stock before dispatch.",
                "groups": groups,
            }
        )


class CatalogPdfViewSet(viewsets.ModelViewSet):
    queryset = CatalogPdf.objects.select_related("uploaded_by")
    serializer_class = CatalogPdfSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pagination_class = None
    search_fields = ["title", "category"]

    def get_queryset(self):
        qs = CatalogPdf.objects.select_related("uploaded_by")
        if not self.request.user.is_admin:
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        obj = serializer.save(uploaded_by=self.request.user)
        log_activity(self.request.user, "create", "CatalogPdf", obj.id, f"Uploaded catalog PDF {obj.title}")

    def perform_destroy(self, instance):
        log_activity(self.request.user, "delete", "CatalogPdf", instance.id, f"Deleted catalog PDF {instance.title}")
        instance.file.delete(save=False)
        instance.delete()

    @action(detail=True, methods=["get"])
    def view(self, request, pk=None):
        obj = self.get_object()
        handle = obj.file.open("rb")
        return FileResponse(handle, content_type="application/pdf", filename=os.path.basename(obj.file.name) or "catalog.pdf")
