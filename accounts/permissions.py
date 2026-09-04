from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsSalesOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_admin or user.is_sales))


class CanManageCustomers(BasePermission):
    """Sales and Admin can write; Accountant is read-only."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return user.is_admin or user.is_sales


class CanManageProducts(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return user.is_admin


class CanManageInvoices(BasePermission):
    """
    Admin: full
    Sales: create/update own (write allowed)
    Accountant: read / print / pdf only
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        action = getattr(view, "action", None)
        if action in ("pdf", "email", "whatsapp"):
            return True
        return user.is_admin or user.is_sales
