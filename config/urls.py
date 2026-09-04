from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(_request):
    return Response({"status": "ok", "app": "SPARS ERP"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/", include("accounts.urls")),
    path("api/customers/", include("customers.urls")),
    path("api/products/", include("products.urls")),
    path("api/invoices/", include("invoices.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/company/", include("company.urls")),
    path("api/activity/", include("activity.urls")),
    path("api/attendance/", include("attendance.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "SPARS ERP Administration"
admin.site.site_title = "SPARS ERP"
admin.site.index_title = "Proforma Invoice Management"
