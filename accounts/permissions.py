from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsInternalUser(BasePermission):
    """Staff ERP users (not dealer portal)."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_internal", False))


class IsDealer(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_dealer", False))


class IsHrOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_admin or user.is_hr))


class IsAccountsOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_internal):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_admin or user.is_accountant


class IsPayrollUser(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_admin or user.is_accountant or user.is_hr)
        )


class CanManageLeads(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_internal):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_admin or user.is_sales or user.is_manager


class CanManageInventory(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_internal):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_admin or user.is_accountant


class CanManagePurchases(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_internal):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_admin or user.is_accountant


class CanManagePayments(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_internal):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_admin or user.is_accountant or user.is_sales


class CanManageWarranty(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_internal):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_admin or user.is_sales or user.is_technician or user.is_accountant


class CanManageService(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_internal):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.is_admin or user.is_technician or user.is_sales or user.is_manager


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
        if not (user and user.is_authenticated and getattr(user, "is_internal", False)):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return user.is_admin or user.is_sales


class CanManageProducts(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and getattr(user, "is_internal", False)):
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
        if not (user and user.is_authenticated and getattr(user, "is_internal", False)):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        action = getattr(view, "action", None)
        if action in ("pdf", "email", "whatsapp"):
            return True
        return user.is_admin or user.is_sales
