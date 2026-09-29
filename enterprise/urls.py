from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("leads", views.LeadViewSet, basename="leads")
router.register("warehouses", views.WarehouseViewSet, basename="warehouses")
router.register("stock", views.StockBalanceViewSet, basename="stock")
router.register("stock-moves", views.StockMovementViewSet, basename="stock-moves")
router.register("serials", views.SerialNumberViewSet, basename="serials")
router.register("batches", views.ProductBatchViewSet, basename="batches")
router.register("purchase-orders", views.PurchaseOrderViewSet, basename="purchase-orders")
router.register("grn", views.GoodsReceiptViewSet, basename="grn")
router.register("purchase-bills", views.PurchaseBillViewSet, basename="purchase-bills")
router.register("vendor-payments", views.VendorPaymentViewSet, basename="vendor-payments")
router.register("payments", views.PaymentViewSet, basename="payments")
router.register("departments", views.DepartmentViewSet, basename="departments")
router.register("employees", views.EmployeeProfileViewSet, basename="employees")
router.register("employee-docs", views.EmployeeDocumentViewSet, basename="employee-docs")
router.register("leave-balances", views.LeaveBalanceViewSet, basename="leave-balances")
router.register("leaves", views.LeaveRequestViewSet, basename="leaves")
router.register("salary-structures", views.SalaryStructureViewSet, basename="salary-structures")
router.register("payroll", views.PayrollRunViewSet, basename="payroll")
router.register("payslips", views.PayslipViewSet, basename="payslips")
router.register("warranties", views.WarrantyRegistrationViewSet, basename="warranties")
router.register("warranty-claims", views.WarrantyClaimViewSet, basename="warranty-claims")
router.register("service-tickets", views.ServiceTicketViewSet, basename="service-tickets")
router.register("tasks", views.WorkTaskViewSet, basename="tasks")
router.register("folders", views.DocFolderViewSet, basename="folders")
router.register("documents", views.ManagedDocumentViewSet, basename="documents")
router.register("notifications", views.NotificationViewSet, basename="notifications")

urlpatterns = [
    path("md/", views.md_dashboard),
    path("ai/", views.ai_assistant),
    path("portal/home/", views.portal_home),
    path("portal/products/", views.portal_products),
    path("portal/catalogs/", views.portal_catalogs),
    path("portal/invoices/", views.portal_invoices),
    path("portal/invoices/<int:pk>/pdf/", views.portal_invoice_pdf),
    path("portal/tickets/", views.portal_tickets),
    path("portal/tickets/create/", views.portal_ticket),
    path("portal/warranty/", views.portal_warranties),
    path("portal/warranty/claim/", views.portal_warranty_claim),
    path("portal/invite/", views.portal_invite),
    path("", include(router.urls)),
]
