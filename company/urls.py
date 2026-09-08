from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CareerOpeningViewSet,
    CompanyEventViewSet,
    CompanySettingsView,
    PublicPageView,
    backup_database,
    pi_terms,
    public_profile,
)

router = DefaultRouter()
router.register("events", CompanyEventViewSet, basename="company-events")
router.register("careers", CareerOpeningViewSet, basename="company-careers")

urlpatterns = [
    path("settings/", CompanySettingsView.as_view()),
    path("public/", public_profile),
    path("public-page/", PublicPageView.as_view()),
    path("pi-terms/", pi_terms),
    path("backup/", backup_database),
    path("", include(router.urls)),
]
