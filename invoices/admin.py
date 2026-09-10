from django.contrib import admin

from .models import InvoiceDispatch, InvoiceItem, ProformaInvoice


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


@admin.register(ProformaInvoice)
class ProformaInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "pi_number",
        "tax_invoice_number",
        "customer",
        "pi_date",
        "grand_total",
        "advance_received",
        "status",
        "created_by",
        "last_sent_at",
    )
    inlines = [InvoiceItemInline]


@admin.register(InvoiceDispatch)
class InvoiceDispatchAdmin(admin.ModelAdmin):
    list_display = ("invoice", "channel", "recipient", "sent_by", "sent_at")
