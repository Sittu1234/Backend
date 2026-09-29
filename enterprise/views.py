from io import BytesIO
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from accounts.permissions import (
    CanManageInventory,
    CanManageLeads,
    CanManagePayments,
    CanManagePurchases,
    CanManageService,
    CanManageWarranty,
    IsAdmin,
    IsDealer,
    IsHrOrAdmin,
    IsInternalUser,
    IsPayrollUser,
)
from activity.utils import log_activity
from core.scoping import dealer_queryset, invoice_queryset
from customers.models import Customer
from invoices.models import ProformaInvoice
from invoices.pdf import build_pi_pdf
from products.models import CatalogPdf, Product
from products.serializers import CatalogPdfSerializer, ProductSerializer

from .models import (
    Department,
    DocFolder,
    DocumentVersion,
    EmployeeDocument,
    EmployeeProfile,
    GoodsReceipt,
    Lead,
    LeadFollowUp,
    LeadNote,
    LeaveBalance,
    LeaveRequest,
    ManagedDocument,
    Notification,
    Payment,
    PayrollRun,
    Payslip,
    ProductBatch,
    PurchaseBill,
    PurchaseOrder,
    PurchaseOrderItem,
    SalaryStructure,
    SerialNumber,
    ServiceTicket,
    StockBalance,
    StockMovement,
    TaskComment,
    TicketUpdate,
    VendorPayment,
    Warehouse,
    WarrantyClaim,
    WarrantyRegistration,
    WorkTask,
)
from .notify import notify
from .pdfs import build_payslip_pdf, build_receipt_pdf
from .serializers import (
    DepartmentSerializer,
    DocFolderSerializer,
    EmployeeDocumentSerializer,
    EmployeeProfileSerializer,
    GoodsReceiptSerializer,
    LeadFollowUpSerializer,
    LeadNoteSerializer,
    LeadSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    ManagedDocumentSerializer,
    NotificationSerializer,
    PaymentSerializer,
    PayrollRunSerializer,
    PayslipSerializer,
    ProductBatchSerializer,
    PurchaseBillSerializer,
    PurchaseOrderSerializer,
    SalaryStructureSerializer,
    SerialNumberSerializer,
    ServiceTicketSerializer,
    StockBalanceSerializer,
    StockMovementSerializer,
    TaskCommentSerializer,
    TicketUpdateSerializer,
    VendorPaymentSerializer,
    WarehouseSerializer,
    WarrantyClaimSerializer,
    WarrantyRegistrationSerializer,
    WorkTaskSerializer,
)
from .services import apply_stock_move, draft_email, draft_whatsapp, followup_suggestion, process_payroll_run, score_lead


def _excel(filename, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(list(row))
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    res = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    res["Content-Disposition"] = f'attachment; filename="{filename}"'
    return res


def _lead_qs(user):
    qs = Lead.objects.select_related("assigned_to", "created_by", "converted_dealer").prefetch_related("call_notes", "followups")
    if user.is_admin or user.is_manager:
        return qs
    if user.is_sales:
        return qs.filter(Q(assigned_to=user) | Q(created_by=user))
    return qs


class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    permission_classes = [CanManageLeads]
    search_fields = ["lead_number", "company_name", "contact_person", "mobile", "email", "city"]
    filterset_fields = ["status", "source", "assigned_to", "state", "city"]
    ordering_fields = ["created_at", "priority_score", "next_follow_up", "company_name"]

    def get_queryset(self):
        return _lead_qs(self.request.user)

    def perform_create(self, serializer):
        extra = {"created_by": self.request.user}
        if self.request.user.is_sales and not serializer.validated_data.get("assigned_to"):
            extra["assigned_to"] = self.request.user
        lead = serializer.save(**extra)
        log_activity(self.request.user, "create", "Lead", lead.id, f"Created {lead.lead_number}")
        if lead.assigned_to:
            notify(lead.assigned_to, "lead", f"New lead {lead.lead_number}", lead.company_name, link="/crm")

    def perform_update(self, serializer):
        lead = serializer.save()
        log_activity(self.request.user, "update", "Lead", lead.id, f"Updated {lead.lead_number}")

    @action(detail=True, methods=["post"])
    def notes(self, request, pk=None):
        lead = self.get_object()
        ser = LeadNoteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(lead=lead, author=request.user)
        return Response(LeadSerializer(lead).data)

    @action(detail=True, methods=["post"])
    def followups(self, request, pk=None):
        lead = self.get_object()
        ser = LeadFollowUpSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        fu = ser.save(lead=lead, created_by=request.user)
        lead.next_follow_up = fu.due_at
        lead.status = Lead.Status.FOLLOW_UP if lead.status == Lead.Status.NEW else lead.status
        lead.priority_score = score_lead(lead)
        lead.save(update_fields=["next_follow_up", "status", "priority_score"])
        if lead.assigned_to:
            notify(lead.assigned_to, "follow_up", f"Follow-up {lead.lead_number}", str(fu.due_at), link="/crm")
        return Response(LeadSerializer(lead).data)

    @action(detail=True, methods=["post"])
    def convert_dealer(self, request, pk=None):
        lead = self.get_object()
        if lead.converted_dealer_id:
            raise ValidationError("Lead already converted.")
        dealer = Customer.objects.create(
            customer_name=lead.contact_person,
            company_name=lead.company_name,
            party_type=Customer.PartyType.DEALER,
            mobile=lead.mobile,
            email=lead.email,
            state=lead.state or "Uttar Pradesh",
            city=lead.city or "-",
            pincode=request.data.get("pincode") or "000000",
            billing_address=request.data.get("billing_address") or f"{lead.city}, {lead.state}",
            contact_person=lead.contact_person,
            assigned_to=lead.assigned_to,
            created_by=request.user,
            notes=f"Converted from {lead.lead_number}",
        )
        lead.converted_dealer = dealer
        lead.status = Lead.Status.WON
        lead.priority_score = score_lead(lead)
        lead.save(update_fields=["converted_dealer", "status", "priority_score"])
        log_activity(request.user, "convert", "Lead", lead.id, f"{lead.lead_number} → dealer {dealer.id}")
        return Response({"lead": LeadSerializer(lead).data, "dealer_id": dealer.id})

    @action(detail=False, methods=["get"])
    def pipeline(self, request):
        qs = self.filter_queryset(self.get_queryset())
        data = []
        for value, label in Lead.Status.choices:
            bucket = qs.filter(status=value)
            data.append({"status": value, "label": label, "count": bucket.count()})
        due = qs.filter(next_follow_up__date__lte=timezone.localdate(), status__in=["new", "contacted", "follow_up", "interested", "negotiation"])
        return Response({"pipeline": data, "followups_due": due.count(), "hot": qs.filter(priority_score__gte=70).count()})

    @action(detail=False, methods=["get"])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return _excel(
            "leads.xlsx",
            ["Lead", "Company", "Contact", "Mobile", "Source", "Status", "Score", "Assigned"],
            [
                (l.lead_number, l.company_name, l.contact_person, l.mobile, l.source, l.status, l.priority_score, l.assigned_to.name if l.assigned_to else "")
                for l in qs
            ],
        )


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [CanManageInventory]
    search_fields = ["name", "code", "city"]
    pagination_class = None


class StockBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockBalance.objects.select_related("warehouse", "product")
    serializer_class = StockBalanceSerializer
    permission_classes = [CanManageInventory]
    search_fields = ["product__product_name", "product__product_code", "product__sku"]
    filterset_fields = ["warehouse", "product"]

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        qs = self.get_queryset()
        total_skus = qs.values("product").distinct().count()
        total_qty = qs.aggregate(t=Sum("qty"))["t"] or 0
        low = []
        out = []
        for row in qs.select_related("product", "warehouse"):
            if row.qty <= 0:
                out.append(StockBalanceSerializer(row).data)
            elif row.qty <= Decimal(row.product.min_stock or 0):
                low.append(StockBalanceSerializer(row).data)
        fast = (
            StockMovement.objects.filter(kind=StockMovement.Kind.OUT)
            .values("product_id", "product__product_name", "product__product_code")
            .annotate(moved=Sum("qty"))
            .order_by("-moved")[:8]
        )
        slow = (
            StockBalance.objects.values("product_id", "product__product_name", "product__product_code")
            .annotate(qty=Sum("qty"), moved=Count("product__movements"))
            .order_by("moved", "-qty")[:8]
        )
        return Response(
            {
                "total_skus": total_skus,
                "total_qty": total_qty,
                "low_stock": low[:20],
                "out_of_stock": out[:20],
                "fast_moving": list(fast),
                "slow_moving": list(slow),
            }
        )

    @action(detail=False, methods=["get"])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return _excel(
            "stock.xlsx",
            ["Warehouse", "SKU", "Product", "Qty", "Min"],
            [(b.warehouse.code, b.product.product_code, b.product.product_name, b.qty, b.product.min_stock) for b in qs],
        )


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("warehouse", "to_warehouse", "product", "created_by")
    serializer_class = StockMovementSerializer
    permission_classes = [CanManageInventory]
    filterset_fields = ["kind", "warehouse", "product"]
    search_fields = ["movement_number", "reference", "product__product_code"]

    @action(detail=False, methods=["post"])
    def move(self, request):
        kind = request.data.get("kind")
        try:
            warehouse = Warehouse.objects.get(pk=request.data.get("warehouse"))
            product = Product.objects.get(pk=request.data.get("product"))
        except (Warehouse.DoesNotExist, Product.DoesNotExist, TypeError, ValueError):
            raise ValidationError("Warehouse and product are required.")
        to_wh = None
        if request.data.get("to_warehouse"):
            to_wh = Warehouse.objects.filter(pk=request.data.get("to_warehouse")).first()
        serials = request.data.get("serials") or []
        if isinstance(serials, str):
            serials = [s.strip() for s in serials.replace(",", "\n").splitlines() if s.strip()]
        mv = apply_stock_move(
            kind=kind,
            warehouse=warehouse,
            product=product,
            qty=request.data.get("qty") or 0,
            user=request.user,
            to_warehouse=to_wh,
            reference=request.data.get("reference") or "",
            notes=request.data.get("notes") or "",
            serials=serials,
            batch_no=request.data.get("batch_no") or "",
            mfg_date=request.data.get("mfg_date") or None,
            expiry_date=request.data.get("expiry_date") or None,
        )
        log_activity(request.user, "stock", "StockMovement", mv.id, f"{mv.kind} {mv.qty}")
        return Response(StockMovementSerializer(mv).data, status=201)


class SerialNumberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SerialNumber.objects.select_related("product", "warehouse", "dealer")
    serializer_class = SerialNumberSerializer
    permission_classes = [CanManageInventory]
    search_fields = ["serial", "product__product_code"]
    filterset_fields = ["status", "warehouse", "product"]


class ProductBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductBatch.objects.select_related("product", "warehouse")
    serializer_class = ProductBatchSerializer
    permission_classes = [CanManageInventory]
    search_fields = ["batch_no", "product__product_code"]
    filterset_fields = ["warehouse", "product"]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related("vendor", "created_by", "approved_by").prefetch_related("items__product")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [CanManagePurchases]
    search_fields = ["po_number", "vendor__customer_name", "vendor__company_name"]
    filterset_fields = ["status", "vendor"]

    def perform_create(self, serializer):
        po = serializer.save(created_by=self.request.user)
        log_activity(self.request.user, "create", "PurchaseOrder", po.id, po.po_number)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        po = self.get_object()
        if po.status != PurchaseOrder.Status.DRAFT:
            raise ValidationError("Only draft POs can be sent.")
        po.status = PurchaseOrder.Status.SENT
        po.save(update_fields=["status"])
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not (request.user.is_admin or request.user.is_accountant):
            raise PermissionDenied("Only Admin or Accounts can approve purchase orders.")
        po = self.get_object()
        if po.status not in (PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.SENT):
            raise ValidationError("This PO cannot be approved.")
        po.status = PurchaseOrder.Status.APPROVED
        po.approved_by = request.user
        po.approved_at = timezone.now()
        po.save(update_fields=["status", "approved_by", "approved_at"])
        log_activity(request.user, "approve", "PurchaseOrder", po.id, po.po_number)
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=False, methods=["get"])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return _excel(
            "purchase_orders.xlsx",
            ["PO", "Vendor", "Status", "Date", "Total"],
            [(p.po_number, p.vendor.customer_name, p.status, str(p.po_date), p.grand_total) for p in qs],
        )


class GoodsReceiptViewSet(viewsets.ModelViewSet):
    queryset = GoodsReceipt.objects.select_related("purchase_order", "warehouse", "received_by").prefetch_related("items")
    serializer_class = GoodsReceiptSerializer
    permission_classes = [CanManagePurchases]
    search_fields = ["grn_number", "purchase_order__po_number"]
    http_method_names = ["get", "post", "head", "options"]

    def perform_create(self, serializer):
        grn = serializer.save(received_by=self.request.user)
        po = grn.purchase_order
        if po.status not in (PurchaseOrder.Status.APPROVED, PurchaseOrder.Status.RECEIVED):
            raise ValidationError("GRN is allowed only on approved purchase orders.")
        for item in grn.items.all():
            serials = [s.strip() for s in (item.serials_text or "").replace(",", "\n").splitlines() if s.strip()]
            apply_stock_move(
                kind=StockMovement.Kind.IN,
                warehouse=grn.warehouse,
                product=item.product,
                qty=item.qty,
                user=self.request.user,
                reference=grn.grn_number,
                serials=serials,
            )
            poi = po.items.filter(product=item.product).first()
            if poi:
                poi.received_qty = F("received_qty") + item.qty
                poi.save(update_fields=["received_qty"])
        po.status = PurchaseOrder.Status.RECEIVED
        po.save(update_fields=["status"])
        log_activity(self.request.user, "create", "GoodsReceipt", grn.id, grn.grn_number)


class PurchaseBillViewSet(viewsets.ModelViewSet):
    queryset = PurchaseBill.objects.select_related("vendor", "purchase_order")
    serializer_class = PurchaseBillSerializer
    permission_classes = [CanManagePurchases]
    search_fields = ["bill_number", "vendor__customer_name"]
    filterset_fields = ["vendor"]


class VendorPaymentViewSet(viewsets.ModelViewSet):
    queryset = VendorPayment.objects.select_related("vendor", "bill")
    serializer_class = VendorPaymentSerializer
    permission_classes = [CanManagePurchases]
    search_fields = ["payment_number", "vendor__customer_name", "reference"]

    def perform_create(self, serializer):
        pay = serializer.save(created_by=self.request.user)
        if pay.bill_id:
            pay.bill.paid_amount = F("paid_amount") + pay.amount
            pay.bill.save(update_fields=["paid_amount"])


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [CanManagePayments]
    search_fields = ["receipt_number", "customer__customer_name", "reference"]
    filterset_fields = ["mode", "kind", "customer"]

    def get_queryset(self):
        qs = Payment.objects.select_related("customer", "invoice", "received_by")
        if self.request.user.is_sales:
            dealers = dealer_queryset(Customer.objects.all(), self.request.user)
            return qs.filter(customer__in=dealers)
        return qs

    def perform_create(self, serializer):
        pay = serializer.save(received_by=self.request.user)
        if pay.invoice_id:
            inv = pay.invoice
            inv.advance_received = Decimal(inv.advance_received or 0) + Decimal(pay.amount)
            inv.save(update_fields=["advance_received"])
        log_activity(self.request.user, "create", "Payment", pay.id, pay.receipt_number)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        inv = invoice_queryset(ProformaInvoice.objects.filter(status="invoiced"), request.user)
        due_rows = []
        overdue = 0
        pending = Decimal("0")
        today = timezone.localdate()
        for invoice in inv.select_related("customer"):
            due = invoice.balance_due
            if due <= 0:
                continue
            pending += due
            aged = (today - (invoice.tax_invoice_date or invoice.pi_date)).days
            if aged > 30:
                overdue += 1
            due_rows.append(
                {
                    "id": invoice.id,
                    "number": invoice.tax_invoice_number or invoice.pi_number,
                    "customer": invoice.customer.customer_name,
                    "due": due,
                    "days": aged,
                }
            )
        collected = self.get_queryset().aggregate(t=Sum("amount"))["t"] or 0
        return Response(
            {
                "collected": collected,
                "pending": pending,
                "overdue_count": overdue,
                "dues": due_rows[:50],
            }
        )

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        pay = self.get_object()
        data = build_receipt_pdf(pay)
        res = HttpResponse(data, content_type="application/pdf")
        res["Content-Disposition"] = f'inline; filename="{pay.receipt_number}.pdf"'
        return res

    @action(detail=False, methods=["get"])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())
        return _excel(
            "collections.xlsx",
            ["Receipt", "Customer", "Amount", "Mode", "Date"],
            [(p.receipt_number, p.customer.customer_name, p.amount, p.mode, str(p.received_on)) for p in qs],
        )


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsHrOrAdmin]
    pagination_class = None


class EmployeeProfileViewSet(viewsets.ModelViewSet):
    queryset = EmployeeProfile.objects.select_related("user", "department").prefetch_related("documents")
    serializer_class = EmployeeProfileSerializer
    permission_classes = [IsHrOrAdmin]
    search_fields = ["user__name", "user__employee_id", "designation", "aadhaar_number", "pan_number"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]


class EmployeeDocumentViewSet(viewsets.ModelViewSet):
    queryset = EmployeeDocument.objects.select_related("profile")
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [IsHrOrAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    queryset = LeaveBalance.objects.select_related("user")
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsInternalUser]
    filterset_fields = ["year", "user"]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.is_admin or u.is_hr:
            return qs
        return qs.filter(user=u)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsInternalUser]
    filterset_fields = ["status", "kind", "user"]

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("user")
        u = self.request.user
        if u.is_admin or u.is_hr:
            return qs
        if u.is_manager:
            return qs.filter(Q(user=u) | Q(user__manager=u))
        return qs.filter(user=u)

    def perform_create(self, serializer):
        req = serializer.save(user=self.request.user)
        targets = []
        if self.request.user.manager_id:
            targets.append(self.request.user.manager)
        targets += list(User.objects.filter(role__in=[User.Role.ADMIN, User.Role.HR], is_active=True))
        for t in {x.id: x for x in targets if x}.values():
            notify(t, "leave", f"Leave {req.request_number}", f"{req.user.name} {req.kind} {req.start_date}", link="/hr")

    @action(detail=True, methods=["post"])
    def manager_review(self, request, pk=None):
        req = self.get_object()
        if not (request.user.is_manager or request.user.is_admin or request.user.is_hr):
            raise PermissionDenied("Not allowed.")
        if request.data.get("approve"):
            req.status = LeaveRequest.Status.MANAGER_APPROVED
            req.manager_reviewed_by = request.user
        else:
            req.status = LeaveRequest.Status.REJECTED
            req.manager_reviewed_by = request.user
        req.review_note = request.data.get("note") or ""
        req.save()
        notify(req.user, "leave", f"Leave {req.status}", req.review_note, link="/hr")
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def admin_review(self, request, pk=None):
        req = self.get_object()
        if not (request.user.is_admin or request.user.is_hr):
            raise PermissionDenied("Only Admin / HR can give final approval.")
        if request.data.get("approve"):
            req.status = LeaveRequest.Status.APPROVED
            req.admin_reviewed_by = request.user
            year = req.start_date.year
            bal, _ = LeaveBalance.objects.get_or_create(user=req.user, year=year)
            field = {"casual": "casual", "sick": "sick", "earned": "earned"}[req.kind]
            setattr(bal, field, max(Decimal("0"), Decimal(getattr(bal, field)) - Decimal(req.days)))
            bal.save()
        else:
            req.status = LeaveRequest.Status.REJECTED
            req.admin_reviewed_by = request.user
        req.review_note = request.data.get("note") or ""
        req.save()
        notify(req.user, "leave", f"Leave {req.status}", req.review_note, link="/hr")
        return Response(LeaveRequestSerializer(req).data)


class SalaryStructureViewSet(viewsets.ModelViewSet):
    queryset = SalaryStructure.objects.select_related("user")
    serializer_class = SalaryStructureSerializer
    permission_classes = [IsPayrollUser]


class PayrollRunViewSet(viewsets.ModelViewSet):
    queryset = PayrollRun.objects.prefetch_related("payslips__user")
    serializer_class = PayrollRunSerializer
    permission_classes = [IsPayrollUser]
    http_method_names = ["get", "post", "head", "options"]

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        run = self.get_object()
        count = process_payroll_run(run, request.user, request.data.get("bonuses") or {})
        return Response({"processed": count, **PayrollRunSerializer(run).data})

    @action(detail=False, methods=["get"])
    def export(self, request):
        year = request.query_params.get("year")
        month = request.query_params.get("month")
        qs = Payslip.objects.select_related("user", "payroll_run")
        if year:
            qs = qs.filter(payroll_run__year=year)
        if month:
            qs = qs.filter(payroll_run__month=month)
        return _excel(
            "salary_report.xlsx",
            ["Emp", "Name", "Gross", "PF", "ESI", "TDS", "Net", "Month"],
            [
                (
                    p.user.employee_id,
                    p.user.name,
                    p.gross,
                    p.pf,
                    p.esi,
                    p.tds,
                    p.net,
                    f"{p.payroll_run.month}/{p.payroll_run.year}",
                )
                for p in qs
            ],
        )


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayslipSerializer
    permission_classes = [IsInternalUser]
    filterset_fields = ["payroll_run", "user"]

    def get_queryset(self):
        qs = Payslip.objects.select_related("user", "payroll_run")
        u = self.request.user
        if u.is_admin or u.is_hr or u.is_accountant:
            return qs
        return qs.filter(user=u)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        slip = self.get_object()
        data = build_payslip_pdf(slip)
        res = HttpResponse(data, content_type="application/pdf")
        res["Content-Disposition"] = f'inline; filename="payslip-{slip.user.employee_id}.pdf"'
        return res


class WarrantyRegistrationViewSet(viewsets.ModelViewSet):
    queryset = WarrantyRegistration.objects.select_related("product", "dealer")
    serializer_class = WarrantyRegistrationSerializer
    permission_classes = [CanManageWarranty]
    search_fields = ["serial", "customer_name", "customer_mobile", "dealer__customer_name"]
    filterset_fields = ["dealer", "product"]


class WarrantyClaimViewSet(viewsets.ModelViewSet):
    queryset = WarrantyClaim.objects.select_related("registration__dealer", "registration__product", "created_by")
    serializer_class = WarrantyClaimSerializer
    permission_classes = [CanManageWarranty]
    search_fields = ["claim_number", "registration__serial", "issue"]
    filterset_fields = ["status"]

    def perform_create(self, serializer):
        claim = serializer.save(created_by=self.request.user)
        for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
            notify(admin, "warranty", f"Claim {claim.claim_number}", claim.issue[:180], link="/warranty")

    @action(detail=True, methods=["post"])
    def set_status(self, request, pk=None):
        claim = self.get_object()
        status = request.data.get("status")
        if status not in dict(WarrantyClaim.Status.choices):
            raise ValidationError("Invalid status.")
        claim.status = status
        claim.resolution = request.data.get("resolution") or claim.resolution
        claim.save()
        return Response(WarrantyClaimSerializer(claim).data)


class ServiceTicketViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceTicketSerializer
    permission_classes = [CanManageService]
    search_fields = ["ticket_number", "customer_name", "customer_mobile", "serial", "complaint"]
    filterset_fields = ["status", "priority", "technician", "dealer"]

    def get_queryset(self):
        qs = ServiceTicket.objects.select_related("dealer", "product", "technician").prefetch_related("updates")
        if self.request.user.is_technician:
            return qs.filter(Q(technician=self.request.user) | Q(status="open"))
        return qs

    def perform_create(self, serializer):
        ticket = serializer.save(created_by=self.request.user)
        if ticket.technician:
            notify(ticket.technician, "service", f"Ticket {ticket.ticket_number}", ticket.complaint[:180], link="/service")

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        tech_id = request.data.get("technician")
        ticket.technician_id = tech_id
        ticket.status = ServiceTicket.Status.ASSIGNED
        ticket.save(update_fields=["technician_id", "status"])
        if ticket.technician:
            notify(ticket.technician, "service", f"Assigned {ticket.ticket_number}", ticket.complaint[:180], link="/service")
        return Response(ServiceTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def updates(self, request, pk=None):
        ticket = self.get_object()
        ser = TicketUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(ticket=ticket, author=request.user)
        if request.data.get("status"):
            ticket.status = request.data["status"]
            ticket.save(update_fields=["status"])
        return Response(ServiceTicketSerializer(ticket).data)


class WorkTaskViewSet(viewsets.ModelViewSet):
    serializer_class = WorkTaskSerializer
    permission_classes = [IsInternalUser]
    search_fields = ["task_number", "title"]
    filterset_fields = ["status", "priority", "assigned_to"]

    def get_queryset(self):
        qs = WorkTask.objects.select_related("assigned_to", "assigned_by").prefetch_related("comments")
        u = self.request.user
        if u.is_admin or u.is_manager:
            return qs
        return qs.filter(Q(assigned_to=u) | Q(assigned_by=u))

    def perform_create(self, serializer):
        if not (self.request.user.is_admin or self.request.user.is_manager):
            raise PermissionDenied("Only Admin / Manager can assign tasks.")
        task = serializer.save(assigned_by=self.request.user)
        notify(task.assigned_to, "task", f"Task {task.task_number}", task.title, link="/tasks")

    @action(detail=True, methods=["post"])
    def comments(self, request, pk=None):
        task = self.get_object()
        ser = TaskCommentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(task=task, author=request.user)
        return Response(WorkTaskSerializer(task).data)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        qs = WorkTask.objects.filter(assigned_to=request.user)
        today = timezone.localdate()
        return Response(
            {
                "pending": WorkTaskSerializer(qs.filter(status="pending"), many=True).data,
                "in_progress": WorkTaskSerializer(qs.filter(status="in_progress"), many=True).data,
                "completed": WorkTaskSerializer(qs.filter(status="completed"), many=True).data,
                "overdue": WorkTaskSerializer(qs.exclude(status="completed").filter(due_date__lt=today), many=True).data,
            }
        )


class DocFolderViewSet(viewsets.ModelViewSet):
    queryset = DocFolder.objects.all()
    serializer_class = DocFolderSerializer
    permission_classes = [IsInternalUser]
    filterset_fields = ["kind"]
    pagination_class = None


class ManagedDocumentViewSet(viewsets.ModelViewSet):
    queryset = ManagedDocument.objects.select_related("folder", "uploaded_by").prefetch_related("versions")
    serializer_class = ManagedDocumentSerializer
    permission_classes = [IsInternalUser]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    search_fields = ["title", "notes", "folder__name"]
    filterset_fields = ["folder", "folder__kind"]

    def perform_create(self, serializer):
        doc = serializer.save(uploaded_by=self.request.user, version=1)
        if doc.file:
            DocumentVersion.objects.create(document=doc, version=1, file=doc.file, uploaded_by=self.request.user)

    def perform_update(self, serializer):
        prev = serializer.instance
        new_file = serializer.validated_data.get("file")
        doc = serializer.save()
        if new_file:
            doc.version = prev.version + 1
            doc.save(update_fields=["version"])
            DocumentVersion.objects.create(document=doc, version=doc.version, file=doc.file, uploaded_by=self.request.user)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["kind", "is_read"]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response(NotificationSerializer(n).data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"ok": True})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        return Response({"count": self.get_queryset().filter(is_read=False).count()})


@api_view(["GET"])
@permission_classes([IsInternalUser])
def md_dashboard(request):
    if not request.user.is_admin:
        raise PermissionDenied("MD dashboard is for Admin.")
    today = timezone.localdate()
    month_start = today.replace(day=1)
    q_start = today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)
    inv = ProformaInvoice.objects.exclude(status="cancelled")
    tax = inv.filter(status="invoiced")
    today_sales = tax.filter(tax_invoice_date=today).aggregate(t=Sum("grand_total"))["t"] or 0
    monthly = tax.filter(tax_invoice_date__gte=month_start).aggregate(t=Sum("grand_total"))["t"] or 0
    quarterly = tax.filter(tax_invoice_date__gte=q_start).aggregate(t=Sum("grand_total"))["t"] or 0
    collected = Payment.objects.filter(received_on__gte=month_start).aggregate(t=Sum("amount"))["t"] or 0
    pending = Decimal("0")
    for row in tax:
        pending += row.balance_due
    dealers = Customer.objects.filter(party_type="dealer", is_active=True)
    new_dealers = dealers.filter(created_at__date__gte=month_start).count()
    from attendance.models import Attendance

    present = Attendance.objects.filter(date=today, status="present").count()
    stock_qty = StockBalance.objects.aggregate(t=Sum("qty"))["t"] or 0
    low = StockBalance.objects.filter(qty__lte=F("product__min_stock")).count()
    revenue = (
        tax.filter(tax_invoice_date__gte=today.replace(year=today.year - 1) if today.month == 12 else month_start.replace(month=1))
        .values("tax_invoice_date__month")
        .annotate(total=Sum("grand_total"))
        .order_by("tax_invoice_date__month")
    )
    products = (
        tax.values("items__product_name")
        .annotate(total=Sum("grand_total"), count=Count("id"))
        .order_by("-total")[:8]
    )
    return Response(
        {
            "today_sales": today_sales,
            "monthly_sales": monthly,
            "quarterly_sales": quarterly,
            "collection": collected,
            "pending_payments": pending,
            "active_dealers": dealers.count(),
            "new_dealers": new_dealers,
            "present_today": present,
            "current_stock": stock_qty,
            "low_stock": low,
            "open_leads": Lead.objects.exclude(status__in=["won", "lost"]).count(),
            "open_tickets": ServiceTicket.objects.exclude(status="closed").count(),
            "revenue_trend": list(revenue),
            "product_performance": list(products),
        }
    )


@api_view(["GET", "POST"])
@permission_classes([CanManageLeads])
def ai_assistant(request):
    if request.method == "GET":
        qs = _lead_qs(request.user).exclude(status__in=["won", "lost"])
        top = sorted(qs, key=lambda l: l.priority_score, reverse=True)[:12]
        insights = [
            f"{qs.filter(status='negotiation').count()} leads in negotiation — close with quotation + proposal.",
            f"{qs.filter(next_follow_up__date__lte=timezone.localdate()).count()} follow-ups due today or overdue.",
            f"Highest source this month: check IndiaMART and referral first.",
        ]
        return Response(
            {
                "top_leads": LeadSerializer(top, many=True).data,
                "insights": insights,
            }
        )
    lead_id = request.data.get("lead")
    lead = _lead_qs(request.user).filter(pk=lead_id).first()
    if not lead:
        raise ValidationError("Lead not found.")
    return Response(
        {
            "score": score_lead(lead),
            "suggestion": followup_suggestion(lead),
            "email_draft": draft_email(lead),
            "whatsapp_draft": draft_whatsapp(lead),
        }
    )


def _dealer_or_404(user):
    dealer = user.linked_dealer
    if not dealer:
        raise PermissionDenied("Dealer account is not linked.")
    return dealer


@api_view(["GET"])
@permission_classes([IsDealer])
def portal_home(request):
    dealer = _dealer_or_404(request.user)
    inv = ProformaInvoice.objects.filter(customer=dealer).exclude(status="cancelled")
    outstanding = Decimal("0")
    for row in inv.filter(status="invoiced"):
        outstanding += row.balance_due
    return Response(
        {
            "dealer": {
                "id": dealer.id,
                "name": dealer.customer_name,
                "company": dealer.company_name,
                "gst_no": dealer.gst_no,
                "mobile": dealer.mobile,
                "city": dealer.city,
            },
            "orders": inv.count(),
            "outstanding": outstanding,
            "open_tickets": ServiceTicket.objects.filter(dealer=dealer).exclude(status="closed").count(),
            "warranty_claims": WarrantyClaim.objects.filter(registration__dealer=dealer).exclude(status="completed").count(),
        }
    )


@api_view(["GET"])
@permission_classes([IsDealer])
def portal_products(request):
    qs = Product.objects.filter(is_active=True).select_related("category")
    return Response(ProductSerializer(qs, many=True, context={"request": request}).data)


@api_view(["GET"])
@permission_classes([IsDealer])
def portal_catalogs(request):
    qs = CatalogPdf.objects.filter(is_active=True)
    return Response(CatalogPdfSerializer(qs, many=True, context={"request": request}).data)


@api_view(["GET"])
@permission_classes([IsDealer])
def portal_invoice_pdf(request, pk):
    dealer = _dealer_or_404(request.user)
    invoice = ProformaInvoice.objects.filter(pk=pk, customer=dealer).first()
    if not invoice:
        raise PermissionDenied("Invoice not found.")
    data = build_pi_pdf(invoice, as_tax_invoice=bool(invoice.tax_invoice_number))
    filename = f"{invoice.tax_invoice_number or invoice.pi_number}.pdf"
    res = HttpResponse(data, content_type="application/pdf")
    res["Content-Disposition"] = f'inline; filename="{filename}"'
    return res


@api_view(["GET"])
@permission_classes([IsDealer])
def portal_invoices(request):
    dealer = _dealer_or_404(request.user)
    qs = ProformaInvoice.objects.filter(customer=dealer).order_by("-pi_date")
    data = [
        {
            "id": i.id,
            "pi_number": i.pi_number,
            "tax_invoice_number": i.tax_invoice_number,
            "pi_date": i.pi_date,
            "status": i.status,
            "grand_total": i.grand_total,
            "balance_due": i.balance_due,
        }
        for i in qs
    ]
    return Response(data)


@api_view(["POST"])
@permission_classes([IsDealer])
def portal_ticket(request):
    dealer = _dealer_or_404(request.user)
    ticket = ServiceTicket.objects.create(
        dealer=dealer,
        customer_name=dealer.customer_name,
        customer_mobile=dealer.mobile,
        complaint=request.data.get("complaint") or "",
        origin="dealer_portal",
        created_by=request.user,
        product_id=request.data.get("product") or None,
        serial=request.data.get("serial") or "",
    )
    return Response(ServiceTicketSerializer(ticket).data, status=201)


@api_view(["GET"])
@permission_classes([IsDealer])
def portal_tickets(request):
    dealer = _dealer_or_404(request.user)
    qs = ServiceTicket.objects.filter(dealer=dealer)
    return Response(ServiceTicketSerializer(qs, many=True).data)


@api_view(["POST"])
@permission_classes([IsDealer])
def portal_warranty_claim(request):
    dealer = _dealer_or_404(request.user)
    serial = request.data.get("serial")
    reg = WarrantyRegistration.objects.filter(serial=serial, dealer=dealer).first()
    if not reg:
        raise ValidationError("Serial not registered under your dealership.")
    claim = WarrantyClaim.objects.create(
        registration=reg,
        issue=request.data.get("issue") or "",
        created_by=request.user,
    )
    return Response(WarrantyClaimSerializer(claim).data, status=201)


@api_view(["GET"])
@permission_classes([IsDealer])
def portal_warranties(request):
    dealer = _dealer_or_404(request.user)
    regs = WarrantyRegistration.objects.filter(dealer=dealer)
    claims = WarrantyClaim.objects.filter(registration__dealer=dealer)
    return Response(
        {
            "registrations": WarrantyRegistrationSerializer(regs, many=True).data,
            "claims": WarrantyClaimSerializer(claims, many=True).data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAdmin])
def portal_invite(request):
    try:
        dealer = Customer.objects.get(pk=request.data.get("customer"), party_type=Customer.PartyType.DEALER)
    except Customer.DoesNotExist:
        raise ValidationError("Dealer not found.")
    email = (request.data.get("email") or dealer.email or "").strip().lower()
    password = request.data.get("password") or ""
    if not email or len(password) < 8:
        raise ValidationError("Email and password (min 8 chars) are required.")
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "name": dealer.company_name or dealer.customer_name,
            "role": User.Role.DEALER,
            "mobile": dealer.mobile,
            "linked_dealer": dealer,
        },
    )
    user.role = User.Role.DEALER
    user.linked_dealer = dealer
    user.set_password(password)
    user.is_active = True
    user.save()
    return Response({"id": user.id, "email": user.email, "created": created})
