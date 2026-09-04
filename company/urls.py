from django.urls import path

from .views import CompanySettingsView, backup_database, pi_terms

urlpatterns = [
    path("settings/", CompanySettingsView.as_view()),
    path("pi-terms/", pi_terms),
    path("backup/", backup_database),
]
