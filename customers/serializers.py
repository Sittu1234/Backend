from rest_framework import serializers

from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.name", read_only=True)
    assigned_to_employee_id = serializers.CharField(source="assigned_to.employee_id", read_only=True)

    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ("id", "created_by", "created_at", "updated_at")
