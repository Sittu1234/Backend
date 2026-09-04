from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CatalogPdfViewSet, CategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="categories")
router.register("catalog-pdfs", CatalogPdfViewSet, basename="catalog-pdfs")
router.register("", ProductViewSet, basename="products")

urlpatterns = [path("", include(router.urls))]
