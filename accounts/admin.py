from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import PasswordResetToken, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "employee_id", "name", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("email", "name", "employee_id")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("name", "employee_id", "role", "mobile")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "employee_id", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "expires_at", "used")
