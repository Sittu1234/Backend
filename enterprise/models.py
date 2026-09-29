from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.numbering import next_code


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Lead(TimeStamped):
    class Source(models.TextChoices):
        WEBSITE = "website", "Website"
        INDIAMART = "indiamart", "IndiaMART"
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        LINKEDIN = "linkedin", "LinkedIn"
        JUSTDIAL = "justdial", "Justdial"
        REFERRAL = "referral", "Referral"
        DIRECT = "direct", "Direct Call"

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        FOLLOW_UP = "follow_up", "Follow Up"
        INTERESTED = "interested", "Interested"
        NEGOTIATION = "negotiation", "Negotiation"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    lead_number = models.CharField(max_length=30, unique=True, editable=False)
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150)
    mobile = models.CharField(max_length=15, db_index=True)
    email = models.EmailField(blank=True)
    state = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=80, blank=True)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.DIRECT, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads"
    )
    product_interest = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    next_follow_up = models.DateTimeField(null=True, blank=True, db_index=True)
    priority_score = models.PositiveSmallIntegerField(default=50)
    converted_dealer = models.ForeignKey(
        "customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="from_leads"
    )
    lost_reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="leads_created"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "assigned_to"]),
            models.Index(fields=["source", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.lead_number:
            self.lead_number = next_code(Lead, "lead_number", "LD")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.lead_number} {self.company_name}"


class LeadNote(TimeStamped):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="call_notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    body = models.TextField()

    class Meta:
        ordering = ["-created_at"]


class LeadFollowUp(TimeStamped):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="followups")
    due_at = models.DateTimeField(db_index=True)
    notes = models.CharField(max_length=255, blank=True)
    is_done = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["due_at"]


class Warehouse(TimeStamped):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} {self.name}"


class StockBalance(TimeStamped):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="balances")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="stock_balances")
    qty = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = ("warehouse", "product")
        indexes = [models.Index(fields=["product", "warehouse"])]

    def __str__(self):
        return f"{self.warehouse.code} {self.product.product_code} = {self.qty}"


class StockMovement(TimeStamped):
    class Kind(models.TextChoices):
        IN = "in", "Stock In"
        OUT = "out", "Stock Out"
        TRANSFER = "transfer", "Transfer"

    movement_number = models.CharField(max_length=30, unique=True, editable=False)
    kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="movements")
    to_warehouse = models.ForeignKey(
        Warehouse, null=True, blank=True, on_delete=models.PROTECT, related_name="incoming_transfers"
    )
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="movements")
    qty = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.movement_number:
            self.movement_number = next_code(StockMovement, "movement_number", "STK")
        super().save(*args, **kwargs)


class SerialNumber(TimeStamped):
    class Status(models.TextChoices):
        IN_STOCK = "in_stock", "In Stock"
        SOLD = "sold", "Sold"
        TRANSFERRED = "transferred", "Transferred"
        DEFECTIVE = "defective", "Defective"
        WARRANTY = "warranty", "In Warranty Claim"

    serial = models.CharField(max_length=80, unique=True, db_index=True)
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="serials")
    warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_STOCK, db_index=True)
    dealer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL)
    invoice = models.ForeignKey("invoices.ProformaInvoice", null=True, blank=True, on_delete=models.SET_NULL)
    batch = models.ForeignKey("ProductBatch", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]


class ProductBatch(TimeStamped):
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="batches")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="batches")
    batch_no = models.CharField(max_length=60, db_index=True)
    mfg_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    qty = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        unique_together = ("product", "warehouse", "batch_no")
        ordering = ["-created_at"]


class PurchaseOrder(TimeStamped):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        APPROVED = "approved", "Approved"
        RECEIVED = "received", "Received"
        CLOSED = "closed", "Closed"

    po_number = models.CharField(max_length=30, unique=True, editable=False)
    vendor = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="purchase_orders")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    po_date = models.DateField(default=timezone.localdate)
    expected_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="pos_approved"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="pos_created"
    )

    class Meta:
        ordering = ["-po_date", "-id"]

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = next_code(PurchaseOrder, "po_number", "PO")
        super().save(*args, **kwargs)

    def recalculate(self):
        sub = Decimal("0")
        gst = Decimal("0")
        for item in self.items.all():
            line = Decimal(item.qty) * Decimal(item.rate)
            sub += line
            gst += line * Decimal(item.gst or 0) / Decimal("100")
        self.subtotal = sub.quantize(Decimal("0.01"))
        self.gst_amount = gst.quantize(Decimal("0.01"))
        self.grand_total = (sub + gst).quantize(Decimal("0.01"))


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    gst = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    received_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)


class GoodsReceipt(TimeStamped):
    grn_number = models.CharField(max_length=30, unique=True, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="grns")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    received_date = models.DateField(default=timezone.localdate)
    notes = models.CharField(max_length=255, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-received_date", "-id"]

    def save(self, *args, **kwargs):
        if not self.grn_number:
            self.grn_number = next_code(GoodsReceipt, "grn_number", "GRN")
        super().save(*args, **kwargs)


class GoodsReceiptItem(models.Model):
    grn = models.ForeignKey(GoodsReceipt, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    serials_text = models.TextField(blank=True, help_text="Comma or newline separated serials")


class PurchaseBill(TimeStamped):
    bill_number = models.CharField(max_length=60)
    vendor = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="purchase_bills")
    purchase_order = models.ForeignKey(PurchaseOrder, null=True, blank=True, on_delete=models.SET_NULL)
    bill_date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-bill_date"]
        unique_together = ("vendor", "bill_number")

    @property
    def balance(self):
        return (Decimal(self.amount) + Decimal(self.gst_amount) - Decimal(self.paid_amount)).quantize(Decimal("0.01"))


class VendorPayment(TimeStamped):
    class Mode(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        BANK = "bank", "Bank Transfer"
        CHEQUE = "cheque", "Cheque"

    payment_number = models.CharField(max_length=30, unique=True, editable=False)
    vendor = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="vendor_payments")
    bill = models.ForeignKey(PurchaseBill, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.BANK)
    paid_on = models.DateField(default=timezone.localdate)
    reference = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = next_code(VendorPayment, "payment_number", "VP")
        super().save(*args, **kwargs)


class Payment(TimeStamped):
    class Mode(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        BANK = "bank", "Bank Transfer"
        CHEQUE = "cheque", "Cheque"

    class Kind(models.TextChoices):
        ADVANCE = "advance", "Advance"
        PARTIAL = "partial", "Partial"
        FULL = "full", "Full"

    receipt_number = models.CharField(max_length=30, unique=True, editable=False)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="payments")
    invoice = models.ForeignKey(
        "invoices.ProformaInvoice", null=True, blank=True, on_delete=models.SET_NULL, related_name="payments"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.UPI)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.PARTIAL)
    received_on = models.DateField(default=timezone.localdate, db_index=True)
    reference = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-received_on", "-id"]
        indexes = [models.Index(fields=["customer", "received_on"])]

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = next_code(Payment, "receipt_number", "RCT")
        super().save(*args, **kwargs)


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class EmployeeProfile(TimeStamped):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hr_profile")
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL)
    designation = models.CharField(max_length=120, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    aadhaar_number = models.CharField(max_length=12, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    bank_account = models.CharField(max_length=30, blank=True)
    bank_ifsc = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.user.name


class EmployeeDocument(TimeStamped):
    class Kind(models.TextChoices):
        AADHAAR = "aadhaar", "Aadhaar"
        PAN = "pan", "PAN"
        RESUME = "resume", "Resume"
        OFFER = "offer", "Offer Letter"
        EXPERIENCE = "experience", "Experience Letter"
        OTHER = "other", "Other"

    profile = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=120, blank=True)
    file = models.FileField(upload_to="hr_docs/")


class LeaveBalance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_balances")
    year = models.PositiveIntegerField()
    casual = models.DecimalField(max_digits=5, decimal_places=1, default=12)
    sick = models.DecimalField(max_digits=5, decimal_places=1, default=8)
    earned = models.DecimalField(max_digits=5, decimal_places=1, default=15)

    class Meta:
        unique_together = ("user", "year")


class LeaveRequest(TimeStamped):
    class Kind(models.TextChoices):
        CASUAL = "casual", "Casual Leave"
        SICK = "sick", "Sick Leave"
        EARNED = "earned", "Earned Leave"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        MANAGER_APPROVED = "manager_approved", "Manager Approved"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    request_number = models.CharField(max_length=30, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_requests")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1, default=1)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    manager_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="leave_mgr_reviews"
    )
    admin_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="leave_admin_reviews"
    )
    review_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = next_code(LeaveRequest, "request_number", "LV")
        super().save(*args, **kwargs)


class SalaryStructure(TimeStamped):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="salary_structure")
    basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    incentive = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pf_percent = models.DecimalField(max_digits=5, decimal_places=2, default=12)
    esi_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.75)
    tds_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)


class PayrollRun(TimeStamped):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PROCESSED = "processed", "Processed"

    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]


class Payslip(TimeStamped):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="payslips")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payslips")
    basic = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    incentive = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pf = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    esi = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tds = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ("payroll_run", "user")


class WarrantyRegistration(TimeStamped):
    serial = models.CharField(max_length=80, unique=True)
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    dealer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="warranties")
    customer_name = models.CharField(max_length=150)
    customer_mobile = models.CharField(max_length=15)
    purchase_date = models.DateField()
    warranty_start = models.DateField()
    warranty_end = models.DateField(db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["dealer", "warranty_end"])]


class WarrantyClaim(TimeStamped):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"

    claim_number = models.CharField(max_length=30, unique=True, editable=False)
    registration = models.ForeignKey(WarrantyRegistration, on_delete=models.PROTECT, related_name="claims")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    issue = models.TextField()
    resolution = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.claim_number:
            self.claim_number = next_code(WarrantyClaim, "claim_number", "WC")
        super().save(*args, **kwargs)


class ServiceTicket(TimeStamped):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        WAITING = "waiting", "Waiting Parts"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    ticket_number = models.CharField(max_length=30, unique=True, editable=False)
    dealer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL)
    customer_name = models.CharField(max_length=150)
    customer_mobile = models.CharField(max_length=15, blank=True)
    product = models.ForeignKey("products.Product", null=True, blank=True, on_delete=models.SET_NULL)
    serial = models.CharField(max_length=80, blank=True)
    complaint = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="service_tickets"
    )
    origin = models.CharField(max_length=20, default="internal")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets_created"
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = next_code(ServiceTicket, "ticket_number", "SRV")
        super().save(*args, **kwargs)


class TicketUpdate(TimeStamped):
    ticket = models.ForeignKey(ServiceTicket, on_delete=models.CASCADE, related_name="updates")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    body = models.TextField()
    status = models.CharField(max_length=20, blank=True)


class WorkTask(TimeStamped):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    task_number = models.CharField(max_length=30, unique=True, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assigned_tasks"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="created_tasks"
    )
    due_date = models.DateField(db_index=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    class Meta:
        ordering = ["due_date", "-priority"]
        indexes = [models.Index(fields=["assigned_to", "status"])]

    def save(self, *args, **kwargs):
        if not self.task_number:
            self.task_number = next_code(WorkTask, "task_number", "TSK")
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return self.status != self.Status.COMPLETED and self.due_date < timezone.localdate()


class TaskComment(TimeStamped):
    task = models.ForeignKey(WorkTask, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    body = models.TextField()


class DocFolder(TimeStamped):
    class Kind(models.TextChoices):
        COMPANY = "company", "Company Documents"
        EMPLOYEE = "employee", "Employee Documents"
        DEALER = "dealer", "Dealer Documents"
        VENDOR = "vendor", "Vendor Documents"

    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=Kind.choices, db_index=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")

    class Meta:
        unique_together = ("kind", "name", "parent")
        ordering = ["kind", "name"]


class ManagedDocument(TimeStamped):
    folder = models.ForeignKey(DocFolder, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=200, db_index=True)
    file = models.FileField(upload_to="dms/")
    version = models.PositiveIntegerField(default=1)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]


class DocumentVersion(TimeStamped):
    document = models.ForeignKey(ManagedDocument, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    file = models.FileField(upload_to="dms/versions/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("document", "version")
        ordering = ["-version"]


class Notification(TimeStamped):
    class Kind(models.TextChoices):
        LEAD = "lead", "New Lead"
        FOLLOW_UP = "follow_up", "Follow-up Due"
        PAYMENT = "payment", "Payment Due"
        LEAVE = "leave", "Leave Request"
        STOCK = "stock", "Low Stock"
        WARRANTY = "warranty", "Warranty Claim"
        TASK = "task", "Task"
        SERVICE = "service", "Service Ticket"
        SYSTEM = "system", "System"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SYSTEM, db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    email_sent = models.BooleanField(default=False)
    whatsapp_hint = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read", "-created_at"])]
