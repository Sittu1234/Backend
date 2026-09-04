from rest_framework import serializers

from .models import CatalogPdf, Category, Product


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(source="products.count", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "description", "product_count", "created_at")


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class CatalogPdfSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.name", read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = CatalogPdf
        fields = (
            "id",
            "title",
            "category",
            "file",
            "file_url",
            "file_name",
            "uploaded_by",
            "uploaded_by_name",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "uploaded_by", "created_at")

    def get_file_url(self, obj):
        if not obj.file:
            return None
        url = obj.file.url
        if url.startswith("http"):
            return url
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_file_name(self, obj):
        return obj.file.name.split("/")[-1] if obj.file else ""

    def validate_file(self, value):
        name = (getattr(value, "name", "") or "").lower()
        if not name.endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are allowed.")
        return value
