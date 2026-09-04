from rest_framework import serializers

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    employee_id = serializers.CharField(source="user.employee_id", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)
    marked_by_name = serializers.CharField(source="marked_by.name", read_only=True)

    class Meta:
        model = Attendance
        fields = (
            "id",
            "user",
            "user_name",
            "employee_id",
            "user_role",
            "date",
            "check_in",
            "check_out",
            "status",
            "notes",
            "marked_by",
            "marked_by_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "marked_by", "created_at", "updated_at")
