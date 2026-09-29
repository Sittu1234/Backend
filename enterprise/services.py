from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from products.models import Product
from .models import (
    Lead,
    Payslip,
    ProductBatch,
    SalaryStructure,
    SerialNumber,
    StockBalance,
    StockMovement,
    Warehouse,
)
from .notify import notify


SOURCE_WEIGHT = {
    "referral": 22,
    "indiamart": 18,
    "website": 14,
    "justdial": 12,
    "linkedin": 12,
    "direct": 10,
    "facebook": 8,
    "instagram": 8,
}

STATUS_WEIGHT = {
    "new": 8,
    "contacted": 12,
    "follow_up": 16,
    "interested": 22,
    "negotiation": 28,
    "won": 40,
    "lost": 0,
}


def score_lead(lead: Lead) -> int:
    score = 30
    score += SOURCE_WEIGHT.get(lead.source, 8)
    score += STATUS_WEIGHT.get(lead.status, 8)
    if lead.next_follow_up:
        delta = (lead.next_follow_up.date() - timezone.localdate()).days
        if 0 <= delta <= 2:
            score += 12
        elif delta < 0:
            score += 6
    if lead.product_interest:
        score += 6
    if lead.email:
        score += 4
    return max(0, min(100, score))


def refresh_lead_score(lead: Lead):
    lead.priority_score = score_lead(lead)
    lead.save(update_fields=["priority_score"])
    return lead.priority_score


def followup_suggestion(lead: Lead) -> str:
    if lead.status == Lead.Status.NEW:
        return "Call within 30 minutes. Introduce Kalpna Traders batteries / EV range and capture GST + city."
    if lead.status == Lead.Status.CONTACTED:
        return "Share price list PDF and 2 matching SKUs. Book a follow-up for tomorrow."
    if lead.status == Lead.Status.FOLLOW_UP:
        return "WhatsApp a short catalogue + ask for monthly volume. Offer dealer scheme if volume is high."
    if lead.status == Lead.Status.INTERESTED:
        return "Send a quotation with business proposal. Confirm GST and shipping city."
    if lead.status == Lead.Status.NEGOTIATION:
        return "Offer a limited discount percent and payment terms (advance + balance). Close this week."
    if lead.status == Lead.Status.WON:
        return "Convert to dealer, create PI, and register warranty serials on dispatch."
    return "Mark lost reason and add to nurture list for a 30-day check-in."


def draft_email(lead: Lead) -> str:
    return (
        f"Dear {lead.contact_person},\n\n"
        f"Thank you for your interest in Kalpna Traders ({lead.product_interest or 'our battery & EV range'}).\n"
        "Please find our latest price list and product details. "
        "I will be happy to share a formal quotation as per your requirement.\n\n"
        "Regards,\nKalpna Traders · SPARS ERP"
    )


def draft_whatsapp(lead: Lead) -> str:
    return (
        f"Namaste {lead.contact_person}, Kalpna Traders se. "
        f"{lead.product_interest or 'Battery / EV scooter'} ke liye price list bhej raha hoon. "
        "Aapko quotation chahiye to company name, city aur qty bata dijiye."
    )


def _adjust_balance(warehouse: Warehouse, product: Product, delta: Decimal):
    bal, _ = StockBalance.objects.get_or_create(warehouse=warehouse, product=product, defaults={"qty": 0})
    StockBalance.objects.filter(pk=bal.pk).update(qty=F("qty") + delta)
    bal.refresh_from_db()
    if bal.qty < 0:
        raise ValidationError("Insufficient stock for this movement.")
    product.refresh_from_db()
    total = StockBalance.objects.filter(product=product).aggregate(t=Sum("qty"))["t"] or 0
    if Decimal(total) <= Decimal(product.min_stock or 0):
        from accounts.models import User

        for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True):
            notify(
                admin,
                "stock",
                f"Low stock: {product.product_code}",
                f"{product.product_name} total qty {total}. Min {product.min_stock}.",
                link="/inventory",
            )
    return bal


@transaction.atomic
def apply_stock_move(*, kind, warehouse, product, qty, user, to_warehouse=None, reference="", notes="", serials=None, batch_no="", mfg_date=None, expiry_date=None):
    qty = Decimal(str(qty))
    if qty <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    serials = [s.strip() for s in (serials or []) if str(s).strip()]

    if kind == StockMovement.Kind.IN:
        _adjust_balance(warehouse, product, qty)
        if batch_no:
            batch, _ = ProductBatch.objects.get_or_create(
                product=product,
                warehouse=warehouse,
                batch_no=batch_no,
                defaults={"mfg_date": mfg_date, "expiry_date": expiry_date, "qty": 0},
            )
            ProductBatch.objects.filter(pk=batch.pk).update(qty=F("qty") + qty)
        else:
            batch = None
        for serial in serials:
            SerialNumber.objects.update_or_create(
                serial=serial,
                defaults={
                    "product": product,
                    "warehouse": warehouse,
                    "status": SerialNumber.Status.IN_STOCK,
                    "batch": batch,
                },
            )
    elif kind == StockMovement.Kind.OUT:
        _adjust_balance(warehouse, product, -qty)
        for serial in serials:
            sn = SerialNumber.objects.filter(serial=serial).first()
            if sn:
                sn.status = SerialNumber.Status.SOLD
                sn.save(update_fields=["status", "updated_at"])
    elif kind == StockMovement.Kind.TRANSFER:
        if not to_warehouse:
            raise ValidationError("Destination warehouse is required for transfer.")
        if to_warehouse.pk == warehouse.pk:
            raise ValidationError("Source and destination warehouse must differ.")
        _adjust_balance(warehouse, product, -qty)
        _adjust_balance(to_warehouse, product, qty)
        for serial in serials:
            sn = SerialNumber.objects.filter(serial=serial).first()
            if sn:
                sn.warehouse = to_warehouse
                sn.status = SerialNumber.Status.TRANSFERRED
                sn.save(update_fields=["warehouse", "status", "updated_at"])
    else:
        raise ValidationError("Invalid movement type.")

    return StockMovement.objects.create(
        kind=kind,
        warehouse=warehouse,
        to_warehouse=to_warehouse,
        product=product,
        qty=qty,
        reference=reference,
        notes=notes,
        created_by=user,
    )


def compute_payslip(user, bonus=0):
    try:
        st = user.salary_structure
    except SalaryStructure.DoesNotExist:
        profile = getattr(user, "hr_profile", None)
        basic = Decimal(getattr(profile, "salary", 0) or 0)
        st = None
        hra = Decimal("0")
        incentive = Decimal("0")
        pf_p = Decimal("12")
        esi_p = Decimal("0.75")
        tds_p = Decimal("0")
    else:
        basic = Decimal(st.basic)
        hra = Decimal(st.hra)
        incentive = Decimal(st.incentive)
        pf_p = Decimal(st.pf_percent)
        esi_p = Decimal(st.esi_percent)
        tds_p = Decimal(st.tds_percent)
    bonus = Decimal(str(bonus or 0))
    gross = basic + hra + incentive + bonus
    pf = (basic * pf_p / Decimal("100")).quantize(Decimal("0.01"))
    esi = (gross * esi_p / Decimal("100")).quantize(Decimal("0.01"))
    tds = (gross * tds_p / Decimal("100")).quantize(Decimal("0.01"))
    net = (gross - pf - esi - tds).quantize(Decimal("0.01"))
    return {
        "basic": basic,
        "hra": hra,
        "incentive": incentive,
        "bonus": bonus,
        "pf": pf,
        "esi": esi,
        "tds": tds,
        "gross": gross.quantize(Decimal("0.01")),
        "net": net,
    }


@transaction.atomic
def process_payroll_run(run, user, bonuses=None):
    from accounts.models import User

    bonuses = bonuses or {}
    Payslip.objects.filter(payroll_run=run).delete()
    staff = User.objects.filter(is_active=True).exclude(role=User.Role.DEALER)
    count = 0
    for emp in staff:
        nums = compute_payslip(emp, bonuses.get(str(emp.id), bonuses.get(emp.id, 0)))
        Payslip.objects.create(payroll_run=run, user=emp, **nums)
        count += 1
    run.status = run.Status.PROCESSED
    run.processed_by = user
    run.processed_at = timezone.now()
    run.save(update_fields=["status", "processed_by", "processed_at"])
    return count
