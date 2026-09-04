from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsAdmin
from .models import ActivityLog


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ActivityLog
        fields = "__all__"


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.select_related("user")
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["action", "model_name", "details", "user__name"]
    filterset_fields = ["action", "model_name"]

    def get_permissions(self):
        return [IsAdmin()]
