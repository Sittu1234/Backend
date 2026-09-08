from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompanyEventViewSet, CompanySettingsView, backup_database, pi_terms, public_profile

router = DefaultRouter()
router.register("events", CompanyEventViewSet, basename="company-events")

urlpatterns = [
    path("settings/", CompanySettingsView.as_view()),
    path("public/", public_profile),
    path("pi-terms/", pi_terms),
    path("backup/", backup_database),
    path("", include(router.urls)),
]
