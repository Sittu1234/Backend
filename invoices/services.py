from django.db import transaction

from invoices.models import ProformaInvoice


def generate_pi_number(prefix: str = "PI") -> str:
    with transaction.atomic():
        return ProformaInvoice.next_pi_number(prefix)


def convert_pi_to_tax_invoice(
    invoice: ProformaInvoice, number=None, invoice_date=None, advance_received=None
) -> ProformaInvoice:
    with transaction.atomic():
        inv = (
            ProformaInvoice.objects.select_for_update()
            .prefetch_related("items")
            .get(pk=invoice.pk)
        )
        ProformaInvoice.objects.select_for_update().filter(tax_invoice_number__isnull=False).exists()
        return inv.convert_to_tax_invoice(
            number=number, invoice_date=invoice_date, advance_received=advance_received
        )
