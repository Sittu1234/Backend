from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from attendance.models import Attendance
from company.models import CompanySettings
from customers.models import Customer
from invoices.models import InvoiceItem, ProformaInvoice
from products.models import Category, Product


class Command(BaseCommand):
    help = "Seed SPARS ERP with demo users, customers, products and invoices"

    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            email="wendy.h@example.net",
            defaults={
                "name": "SPARS Admin",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "mobile": "9876543210",
                "employee_id": "KT001",
            },
        )
        admin.set_password("Admin@123")
        if not admin.employee_id:
            admin.employee_id = "KT001"
        admin.save()

        sales, _ = User.objects.get_or_create(
            email="marco.r@example.org",
            defaults={"name": "Rahul Sharma", "role": User.Role.SALES, "mobile": "9876500001", "employee_id": "KT002"},
        )
        sales.set_password("Sales@123")
        if not sales.employee_id:
            sales.employee_id = "KT002"
        sales.save()

        sales2, _ = User.objects.get_or_create(
            email="ursula.b@example.com",
            defaults={"name": "Neha Verma", "role": User.Role.SALES, "mobile": "9876500003", "employee_id": "KT004"},
        )
        sales2.set_password("Sales@123")
        if not sales2.employee_id:
            sales2.employee_id = "KT004"
        sales2.save()

        acc, _ = User.objects.get_or_create(
            email="iris.p@example.org",
            defaults={"name": "Priya Mehta", "role": User.Role.ACCOUNTANT, "mobile": "9876500002", "employee_id": "KT003"},
        )
        acc.set_password("Accounts@123")
        if not acc.employee_id:
            acc.employee_id = "KT003"
        acc.save()

        settings = CompanySettings.get_solo()
        settings.company_name = "Kalpna Traders"
        settings.tagline = "TRUST • QUALITY • GROWTH"
        settings.address = "C-77, Sector-63A, Chautpur"
        settings.city = ""
        settings.state = "Uttar Pradesh"
        settings.pincode = "201306"
        settings.gst_number = "09BUUPK1450R1ZQ"
        settings.pan_number = "BUUPK1450R"
        settings.phone = "9289975453"
        settings.email = "hrbp@kalpanatraders.com"
        settings.website = "https://www.kalpanatraders.com"
        settings.bank_name = "Kotak Mahindra Bank"
        settings.bank_account_name = "Kalpna Traders"
        settings.bank_account_number = "8550172123"
        settings.bank_ifsc = "KKBK0005028"
        settings.bank_branch = "Harsha Mall, Greater Noida, 201308"
        settings.default_gst = Decimal("18")
        settings.pi_prefix = "QT"
        settings.default_terms = (
            "KALPNA TRADERS: National channel partner of SPARS ELECTRIC.\n"
            "1. This is a computer generated quotation.\n"
            "2. Payment to be made as per agreed terms.\n"
            "3. Prices are exclusive of GST unless mentioned."
        )
        settings.save()

        from company.calendar_data import seed_calendar_events
        from company.models import CompanyEvent

        seed_calendar_events(CompanyEvent)

        from products.catalog import sync_today_price_list

        cats = {}
        for name in ["Industrial Fasteners", "Electrical", "Packaging", "Raw Materials"]:
            cats[name], _ = Category.objects.get_or_create(name=name)

        products = [
            ("MS Bolt M12", "SP-BOLT-012", "Industrial Fasteners", "7318", "PCS", 18, 12.50),
            ("MS Nut M12", "SP-NUT-012", "Industrial Fasteners", "7318", "PCS", 18, 4.75),
            ("Washer M12", "SP-WASH-012", "Industrial Fasteners", "7318", "PCS", 18, 1.20),
            ("Copper Cable 2.5mm", "SP-CAB-25", "Electrical", "8544", "MTR", 18, 48.00),
            ("MCB 32A", "SP-MCB-32", "Electrical", "8536", "NOS", 18, 320.00),
            ("Corrugated Box 18x12", "SP-BOX-1812", "Packaging", "4819", "PCS", 12, 28.00),
            ("Stretch Film 50mic", "SP-FILM-50", "Packaging", "3920", "KG", 18, 145.00),
            ("Mild Steel Round 20mm", "SP-MS-20", "Raw Materials", "7214", "KG", 18, 62.00),
        ]
        product_objs = []
        for name, code, cat, hsn, unit, gst, price in products:
            obj, _ = Product.objects.get_or_create(
                product_code=code,
                defaults={
                    "product_name": name,
                    "category": cats[cat],
                    "hsn_code": hsn,
                    "unit": unit,
                    "gst": gst,
                    "price": Decimal(str(price)),
                    "description": f"Quality {name} for industrial use.",
                },
            )
            product_objs.append(obj)

        sync_today_price_list()

        customer_rows = [
            {
                "customer_name": "Amit Patel",
                "company_name": "Patel Engineering Works",
                "gst_no": "24AABCP1111A1Z2",
                "contact_person": "Amit Patel",
                "mobile": "9825011122",
                "email": "iris.p@example.org",
                "billing_address": "12 GIDC, Vatva",
                "state": "Gujarat",
                "city": "Ahmedabad",
                "pincode": "382445",
            },
            {
                "customer_name": "Sneha Iyer",
                "company_name": "Iyer Electricals",
                "gst_no": "27AABCI2222B1Z8",
                "contact_person": "Sneha Iyer",
                "mobile": "9881100444",
                "email": "xena.w@example.org",
                "billing_address": "88 FC Road",
                "state": "Maharashtra",
                "city": "Pune",
                "pincode": "411004",
            },
            {
                "customer_name": "Ravi Kumar",
                "company_name": "Kumar Traders",
                "gst_no": "29AABCK3333C1Z4",
                "contact_person": "Ravi Kumar",
                "mobile": "9845012398",
                "email": "julia.r@example.org",
                "billing_address": "Peenya Industrial Area",
                "state": "Karnataka",
                "city": "Bengaluru",
                "pincode": "560058",
            },
        ]
        customers = []
        owners = [sales, sales, sales2]
        for row, owner in zip(customer_rows, owners):
            obj, _ = Customer.objects.get_or_create(
                mobile=row["mobile"],
                defaults={**row, "created_by": owner, "assigned_to": owner, "party_type": Customer.PartyType.DEALER},
            )
            if not obj.assigned_to:
                obj.assigned_to = owner
                obj.party_type = Customer.PartyType.DEALER
                obj.save(update_fields=["assigned_to", "party_type"])
            customers.append(obj)

        Customer.objects.get_or_create(
            mobile="9810099001",
            defaults={
                "customer_name": "Shree Steel Suppliers",
                "company_name": "Shree Steel Suppliers Pvt Ltd",
                "party_type": Customer.PartyType.VENDOR,
                "gst_no": "09AABCS9999A1Z1",
                "contact_person": "Manoj Gupta",
                "email": "hannah.h@example.com",
                "billing_address": "Industrial Area, Site-5",
                "state": "Uttar Pradesh",
                "city": "Ghaziabad",
                "pincode": "201001",
                "created_by": admin,
            },
        )

        today = timezone.localdate()
        Attendance.objects.get_or_create(
            user=sales,
            date=today,
            defaults={
                "check_in": timezone.localtime().replace(hour=9, minute=15, second=0, microsecond=0).time(),
                "status": Attendance.Status.PRESENT,
                "marked_by": admin,
            },
        )
        Attendance.objects.get_or_create(
            user=acc,
            date=today,
            defaults={"status": Attendance.Status.PRESENT, "marked_by": admin},
        )

        if not ProformaInvoice.objects.exists():
            today = timezone.localdate()
            inv = ProformaInvoice.objects.create(
                pi_number=ProformaInvoice.next_pi_number("PI"),
                pi_date=today - timedelta(days=3),
                valid_till=today + timedelta(days=12),
                customer=customers[1],
                freight_charges=Decimal("500"),
                packing_charges=Decimal("200"),
                discount_percent=Decimal("5"),
                notes="Delivery within 7 working days after confirmation.",
                terms=settings.default_terms,
                created_by=sales,
                status="sent",
            )
            InvoiceItem.objects.create(
                invoice=inv,
                product=product_objs[0],
                product_name=product_objs[0].product_name,
                hsn_code=product_objs[0].hsn_code,
                unit=product_objs[0].unit,
                qty=500,
                rate=product_objs[0].price,
                gst=product_objs[0].gst,
            )
            InvoiceItem.objects.create(
                invoice=inv,
                product=product_objs[1],
                product_name=product_objs[1].product_name,
                hsn_code=product_objs[1].hsn_code,
                unit=product_objs[1].unit,
                qty=500,
                rate=product_objs[1].price,
                gst=product_objs[1].gst,
            )
            InvoiceItem.objects.create(
                invoice=inv,
                product=product_objs[4],
                product_name=product_objs[4].product_name,
                hsn_code=product_objs[4].hsn_code,
                unit=product_objs[4].unit,
                qty=20,
                rate=product_objs[4].price,
                gst=product_objs[4].gst,
            )
            inv.recalculate()

            inv2 = ProformaInvoice.objects.create(
                pi_number=ProformaInvoice.next_pi_number("PI"),
                pi_date=today,
                valid_till=today + timedelta(days=15),
                customer=customers[0],
                freight_charges=Decimal("1200"),
                packing_charges=Decimal("0"),
                discount=Decimal("0"),
                created_by=sales,
                terms=settings.default_terms,
                status="draft",
            )
            InvoiceItem.objects.create(
                invoice=inv2,
                product=product_objs[7],
                product_name=product_objs[7].product_name,
                hsn_code=product_objs[7].hsn_code,
                unit=product_objs[7].unit,
                qty=250,
                rate=product_objs[7].price,
                gst=product_objs[7].gst,
            )
            inv2.recalculate()

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("Admin:      KT001 / wendy.h@example.net / Admin@123")
        self.stdout.write("Sales:      KT002 / marco.r@example.org / Sales@123")
        self.stdout.write("Sales 2:    KT004 / ursula.b@example.com / Sales@123")
        self.stdout.write("Accountant: KT003 / iris.p@example.org / Accounts@123")
