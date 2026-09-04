from django.contrib import admin

from .models import CatalogPdf, Category, Product

admin.site.register(Category)
admin.site.register(Product)


@admin.register(CatalogPdf)
class CatalogPdfAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "uploaded_by", "created_at", "is_active")
