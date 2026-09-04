from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "status", "check_in", "check_out")
    list_filter = ("status", "date")
    search_fields = ("user__name", "user__employee_id")
