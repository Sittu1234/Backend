from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_name", "company_name", "party_type", "assigned_to", "mobile", "city", "is_active")
    list_filter = ("party_type", "is_active", "state")
    search_fields = ("customer_name", "company_name", "gst_no", "mobile")
