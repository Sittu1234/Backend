from django.db import transaction

from invoices.models import ProformaInvoice


def generate_pi_number(prefix: str = "PI") -> str:
    with transaction.atomic():
        return ProformaInvoice.next_pi_number(prefix)
