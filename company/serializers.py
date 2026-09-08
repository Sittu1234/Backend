from rest_framework import serializers

from .models import CompanyEvent, CompanySettings


class CompanySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySettings
        fields = "__all__"


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
