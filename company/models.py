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


class PublicPage(models.Model):
    hero_kicker = models.CharField(
        max_length=200, blank=True, default="National channel partner · SPARS Electric"
    )
    hero_title = models.CharField(max_length=200, blank=True)
    hero_body = models.TextField(
        blank=True,
        default=(
            "EV scooters, lithium packs and LED batteries — quotations, tax invoices "
            "and dealer support from one Noida team."
        ),
    )
    cta_primary = models.CharField(max_length=80, blank=True, default="Company calendar")
    cta_secondary = models.CharField(max_length=80, blank=True, default="Contact HR / office")
    hero_image = models.CharField(max_length=400, blank=True, default="/home/hero-showroom.jpg")

    about_kicker = models.CharField(max_length=80, blank=True, default="About the company")
    about_title = models.CharField(
        max_length=200, blank=True, default="A trading house built on people and products"
    )
    about_body = models.TextField(
        blank=True,
        default=(
            "Kalpna Traders is the commercial face of SPARS Electric in North India. "
            "Dealers get GST-ready quotations, a live price list and a team that shows "
            "up for launches, birthdays and festivals alike."
        ),
    )

    products_kicker = models.CharField(max_length=80, blank=True, default="Product range")
    products_title = models.CharField(
        max_length=200, blank=True, default="What we quote every day"
    )
    highlight_1_title = models.CharField(max_length=80, blank=True, default="EV Scooter")
    highlight_1_body = models.TextField(
        blank=True, default="Models, battery options and RTO-ready quotations from one desk."
    )
    highlight_1_image = models.CharField(max_length=400, blank=True, default="/home/ev-scooter.jpg")
    highlight_2_title = models.CharField(max_length=80, blank=True, default="Lithium packs")
    highlight_2_body = models.TextField(
        blank=True, default="Voltage, Ah, BMS and connector as per the signed specification."
    )
    highlight_2_image = models.CharField(
        max_length=400, blank=True, default="/home/lithium-battery.jpg"
    )
    highlight_3_title = models.CharField(max_length=80, blank=True, default="LED / inverter")
    highlight_3_body = models.TextField(
        blank=True, default="Stock range with HSN, GST and dealer price list support."
    )
    highlight_3_image = models.CharField(max_length=400, blank=True, default="/home/led-battery.jpg")

    careers_kicker = models.CharField(max_length=80, blank=True, default="Careers")
    careers_title = models.CharField(
        max_length=200, blank=True, default="Build your career with Kalpna Traders"
    )
    careers_body = models.TextField(
        blank=True,
        default=(
            "Sales, accounts and warehouse roles at our Noida desk. "
            "Apply with a short note — we reply from HR."
        ),
    )
    careers_email = models.EmailField(blank=True, default="hrbp@kalpanatraders.com")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Public page"

    def __str__(self):
        return "Public page"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CareerOpening(models.Model):
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=80, blank=True)
    location = models.CharField(max_length=120, blank=True, default="Noida")
    employment_type = models.CharField(max_length=40, blank=True, default="Full-time")
    description = models.TextField(blank=True)
    apply_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-created_at", "id"]

    def __str__(self):
        return self.title
