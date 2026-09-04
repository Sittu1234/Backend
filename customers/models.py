from django.db import models


class Customer(models.Model):
    class PartyType(models.TextChoices):
        DEALER = "dealer", "Dealer"
        VENDOR = "vendor", "Vendor"

    customer_name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    party_type = models.CharField(
        max_length=20, choices=PartyType.choices, default=PartyType.DEALER, db_index=True
    )
    gst_no = models.CharField(max_length=15, blank=True)
    contact_person = models.CharField(max_length=150, blank=True)
    mobile = models.CharField(max_length=15)
    alternate_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    billing_address = models.TextField()
    shipping_address = models.TextField(blank=True)
    state = models.CharField(max_length=80)
    city = models.CharField(max_length=80)
    pincode = models.CharField(max_length=10)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    assigned_to = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dealers",
        help_text="Sales executive responsible for this dealer",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customers",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["customer_name"]

    def __str__(self):
        return self.company_name or self.customer_name
