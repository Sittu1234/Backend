from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, DecimalField
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import User
from customers.models import Customer
from invoices.models import ProformaInvoice
from attendance.models import Attendance
from core.scoping import dealer_queryset, invoice_queryset


def _base_qs(request):
    return invoice_queryset(ProformaInvoice.objects.exclude(status="cancelled"), request.user)


def _tax_totals(qs):
    tax = qs.aggregate(
        taxable=Sum("subtotal"),
        cgst=Sum("cgst_amount"),
        sgst=Sum("sgst_amount"),
        igst=Sum("igst_amount"),
        gst=Sum("gst_amount"),
        sales=Sum("grand_total"),
    )
    return {
        "taxable": float(tax["taxable"] or 0),
        "cgst": float(tax["cgst"] or 0),
        "sgst": float(tax["sgst"] or 0),
        "igst": float(tax["igst"] or 0),
        "gst": float(tax["gst"] or 0),
        "sales_value": float(tax["sales"] or 0),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    qs = _base_qs(request)
    this_month = qs.filter(pi_date__gte=month_start.date())
    pending = qs.filter(status__in=["draft", "sent"])

    monthly_graph = (
        qs.filter(pi_date__gte=(now - timedelta(days=365)).date())
        .annotate(month=TruncMonth("pi_date"))
        .values("month")
        .annotate(total=Sum("grand_total"), count=Count("id"))
        .order_by("month")
    )
    top_customers = (
        qs.values("customer_id", "customer__customer_name", "customer__company_name")
        .annotate(total=Sum("grand_total"), count=Count("id"))
        .order_by("-total")[:5]
    )
    recent = qs.select_related("customer", "created_by").order_by("-created_at")[:8]
    tax = this_month.aggregate(
        taxable=Sum("subtotal"),
        cgst=Sum("cgst_amount"),
        sgst=Sum("sgst_amount"),
        igst=Sum("igst_amount"),
        gst=Sum("gst_amount"),
    )
    today = timezone.localdate()
    dealers = dealer_queryset(
        Customer.objects.filter(is_active=True, party_type=Customer.PartyType.DEALER),
        request.user,
    )
    vendors = Customer.objects.filter(is_active=True, party_type=Customer.PartyType.VENDOR)
    if request.user.is_sales:
        vendors = vendors.none()
    sales_team = User.objects.filter(role=User.Role.SALES, is_active=True)
    today_att = Attendance.objects.filter(date=today)
    mine = Attendance.objects.filter(user=request.user, date=today).first()
    return Response(
        {
            "total_invoices": qs.count(),
            "total_customers": dealers.count(),
            "total_dealers": dealers.count(),
            "total_vendors": vendors.count(),
            "sales_team_count": sales_team.count(),
            "present_today": today_att.filter(status=Attendance.Status.PRESENT).count(),
            "absent_today": today_att.filter(status=Attendance.Status.ABSENT).count(),
            "unmarked_today": max(sales_team.count() - today_att.filter(user__role=User.Role.SALES).count(), 0),
            "monthly_sales": float(this_month.aggregate(s=Sum("grand_total"))["s"] or 0),
            "pending_quotations": pending.count(),
            "monthly_taxable": float(tax["taxable"] or 0),
            "monthly_cgst": float(tax["cgst"] or 0),
            "monthly_sgst": float(tax["sgst"] or 0),
            "monthly_igst": float(tax["igst"] or 0),
            "monthly_gst": float(tax["gst"] or 0),
            "my_attendance": {
                "status": mine.status if mine else "unmarked",
                "check_in": mine.check_in.strftime("%H:%M:%S") if mine and mine.check_in else None,
                "check_out": mine.check_out.strftime("%H:%M:%S") if mine and mine.check_out else None,
            },
            "monthly_graph": [
                {
                    "month": row["month"].strftime("%Y-%m") if row["month"] else "",
                    "total": float(row["total"] or 0),
                    "count": row["count"],
                }
                for row in monthly_graph
            ],
            "top_customers": [
                {
                    "id": row["customer_id"],
                    "name": row["customer__customer_name"],
                    "company": row["customer__company_name"],
                    "total": float(row["total"] or 0),
                    "count": row["count"],
                }
                for row in top_customers
            ],
            "recent_invoices": [
                {
                    "id": inv.id,
                    "pi_number": inv.pi_number,
                    "customer": inv.customer.customer_name,
                    "pi_date": inv.pi_date,
                    "grand_total": float(inv.grand_total),
                    "status": inv.status,
                    "created_by": inv.created_by.name if inv.created_by else "",
                    "created_at": inv.created_at,
                    "last_sent_to": inv.last_sent_to,
                    "last_sent_via": inv.last_sent_via,
                    "last_sent_at": inv.last_sent_at,
                }
                for inv in recent
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def daily_report(request):
    date = request.query_params.get("date") or timezone.localdate().isoformat()
    qs = _base_qs(request).filter(pi_date=date)
    customers = qs.values("customer").distinct().count()
    tax = _tax_totals(qs)
    return Response(
        {
            "date": date,
            "pi_count": qs.count(),
            "sales_value": tax["sales_value"],
            "taxable": tax["taxable"],
            "cgst": tax["cgst"],
            "sgst": tax["sgst"],
            "igst": tax["igst"],
            "gst": tax["gst"],
            "customer_count": customers,
            "invoices": [
                {
                    "id": i.id,
                    "pi_number": i.pi_number,
                    "customer": i.customer.customer_name,
                    "grand_total": float(i.grand_total),
                    "status": i.status,
                    "created_by": i.created_by.name if i.created_by else "",
                    "created_at": i.created_at,
                    "last_sent_to": i.last_sent_to,
                    "last_sent_via": i.last_sent_via,
                    "last_sent_at": i.last_sent_at,
                }
                for i in qs.select_related("customer", "created_by")
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def monthly_report(request):
    now = timezone.now()
    year = int(request.query_params.get("year") or now.year)
    month = int(request.query_params.get("month") or now.month)
    qs = _base_qs(request).filter(pi_date__year=year, pi_date__month=month)
    daily = (
        qs.annotate(day=TruncDay("pi_date"))
        .values("day")
        .annotate(total=Sum("grand_total"), count=Count("id"))
        .order_by("day")
    )
    top = (
        qs.values("customer_id", "customer__customer_name", "customer__company_name")
        .annotate(total=Sum("grand_total"), count=Count("id"))
        .order_by("-total")[:10]
    )
    tax = _tax_totals(qs)
    return Response(
        {
            "year": year,
            "month": month,
            "pi_count": qs.count(),
            "sales_value": tax["sales_value"],
            "taxable": tax["taxable"],
            "cgst": tax["cgst"],
            "sgst": tax["sgst"],
            "igst": tax["igst"],
            "gst": tax["gst"],
            "daily": [
                {
                    "date": row["day"].strftime("%Y-%m-%d") if row["day"] else "",
                    "total": float(row["total"] or 0),
                    "count": row["count"],
                }
                for row in daily
            ],
            "top_customers": [
                {
                    "id": row["customer_id"],
                    "name": row["customer__customer_name"],
                    "company": row["customer__company_name"],
                    "total": float(row["total"] or 0),
                    "count": row["count"],
                }
                for row in top
            ],
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_report(request):
    qs = (
        _base_qs(request)
        .values("customer_id", "customer__customer_name", "customer__company_name", "customer__mobile")
        .annotate(total=Sum("grand_total"), count=Count("id"))
        .order_by("-total")
    )
    customer_id = request.query_params.get("customer")
    invoices = []
    if customer_id:
        invoices = [
            {
                "id": i.id,
                "pi_number": i.pi_number,
                "pi_date": i.pi_date,
                "grand_total": float(i.grand_total),
                "status": i.status,
            }
            for i in _base_qs(request).filter(customer_id=customer_id).select_related("customer")
        ]
    return Response(
        {
            "customers": [
                {
                    "id": row["customer_id"],
                    "name": row["customer__customer_name"],
                    "company": row["customer__company_name"],
                    "mobile": row["customer__mobile"],
                    "total": float(row["total"] or 0),
                    "count": row["count"],
                }
                for row in qs
            ],
            "invoices": invoices,
        }
    )
