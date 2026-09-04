from django.urls import path

from .views import customer_report, daily_report, dashboard, monthly_report

urlpatterns = [
    path("dashboard/", dashboard),
    path("daily/", daily_report),
    path("monthly/", monthly_report),
    path("customers/", customer_report),
]
