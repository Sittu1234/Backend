from django.contrib import admin

from .models import CompanyEvent, CompanySettings


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ("company_name", "phone", "email", "gst_number")


@admin.register(CompanyEvent)
class CompanyEventAdmin(admin.ModelAdmin):
    list_display = ("date", "kind", "title", "is_public", "is_active")
    list_filter = ("kind", "is_public", "is_active")
    search_fields = ("title", "description")
