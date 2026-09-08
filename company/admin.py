from django.contrib import admin

from .models import CareerOpening, CompanyEvent, CompanySettings, PublicPage


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ("company_name", "phone", "email", "gst_number")


@admin.register(CompanyEvent)
class CompanyEventAdmin(admin.ModelAdmin):
    list_display = ("date", "kind", "title", "is_public", "is_active")
    list_filter = ("kind", "is_public", "is_active")
    search_fields = ("title", "description")


@admin.register(PublicPage)
class PublicPageAdmin(admin.ModelAdmin):
    list_display = ("hero_title", "careers_email", "updated_at")


@admin.register(CareerOpening)
class CareerOpeningAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "location", "employment_type", "is_active", "sort_order")
    list_filter = ("is_active", "employment_type")
    search_fields = ("title", "department", "description")
