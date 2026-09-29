from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from company.models import CompanySettings
from core.utils import amount_in_words, indian_money


def _header(c, company, title, number):
    c.setFillColorRGB(0.04, 0.15, 0.25)
    c.rect(0, A4[1] - 28 * mm, A4[0], 28 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(16 * mm, A4[1] - 14 * mm, company.company_name or "Kalpna Traders")
    c.setFont("Helvetica", 9)
    c.drawRightString(A4[0] - 16 * mm, A4[1] - 12 * mm, title)
    c.drawRightString(A4[0] - 16 * mm, A4[1] - 18 * mm, number)


def build_receipt_pdf(payment) -> bytes:
    company = CompanySettings.get_solo()
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _header(c, company, "PAYMENT RECEIPT", payment.receipt_number)
    y = A4[1] - 40 * mm
    c.setFillColorRGB(0.04, 0.15, 0.25)
    c.setFont("Helvetica", 10)
    lines = [
        f"Received from: {payment.customer.company_name or payment.customer.customer_name}",
        f"Date: {payment.received_on.strftime('%d-%m-%Y')}",
        f"Mode: {payment.get_mode_display()}  |  Type: {payment.get_kind_display()}",
        f"Reference: {payment.reference or '-'}",
        f"Against: {(payment.invoice.tax_invoice_number or payment.invoice.pi_number) if payment.invoice_id else 'On account'}",
        f"Amount: ₹ {indian_money(payment.amount)}",
        f"In words: {amount_in_words(payment.amount)}",
        f"Notes: {payment.notes or '-'}",
    ]
    for line in lines:
        c.drawString(20 * mm, y, line)
        y -= 8 * mm
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 20 * mm, f"{company.address} · {company.phone} · {company.email}")
    c.showPage()
    c.save()
    return buf.getvalue()


def build_payslip_pdf(payslip) -> bytes:
    company = CompanySettings.get_solo()
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    title = f"PAYSLIP {payslip.payroll_run.month:02d}/{payslip.payroll_run.year}"
    _header(c, company, title, payslip.user.employee_id or "")
    y = A4[1] - 42 * mm
    c.setFillColorRGB(0.04, 0.15, 0.25)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, payslip.user.name)
    y -= 8 * mm
    c.setFont("Helvetica", 10)
    rows = [
        ("Basic", payslip.basic),
        ("HRA", payslip.hra),
        ("Incentive", payslip.incentive),
        ("Bonus", payslip.bonus),
        ("Gross", payslip.gross),
        ("PF", payslip.pf),
        ("ESI", payslip.esi),
        ("TDS", payslip.tds),
        ("Net Pay", payslip.net),
    ]
    for label, value in rows:
        c.drawString(20 * mm, y, label)
        c.drawRightString(120 * mm, y, f"₹ {indian_money(value)}")
        y -= 7 * mm
    c.setFont("Helvetica", 8)
    c.drawString(20 * mm, 20 * mm, "This is a system-generated payslip from SPARS ERP.")
    c.showPage()
    c.save()
    return buf.getvalue()
