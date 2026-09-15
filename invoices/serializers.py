from decimal import Decimal

from rest_framework import serializers

from customers.serializers import CustomerSerializer
from products.models import Product
from .models import InvoiceDispatch, InvoiceItem, ProformaInvoice


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = (
            "id",
            "product",
            "product_name",
            "remark",
            "hsn_code",
            "unit",
            "qty",
            "rate",
            "gst",
            "amount",
            "gst_amount",
            "total_amount",
        )
        read_only_fields = ("id", "amount", "gst_amount", "total_amount")


class InvoiceDispatchSerializer(serializers.ModelSerializer):
    sent_by_name = serializers.CharField(source="sent_by.name", read_only=True)

    class Meta:
        model = InvoiceDispatch
        fields = ("id", "channel", "recipient", "sent_by", "sent_by_name", "sent_at", "notes")


class InvoiceItemWriteSerializer(serializers.Serializer):
    product = serializers.IntegerField(required=False, allow_null=True)
    product_name = serializers.CharField(required=False, allow_blank=True)
    remark = serializers.CharField(required=False, allow_blank=True)
    hsn_code = serializers.CharField(required=False, allow_blank=True)
    unit = serializers.CharField(required=False, allow_blank=True)
    qty = serializers.DecimalField(max_digits=12, decimal_places=3)
    rate = serializers.DecimalField(max_digits=12, decimal_places=2)
    gst = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class ProformaInvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    customer_detail = CustomerSerializer(source="customer", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    created_by_employee_id = serializers.CharField(source="created_by.employee_id", read_only=True)
    dispatches = InvoiceDispatchSerializer(many=True, read_only=True)
    items_data = InvoiceItemWriteSerializer(many=True, write_only=True, required=False)
    can_convert_tax = serializers.SerializerMethodField()
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = ProformaInvoice
        fields = (
            "id",
            "pi_number",
            "pi_date",
            "valid_till",
            "customer",
            "customer_detail",
            "status",
            "freight_charges",
            "packing_charges",
            "discount",
            "notes",
            "terms",
            "pi_kind",
            "subtotal",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "gst_amount",
            "grand_total",
            "is_interstate",
            "created_by",
            "created_by_name",
            "created_by_employee_id",
            "created_at",
            "updated_at",
            "last_sent_at",
            "last_sent_via",
            "last_sent_to",
            "tax_invoice_number",
            "tax_invoice_date",
            "advance_received",
            "balance_due",
            "converted_at",
            "dispatches",
            "items",
            "items_data",
            "can_convert_tax",
        )
        read_only_fields = (
            "id",
            "pi_number",
            "subtotal",
            "cgst_amount",
            "sgst_amount",
            "igst_amount",
            "gst_amount",
            "grand_total",
            "is_interstate",
            "created_by",
            "created_at",
            "updated_at",
            "last_sent_at",
            "last_sent_via",
            "last_sent_to",
            "converted_at",
            "balance_due",
        )

    def validate_advance_received(self, value):
        if value is None:
            return Decimal("0")
        if value < 0:
            raise serializers.ValidationError("Advance cannot be negative.")
        if self.instance and value > Decimal(self.instance.grand_total or 0):
            raise serializers.ValidationError("Advance cannot be more than the invoice amount.")
        return value

    def validate_tax_invoice_number(self, value):
        value = (value or "").strip()
        if not value:
            return None
        qs = ProformaInvoice.objects.filter(tax_invoice_number__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This tax invoice number is already used.")
        return value

    def get_can_convert_tax(self, obj):
        return obj.can_convert_to_tax()

    def _upsert_items(self, invoice, items_data):
        invoice.items.all().delete()
        for row in items_data:
            product = None
            pid = row.get("product")
            if pid:
                product = Product.objects.filter(pk=pid).first()
            InvoiceItem.objects.create(
                invoice=invoice,
                product=product,
                product_name=row.get("product_name")
                or (product.product_name if product else "Item"),
                remark=(row.get("remark") or "").strip(),
                hsn_code=row.get("hsn_code") or (product.hsn_code if product else ""),
                unit=row.get("unit") or (product.unit if product else "PCS"),
                qty=row.get("qty") or Decimal("0"),
                rate=row.get("rate") or Decimal("0"),
                gst=row.get("gst") if row.get("gst") is not None else (product.gst if product else 18),
            )

    def create(self, validated_data):
        items_data = validated_data.pop("items_data", [])
        from company.models import CompanySettings

        company = CompanySettings.get_solo()
        invoice = ProformaInvoice.objects.create(
            pi_number=ProformaInvoice.next_pi_number(company.pi_prefix or "PI"),
            **validated_data,
        )
        if not invoice.terms:
            from company.terms import terms_text_for_kind

            invoice.terms = terms_text_for_kind(invoice.pi_kind or "battery")
            invoice.save(update_fields=["terms"])
        self._upsert_items(invoice, items_data)
        invoice.recalculate()
        return invoice

    def update(self, instance, validated_data):
        from django.utils import timezone

        items_data = validated_data.pop("items_data", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if instance.tax_invoice_number:
            if not instance.tax_invoice_date:
                instance.tax_invoice_date = timezone.now().date()
            if not instance.converted_at:
                instance.converted_at = timezone.now()
            if instance.status not in (instance.Status.CANCELLED, instance.Status.EXPIRED):
                instance.status = instance.Status.INVOICED
        instance.save()
        if items_data is not None:
            self._upsert_items(instance, items_data)
        instance.recalculate()
        return instance
