from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import CanManageInvoices
from activity.utils import log_activity
from company.models import CompanySettings
from core.scoping import invoice_queryset
from core.utils import amount_in_words
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import ProformaInvoice
from .pdf import build_pi_pdf
from .serializers import ProformaInvoiceSerializer
from .services import convert_pi_to_tax_invoice


def _render_template(tpl: str, invoice) -> str:
    company = CompanySettings.get_solo()
    ctx = {
        "customer_name": invoice.customer.customer_name,
        "company_name": company.company_name,
        "pi_number": invoice.pi_number,
        "pi_date": invoice.pi_date.strftime("%d-%m-%Y"),
        "valid_till": invoice.valid_till.strftime("%d-%m-%Y") if invoice.valid_till else "-",
        "grand_total": f"{invoice.grand_total:,.2f}",
        "amount_words": amount_in_words(invoice.grand_total),
    }
    try:
        return tpl.format(**ctx)
    except (KeyError, ValueError):
        return tpl


class ProformaInvoiceViewSet(viewsets.ModelViewSet):
    queryset = ProformaInvoice.objects.select_related("customer", "created_by").prefetch_related(
        "items__product", "dispatches__sent_by"
    )
    serializer_class = ProformaInvoiceSerializer
    permission_classes = [CanManageInvoices]
    search_fields = ["pi_number", "tax_invoice_number", "customer__customer_name", "customer__company_name", "customer__mobile"]
    filterset_fields = ["status", "customer", "pi_date", "created_by"]
    ordering_fields = ["pi_date", "grand_total", "pi_number", "created_at"]

    def get_queryset(self):
        return invoice_queryset(
            ProformaInvoice.objects.select_related("customer", "created_by").prefetch_related(
                "items__product", "dispatches__sent_by"
            ),
            self.request.user,
        )

    def perform_create(self, serializer):
        customer = serializer.validated_data.get("customer")
        user = self.request.user
        if user.is_sales and customer:
            if customer.assigned_to_id != user.id and customer.created_by_id != user.id:
                raise ValidationError({"customer": "You can only create PI for your own dealers."})
        invoice = serializer.save(created_by=user)
        log_activity(user, "create", "ProformaInvoice", invoice.id, f"Created {invoice.pi_number}")

    def perform_update(self, serializer):
        user = self.request.user
        instance = serializer.instance
        if user.is_sales and instance.created_by_id not in (None, user.id) and instance.customer.assigned_to_id != user.id:
            raise PermissionDenied("You can only update your own PIs.")
        invoice = serializer.save()
        log_activity(user, "update", "ProformaInvoice", invoice.id, f"Updated {invoice.pi_number}")

    def perform_destroy(self, instance):
        if not self.request.user.is_admin:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only admin can delete invoices.")
        log_activity(self.request.user, "delete", "ProformaInvoice", instance.id, f"Deleted {instance.pi_number}")
        instance.delete()

    @action(detail=False, methods=["get"])
    def next_number(self, request):
        company = CompanySettings.get_solo()
        return Response({"pi_number": ProformaInvoice.next_pi_number(company.pi_prefix or "PI")})

    @action(detail=False, methods=["get"])
    def next_tax_number(self, request):
        return Response({"tax_invoice_number": ProformaInvoice.next_tax_invoice_number()})

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        invoice = self.get_object()
        as_tax = request.query_params.get("kind") == "tax"
        if as_tax:
            if not invoice.tax_invoice_number:
                return Response({"detail": "Convert this PI to tax invoice first."}, status=400)
            data = build_pi_pdf(invoice, as_tax_invoice=True)
            filename = f"{invoice.tax_invoice_number}.pdf"
        else:
            data = build_pi_pdf(invoice)
            filename = f"{invoice.pi_number}.pdf"
        response = HttpResponse(data, content_type="application/pdf")
        disposition = "inline" if request.query_params.get("inline") else "attachment"
        response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        return response

    @action(detail=True, methods=["post"])
    def convert_tax(self, request, pk=None):
        invoice = self.get_object()
        user = request.user
        if not (user.is_admin or user.is_sales):
            raise PermissionDenied("Only admin or sales can convert to tax invoice.")
        if user.is_sales and invoice.created_by_id not in (None, user.id) and invoice.customer.assigned_to_id != user.id:
            raise PermissionDenied("You can only convert your own PIs.")
        number = (request.data.get("tax_invoice_number") or "").strip()
        raw_date = request.data.get("tax_invoice_date")
        invoice_date = None
        if raw_date:
            from datetime import datetime

            try:
                invoice_date = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d").date()
            except ValueError:
                return Response({"detail": "Invalid tax invoice date."}, status=400)
        try:
            invoice = convert_pi_to_tax_invoice(invoice, number=number or None, invoice_date=invoice_date)
        except Exception as exc:
            from django.core.exceptions import ValidationError as DjangoValidationError

            if isinstance(exc, DjangoValidationError):
                msg = " ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
                return Response({"detail": msg}, status=400)
            raise
        log_activity(
            request.user,
            "update",
            "ProformaInvoice",
            invoice.id,
            f"Converted {invoice.pi_number} to tax invoice {invoice.tax_invoice_number}",
        )
        return Response(ProformaInvoiceSerializer(invoice, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def email(self, request, pk=None):
        invoice = self.get_object()
        company = CompanySettings.get_solo()
        to_email = request.data.get("to") or invoice.customer.email
        if not to_email:
            return Response({"detail": "Customer has no email address."}, status=400)
        body = request.data.get("message") or _render_template(company.email_template, invoice)
        subject = request.data.get("subject") or f"Proforma Invoice {invoice.pi_number} – {company.company_name}"
        mail = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        mail.attach(f"{invoice.pi_number}.pdf", build_pi_pdf(invoice), "application/pdf")
        mail.send(fail_silently=False)
        invoice.record_dispatch("email", to_email, sent_by=request.user)
        log_activity(request.user, "email", "ProformaInvoice", invoice.id, f"Emailed {invoice.pi_number} to {to_email}")
        return Response({"detail": f"Email sent to {to_email}."})

    @action(detail=True, methods=["get"])
    def whatsapp(self, request, pk=None):
        invoice = self.get_object()
        company = CompanySettings.get_solo()
        mobile = "".join(ch for ch in (invoice.customer.mobile or "") if ch.isdigit())
        if mobile and not mobile.startswith("91") and len(mobile) == 10:
            mobile = "91" + mobile
        text = _render_template(company.whatsapp_template, invoice)
        link = f"{settings.FRONTEND_URL}/invoices/{invoice.id}"
        pdf_url = f"{request.build_absolute_uri(f'/api/invoices/{invoice.id}/pdf/')}?inline=1"
        full = f"{text}\n\nView: {link}\nPDF: {pdf_url}"
        wa = f"https://wa.me/{mobile}?text={quote(full)}" if mobile else f"https://wa.me/?text={quote(full)}"
        invoice.record_dispatch("whatsapp", mobile or "", sent_by=request.user)
        return Response(
            {
                "url": wa,
                "mobile": mobile,
                "message": full,
                "pdf_url": pdf_url,
                "share_link": link,
            }
        )
