from rest_framework import serializers

from .models import (
    Department,
    DocFolder,
    DocumentVersion,
    EmployeeDocument,
    EmployeeProfile,
    GoodsReceipt,
    GoodsReceiptItem,
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
from .services import draft_email, draft_whatsapp, followup_suggestion, score_lead


class LeadNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)

    class Meta:
        model = LeadNote
        fields = ("id", "body", "author", "author_name", "created_at")
        read_only_fields = ("id", "author", "created_at")


class LeadFollowUpSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = LeadFollowUp
        fields = ("id", "due_at", "notes", "is_done", "created_by", "created_by_name", "created_at")
        read_only_fields = ("id", "created_by", "created_at")


class LeadSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    converted_dealer_name = serializers.CharField(source="converted_dealer.customer_name", read_only=True)
    call_notes = LeadNoteSerializer(many=True, read_only=True)
    followups = LeadFollowUpSerializer(many=True, read_only=True)
    followup_suggestion = serializers.SerializerMethodField()
    email_draft = serializers.SerializerMethodField()
    whatsapp_draft = serializers.SerializerMethodField()
    whatsapp_url = serializers.SerializerMethodField()
    mailto = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = "__all__"
        read_only_fields = ("id", "lead_number", "priority_score", "created_by", "created_at", "updated_at")

    def get_followup_suggestion(self, obj):
        return followup_suggestion(obj)

    def get_email_draft(self, obj):
        return draft_email(obj)

    def get_whatsapp_draft(self, obj):
        return draft_whatsapp(obj)

    def get_whatsapp_url(self, obj):
        mobile = "".join(ch for ch in (obj.mobile or "") if ch.isdigit())
        if mobile and len(mobile) == 10:
            mobile = "91" + mobile
        if not mobile:
            return ""
        from urllib.parse import quote

        return f"https://wa.me/{mobile}?text={quote(draft_whatsapp(obj))}"

    def get_mailto(self, obj):
        if not obj.email:
            return ""
        from urllib.parse import quote

        return f"mailto:{obj.email}?subject={quote('Kalpna Traders')}&body={quote(draft_email(obj))}"

    def create(self, validated_data):
        lead = super().create(validated_data)
        lead.priority_score = score_lead(lead)
        lead.save(update_fields=["priority_score"])
        return lead

    def update(self, instance, validated_data):
        lead = super().update(instance, validated_data)
        lead.priority_score = score_lead(lead)
        lead.save(update_fields=["priority_score"])
        return lead


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class StockBalanceSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    warehouse_code = serializers.CharField(source="warehouse.code", read_only=True)
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    product_code = serializers.CharField(source="product.product_code", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    min_stock = serializers.DecimalField(source="product.min_stock", max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = StockBalance
        fields = "__all__"


class StockMovementSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    to_warehouse_name = serializers.CharField(source="to_warehouse.name", read_only=True)
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = StockMovement
        fields = "__all__"
        read_only_fields = ("id", "movement_number", "created_by", "created_at", "updated_at")


class SerialNumberSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    dealer_name = serializers.CharField(source="dealer.customer_name", read_only=True)

    class Meta:
        model = SerialNumber
        fields = "__all__"


class ProductBatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)

    class Meta:
        model = ProductBatch
        fields = "__all__"


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = ("id", "product", "product_name", "qty", "rate", "gst", "received_qty")
        extra_kwargs = {"received_qty": {"read_only": True}}


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    vendor_name = serializers.CharField(source="vendor.customer_name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.name", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = (
            "id",
            "po_number",
            "subtotal",
            "gst_amount",
            "grand_total",
            "approved_by",
            "approved_at",
            "created_by",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        po = PurchaseOrder.objects.create(**validated_data)
        for item in items:
            PurchaseOrderItem.objects.create(purchase_order=po, **item)
        po.recalculate()
        po.save(update_fields=["subtotal", "gst_amount", "grand_total"])
        return po

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        if items is not None:
            instance.items.all().delete()
            for item in items:
                PurchaseOrderItem.objects.create(purchase_order=instance, **item)
            instance.recalculate()
            instance.save(update_fields=["subtotal", "gst_amount", "grand_total"])
        return instance


class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)

    class Meta:
        model = GoodsReceiptItem
        fields = ("id", "product", "product_name", "qty", "serials_text")


class GoodsReceiptSerializer(serializers.ModelSerializer):
    items = GoodsReceiptItemSerializer(many=True)
    po_number = serializers.CharField(source="purchase_order.po_number", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    received_by_name = serializers.CharField(source="received_by.name", read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = "__all__"
        read_only_fields = ("id", "grn_number", "received_by", "created_at", "updated_at")

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        grn = GoodsReceipt.objects.create(**validated_data)
        for item in items:
            GoodsReceiptItem.objects.create(grn=grn, **item)
        return grn


class PurchaseBillSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.customer_name", read_only=True)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseBill
        fields = "__all__"


class VendorPaymentSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.customer_name", read_only=True)

    class Meta:
        model = VendorPayment
        fields = "__all__"
        read_only_fields = ("id", "payment_number", "created_by", "created_at", "updated_at")


class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.customer_name", read_only=True)
    invoice_number = serializers.SerializerMethodField()
    received_by_name = serializers.CharField(source="received_by.name", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ("id", "receipt_number", "received_by", "created_at", "updated_at")

    def get_invoice_number(self, obj):
        if not obj.invoice:
            return ""
        return obj.invoice.tax_invoice_number or obj.invoice.pi_number


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocument
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class EmployeeProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    employee_id = serializers.CharField(source="user.employee_id", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = "__all__"


class LeaveBalanceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = "__all__"


class LeaveRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    employee_id = serializers.CharField(source="user.employee_id", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = (
            "id",
            "request_number",
            "user",
            "status",
            "manager_reviewed_by",
            "admin_reviewed_by",
            "created_at",
            "updated_at",
        )


class SalaryStructureSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = SalaryStructure
        fields = "__all__"


class PayslipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    employee_id = serializers.CharField(source="user.employee_id", read_only=True)

    class Meta:
        model = Payslip
        fields = "__all__"


class PayrollRunSerializer(serializers.ModelSerializer):
    payslips = PayslipSerializer(many=True, read_only=True)
    processed_by_name = serializers.CharField(source="processed_by.name", read_only=True)

    class Meta:
        model = PayrollRun
        fields = "__all__"
        read_only_fields = ("id", "status", "processed_by", "processed_at", "created_at", "updated_at")


class WarrantyRegistrationSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    dealer_name = serializers.CharField(source="dealer.customer_name", read_only=True)

    class Meta:
        model = WarrantyRegistration
        fields = "__all__"


class WarrantyClaimSerializer(serializers.ModelSerializer):
    serial = serializers.CharField(source="registration.serial", read_only=True)
    dealer_name = serializers.CharField(source="registration.dealer.customer_name", read_only=True)
    product_name = serializers.CharField(source="registration.product.product_name", read_only=True)
    customer_name = serializers.CharField(source="registration.customer_name", read_only=True)

    class Meta:
        model = WarrantyClaim
        fields = "__all__"
        read_only_fields = ("id", "claim_number", "created_by", "created_at", "updated_at")


class TicketUpdateSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)

    class Meta:
        model = TicketUpdate
        fields = ("id", "body", "status", "author", "author_name", "created_at")
        read_only_fields = ("id", "author", "created_at")


class ServiceTicketSerializer(serializers.ModelSerializer):
    dealer_name = serializers.CharField(source="dealer.customer_name", read_only=True)
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    technician_name = serializers.CharField(source="technician.name", read_only=True)
    updates = TicketUpdateSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceTicket
        fields = "__all__"
        read_only_fields = ("id", "ticket_number", "created_by", "created_at", "updated_at")


class TaskCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)

    class Meta:
        model = TaskComment
        fields = ("id", "body", "author", "author_name", "created_at")
        read_only_fields = ("id", "author", "created_at")


class WorkTaskSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.name", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.name", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    comments = TaskCommentSerializer(many=True, read_only=True)

    class Meta:
        model = WorkTask
        fields = "__all__"
        read_only_fields = ("id", "task_number", "assigned_by", "created_at", "updated_at")


class DocFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocFolder
        fields = "__all__"


class DocumentVersionSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.name", read_only=True)

    class Meta:
        model = DocumentVersion
        fields = "__all__"


class ManagedDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.name", read_only=True)
    folder_name = serializers.CharField(source="folder.name", read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ManagedDocument
        fields = "__all__"
        read_only_fields = ("id", "version", "uploaded_by", "created_at", "updated_at")

    def get_file_url(self, obj):
        if not obj.file:
            return ""
        url = obj.file.url
        request = self.context.get("request")
        if request and not url.startswith("http"):
            return request.build_absolute_uri(url)
        return url


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")


class DealerPortalHomeSerializer(serializers.Serializer):
    dealer = CustomerSerializer()
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)
    invoice_count = serializers.IntegerField()
    open_tickets = serializers.IntegerField()
    warranty_claims = serializers.IntegerField()
