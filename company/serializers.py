from rest_framework import serializers

from .models import CareerOpening, CompanyEvent, CompanySettings, PublicPage


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = "__all__"


class PublicPageSerializer(serializers.ModelSerializer):
    highlights = serializers.SerializerMethodField()

    class Meta:
        model = PublicPage
        fields = "__all__"
        read_only_fields = ("id", "updated_at")

    def get_highlights(self, obj):
        rows = [
            {"title": obj.highlight_1_title, "body": obj.highlight_1_body, "image": obj.highlight_1_image},
            {"title": obj.highlight_2_title, "body": obj.highlight_2_body, "image": obj.highlight_2_image},
            {"title": obj.highlight_3_title, "body": obj.highlight_3_body, "image": obj.highlight_3_image},
        ]
        return [row for row in rows if (row["title"] or "").strip()]


class CareerOpeningSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerOpening
        fields = (
            "id",
            "title",
            "department",
            "location",
            "employment_type",
            "description",
            "apply_email",
            "is_active",
            "sort_order",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class PublicCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = (
            "company_name",
            "tagline",
            "address",
            "city",
            "state",
            "pincode",
            "phone",
            "email",
            "website",
            "gst_number",
        )


class CompanyEventSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = CompanyEvent
        fields = (
            "id",
            "title",
            "kind",
            "kind_label",
            "date",
            "end_date",
            "description",
            "is_public",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
