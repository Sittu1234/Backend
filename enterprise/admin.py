from django.contrib import admin

from . import models

admin.site.register(models.Lead)
admin.site.register(models.Warehouse)
admin.site.register(models.StockBalance)
admin.site.register(models.PurchaseOrder)
admin.site.register(models.Payment)
admin.site.register(models.EmployeeProfile)
admin.site.register(models.LeaveRequest)
admin.site.register(models.PayrollRun)
admin.site.register(models.Payslip)
admin.site.register(models.WarrantyRegistration)
admin.site.register(models.WarrantyClaim)
admin.site.register(models.ServiceTicket)
admin.site.register(models.WorkTask)
admin.site.register(models.ManagedDocument)
admin.site.register(models.Notification)
