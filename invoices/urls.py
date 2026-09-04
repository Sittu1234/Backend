from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProformaInvoiceViewSet

router = DefaultRouter()
router.register("", ProformaInvoiceViewSet, basename="invoices")

urlpatterns = [path("", include(router.urls))]
