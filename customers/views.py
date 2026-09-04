from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import CanManageCustomers
from activity.utils import log_activity
from core.scoping import dealer_queryset
from rest_framework.exceptions import PermissionDenied
from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.select_related("created_by", "assigned_to")
    serializer_class = CustomerSerializer
    permission_classes = [CanManageCustomers]
    search_fields = [
        "customer_name",
        "company_name",
        "gst_no",
        "mobile",
        "email",
        "city",
        "contact_person",
    ]
    filterset_fields = ["state", "city", "is_active", "party_type", "assigned_to", "created_by"]
    ordering_fields = ["customer_name", "created_at", "company_name"]

    def get_queryset(self):
        return dealer_queryset(
            Customer.objects.select_related("created_by", "assigned_to"),
            self.request.user,
        )

    def perform_create(self, serializer):
        extra = {"created_by": self.request.user}
        if self.request.user.is_sales:
            extra["assigned_to"] = self.request.user
            extra["party_type"] = Customer.PartyType.DEALER
        customer = serializer.save(**extra)
        log_activity(
            self.request.user, "create", "Customer", customer.id, f"Created {customer}"
        )

    def perform_update(self, serializer):
        if self.request.user.is_sales:
            customer = serializer.save(
                assigned_to=serializer.instance.assigned_to or self.request.user,
                party_type=Customer.PartyType.DEALER,
            )
        else:
            customer = serializer.save()
        log_activity(
            self.request.user, "update", "Customer", customer.id, f"Updated {customer}"
        )

    def perform_destroy(self, instance):
        if not self.request.user.is_admin:
            raise PermissionDenied("Only admin can delete dealers or vendors.")
        log_activity(
            self.request.user, "delete", "Customer", instance.id, f"Deleted {instance}"
        )
        instance.delete()

    @action(detail=False, methods=["get"])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        wb = Workbook()
        ws = wb.active
        ws.title = "Parties"
        headers = [
            "Type",
            "Name",
            "Company",
            "GST",
            "Contact Person",
            "Mobile",
            "Alternate",
            "Email",
            "Billing Address",
            "Shipping Address",
            "State",
            "City",
            "Pincode",
            "Sales Executive",
            "Created By",
        ]
        ws.append(headers)
        for c in qs:
            ws.append(
                [
                    c.party_type,
                    c.customer_name,
                    c.company_name,
                    c.gst_no,
                    c.contact_person,
                    c.mobile,
                    c.alternate_number,
                    c.email,
                    c.billing_address,
                    c.shipping_address,
                    c.state,
                    c.city,
                    c.pincode,
                    c.assigned_to.name if c.assigned_to else "",
                    c.created_by.name if c.created_by else "",
                ]
            )
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        response = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="parties.xlsx"'
        return response

    @action(detail=False, methods=["get"])
    def lookup(self, request):
        qs = self.get_queryset().filter(is_active=True)
        party_type = request.query_params.get("party_type", "dealer")
        if party_type:
            qs = qs.filter(party_type=party_type)
        assigned = request.query_params.get("assigned_to")
        if assigned:
            qs = qs.filter(assigned_to_id=assigned)
        qs = qs.order_by("customer_name")
        data = [
            {
                "id": c.id,
                "customer_name": c.customer_name,
                "company_name": c.company_name,
                "party_type": c.party_type,
                "gst_no": c.gst_no,
                "mobile": c.mobile,
                "email": c.email,
                "billing_address": c.billing_address,
                "shipping_address": c.shipping_address,
                "state": c.state,
                "city": c.city,
                "pincode": c.pincode,
                "contact_person": c.contact_person,
                "assigned_to": c.assigned_to_id,
                "assigned_to_name": c.assigned_to.name if c.assigned_to else "",
            }
            for c in qs
        ]
        return Response(data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.get_queryset().filter(is_active=True)
        dealers = qs.filter(party_type=Customer.PartyType.DEALER)
        vendors = qs.filter(party_type=Customer.PartyType.VENDOR)
        return Response(
            {
                "dealers": dealers.count(),
                "vendors": vendors.count(),
            }
        )
