from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = [
        ("PCS", "Pieces"),
        ("KG", "Kilogram"),
        ("G", "Gram"),
        ("LTR", "Litre"),
        ("MTR", "Meter"),
        ("BOX", "Box"),
        ("SET", "Set"),
        ("NOS", "Numbers"),
        ("PKT", "Packet"),
        ("TON", "Ton"),
    ]

    product_name = models.CharField(max_length=200)
    product_code = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    hsn_code = models.CharField(max_length=8, blank=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="PCS")
    gst = models.DecimalField(max_digits=5, decimal_places=2, default=18)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_name"]

    def __str__(self):
        return f"{self.product_code} – {self.product_name}"


class CatalogPdf(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=80, blank=True)
    file = models.FileField(upload_to="catalog_pdfs/")
    uploaded_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="catalog_pdfs",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
