from django.db import models

from company.terms import default_terms_text


class CompanySettings(models.Model):
    company_name = models.CharField(max_length=200, default="Kalpna Traders")
    tagline = models.CharField(
        max_length=200, blank=True, default="TRUST • QUALITY • GROWTH"
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=80, blank=True)
    state = models.CharField(max_length=80, blank=True, default="Maharashtra")
    pincode = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=80, default="India")
    gst_number = models.CharField(max_length=15, blank=True)
    pan_number = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)

    bank_name = models.CharField(max_length=150, blank=True)
    bank_account_name = models.CharField(max_length=150, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    bank_ifsc = models.CharField(max_length=15, blank=True)
    bank_branch = models.CharField(max_length=150, blank=True)

    default_gst = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    pi_prefix = models.CharField(max_length=10, default="QT")
    default_terms = models.TextField(blank=True, default=default_terms_text)
    email_template = models.TextField(
        blank=True,
        default=(
            "Dear {customer_name},\n\n"
            "Please find attached Proforma Invoice {pi_number} dated {pi_date} "
            "for {grand_total}.\n\n"
            "Valid till: {valid_till}\n\n"
            "Thank you for your business.\n\n"
            "Regards,\n{company_name}"
        ),
    )
    whatsapp_template = models.TextField(
        blank=True,
        default=(
            "Hello {customer_name}, your Proforma Invoice {pi_number} "
            "dated {pi_date} for INR {grand_total} is ready. Valid till {valid_till}."
        ),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company Settings"

    def __str__(self):
        return self.company_name

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CompanyEvent(models.Model):
    class Kind(models.TextChoices):
        EVENT = "event", "Company Event"
        BIRTHDAY = "birthday", "Birthday"
        FESTIVAL = "festival", "Festival"
        HOLIDAY = "holiday", "Holiday"

    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.EVENT)
    date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]

    def __str__(self):
        return f"{self.date} {self.title}"
