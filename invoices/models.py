from decimal import Decimal

from django.db import models
from django.utils import timezone


class ProformaInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        INVOICED = "invoiced", "Tax Invoice"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    pi_number = models.CharField(max_length=30, unique=True, editable=False)
    pi_date = models.DateField(default=timezone.now)
    valid_till = models.DateField(null=True, blank=True)
    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="invoices"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    freight_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    packing_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    class PiKind(models.TextChoices):
        BATTERY = "battery", "Battery"
        EV_SCOOTER = "ev_scooter", "EV Scooter"
        BOTH = "both", "Both"

    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    pi_kind = models.CharField(
        max_length=20,
        choices=PiKind.choices,
        default=PiKind.BATTERY,
        blank=True,
    )

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cgst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    sgst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    igst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_interstate = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="invoices",
    )
    last_sent_at = models.DateTimeField(null=True, blank=True)
    last_sent_via = models.CharField(max_length=20, blank=True)
    last_sent_to = models.CharField(max_length=200, blank=True)
    tax_invoice_number = models.CharField(max_length=60, unique=True, null=True, blank=True)
    tax_invoice_date = models.DateField(null=True, blank=True)
    advance_received = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    converted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-pi_date", "-id"]

    def __str__(self):
        return self.pi_number

    @staticmethod
    def next_pi_number(prefix="PI"):
        year = timezone.now().year
        start = f"{prefix}-{year}-"
        last = (
            ProformaInvoice.objects.filter(pi_number__startswith=start)
            .order_by("-pi_number")
            .first()
        )
        seq = 1
        if last:
            try:
                seq = int(last.pi_number.split("-")[-1]) + 1
            except ValueError:
                seq = 1
        return f"{prefix}-{year}-{seq:04d}"

    @staticmethod
    def next_tax_invoice_number(prefix="INV", start_seq=4):
        """Tax invoices start at 0004 (001–003 reserved / PI series)."""
        year = timezone.now().year
        start = f"{prefix}-{year}-"
        last = (
            ProformaInvoice.objects.filter(tax_invoice_number__startswith=start)
            .order_by("-tax_invoice_number")
            .first()
        )
        seq = start_seq
        if last and last.tax_invoice_number:
            try:
                seq = max(start_seq, int(last.tax_invoice_number.split("-")[-1]) + 1)
            except ValueError:
                seq = start_seq
        return f"{prefix}-{year}-{seq:04d}"

    @property
    def is_tax_invoice(self):
        return bool(self.tax_invoice_number)

    @property
    def balance_due(self):
        remaining = Decimal(self.grand_total or 0) - Decimal(self.advance_received or 0)
        if remaining < 0:
            remaining = Decimal("0")
        return remaining.quantize(Decimal("0.01"))

    def apply_advance_received(self, amount):
        from django.core.exceptions import ValidationError

        value = Decimal(str(amount if amount is not None else 0)).quantize(Decimal("0.01"))
        if value < 0:
            raise ValidationError("Advance cannot be negative.")
        total = Decimal(self.grand_total or 0)
        if value > total:
            raise ValidationError("Advance cannot be more than the invoice amount.")
        self.advance_received = value
        return value

    def can_convert_to_tax(self):
        if self.tax_invoice_number:
            return False
        if self.status in (self.Status.CANCELLED, self.Status.EXPIRED):
            return False
        return len(self.items.all()) > 0

    def convert_to_tax_invoice(self, number=None, invoice_date=None, advance_received=None):
        from django.core.exceptions import ValidationError

        if self.status in (self.Status.CANCELLED, self.Status.EXPIRED) and not self.tax_invoice_number:
            raise ValidationError("Cancelled or expired PI cannot be converted.")
        if not self.tax_invoice_number and len(self.items.all()) == 0:
            raise ValidationError("Add products before converting to tax invoice.")
        custom = (number or "").strip()
        if custom:
            clash = (
                ProformaInvoice.objects.filter(tax_invoice_number__iexact=custom)
                .exclude(pk=self.pk)
                .exists()
            )
            if clash:
                raise ValidationError("This tax invoice number is already used.")
            self.tax_invoice_number = custom
        elif not self.tax_invoice_number:
            self.tax_invoice_number = self.next_tax_invoice_number()
        if invoice_date:
            self.tax_invoice_date = invoice_date
        elif not self.tax_invoice_date:
            self.tax_invoice_date = timezone.now().date()
        if advance_received is not None:
            self.apply_advance_received(advance_received)
        if not self.converted_at:
            self.converted_at = timezone.now()
        self.status = self.Status.INVOICED
        self.save(
            update_fields=[
                "tax_invoice_number",
                "tax_invoice_date",
                "advance_received",
                "converted_at",
                "status",
                "updated_at",
            ]
        )
        return self

    def recalculate(self):
        from company.models import CompanySettings

        company = CompanySettings.get_solo()
        company_state = (company.state or "").strip().lower()
        customer_state = (self.customer.state or "").strip().lower()
        self.is_interstate = bool(company_state and customer_state and company_state != customer_state)

        items = list(self.items.all())
        subtotal = sum((i.amount for i in items), Decimal("0"))
        gst_total = sum((i.gst_amount for i in items), Decimal("0"))
        extras = Decimal(self.freight_charges or 0) + Decimal(self.packing_charges or 0)
        percent = Decimal(self.discount_percent or 0)
        if percent < 0:
            percent = Decimal("0")
        if percent > 100:
            percent = Decimal("100")
        self.discount_percent = percent
        base = subtotal + extras
        discount = (base * percent / Decimal("100")).quantize(Decimal("0.01")) if percent else Decimal("0")
        self.discount = discount

        taxable = base - discount
        if taxable < 0:
            taxable = Decimal("0")

        extra_gst_rate = Decimal(company.default_gst or 0) / Decimal("100")
        extra_gst = (Decimal(extras) * extra_gst_rate).quantize(Decimal("0.01"))
        gst_total = (gst_total + extra_gst).quantize(Decimal("0.01"))
        if percent and base > 0:
            gst_total = (gst_total * (Decimal("100") - percent) / Decimal("100")).quantize(Decimal("0.01"))

        if self.is_interstate:
            self.igst_amount = gst_total
            self.cgst_amount = Decimal("0")
            self.sgst_amount = Decimal("0")
        else:
            half = (gst_total / 2).quantize(Decimal("0.01"))
            self.cgst_amount = half
            self.sgst_amount = gst_total - half
            self.igst_amount = Decimal("0")

        self.subtotal = subtotal.quantize(Decimal("0.01"))
        self.gst_amount = gst_total
        self.grand_total = (taxable + gst_total).quantize(Decimal("0.01"))
        self.save(
            update_fields=[
                "subtotal",
                "cgst_amount",
                "sgst_amount",
                "igst_amount",
                "gst_amount",
                "grand_total",
                "discount",
                "discount_percent",
                "is_interstate",
                "updated_at",
            ]
        )

    def record_dispatch(self, channel, recipient, sent_by=None, notes=""):
        dispatch = InvoiceDispatch.objects.create(
            invoice=self,
            channel=channel,
            recipient=recipient or "",
            sent_by=sent_by,
            notes=notes,
        )
        self.last_sent_at = dispatch.sent_at
        self.last_sent_via = channel
        self.last_sent_to = recipient or ""
        if self.status == self.Status.DRAFT:
            self.status = self.Status.SENT
        self.save(update_fields=["last_sent_at", "last_sent_via", "last_sent_to", "status", "updated_at"])
        return dispatch


class InvoiceDispatch(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"

    invoice = models.ForeignKey(
        ProformaInvoice, on_delete=models.CASCADE, related_name="dispatches"
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    recipient = models.CharField(max_length=200)
    sent_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="invoice_dispatches"
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.invoice.pi_number} {self.channel} {self.recipient}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        ProformaInvoice, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "products.Product", null=True, blank=True, on_delete=models.SET_NULL
    )
    product_name = models.CharField(max_length=200)
    remark = models.CharField(max_length=200, blank=True)
    hsn_code = models.CharField(max_length=8, blank=True)
    unit = models.CharField(max_length=10, default="PCS")
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    gst = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        qty = Decimal(self.qty or 0)
        rate = Decimal(self.rate or 0)
        gst = Decimal(self.gst or 0)
        self.amount = (qty * rate).quantize(Decimal("0.01"))
        self.gst_amount = (self.amount * gst / Decimal("100")).quantize(Decimal("0.01"))
        self.total_amount = (self.amount + self.gst_amount).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
