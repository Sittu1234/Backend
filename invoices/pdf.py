from decimal import Decimal
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from company.models import CompanySettings
from company.terms import ADDITIONAL_INFO, PI_KIND_LABELS, parse_terms_text, terms_text_for_kind
from core.utils import amount_in_words, indian_money
from django.conf import settings as dj_settings

NAVY = colors.HexColor("#163A5F")
NAVY_DARK = colors.HexColor("#0F2C4A")
BORDER = colors.HexColor("#9AA4B2")
HEAD_BG = colors.HexColor("#EEF1F4")
MUTED = colors.HexColor("#4B5563")
BLACK = colors.black
WHITE = colors.white
ROW_H = colors.HexColor("#F8FAFC")

PAGE_W, PAGE_H = A4
ML, MR, MT, MB = 10 * mm, 10 * mm, 8 * mm, 14 * mm
CONTENT_W = PAGE_W - ML - MR


def _esc(text) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _styles():
    return {
        "brand": ParagraphStyle(
            "ke_brand",
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            alignment=TA_CENTER,
            textColor=NAVY_DARK,
        ),
        "tag": ParagraphStyle(
            "ke_tag",
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            alignment=TA_CENTER,
            textColor=MUTED,
        ),
        "meta": ParagraphStyle(
            "ke_meta", fontName="Helvetica", fontSize=8, leading=11, alignment=TA_CENTER, textColor=BLACK
        ),
        "bar": ParagraphStyle(
            "ke_bar",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            textColor=WHITE,
        ),
        "hcell": ParagraphStyle(
            "ke_hcell",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "lab": ParagraphStyle("ke_lab", fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=BLACK),
        "val": ParagraphStyle("ke_val", fontName="Helvetica", fontSize=8, leading=11, textColor=BLACK),
        "th": ParagraphStyle(
            "ke_th", fontName="Helvetica-Bold", fontSize=7.5, leading=10, alignment=TA_CENTER, textColor=BLACK
        ),
        "td": ParagraphStyle("ke_td", fontName="Helvetica", fontSize=8, leading=10, alignment=TA_CENTER),
        "tdl": ParagraphStyle("ke_tdl", fontName="Helvetica", fontSize=8, leading=10, alignment=TA_LEFT),
        "tdnote": ParagraphStyle(
            "ke_tdnote", fontName="Helvetica-Oblique", fontSize=7, leading=9, alignment=TA_LEFT, textColor=MUTED
        ),
        "tdr": ParagraphStyle("ke_tdr", fontName="Helvetica", fontSize=8, leading=10, alignment=TA_RIGHT),
        "boxh": ParagraphStyle(
            "ke_boxh", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=NAVY_DARK
        ),
        "small": ParagraphStyle("ke_small", fontName="Helvetica", fontSize=7.5, leading=10.5, textColor=BLACK),
        "smallb": ParagraphStyle(
            "ke_smallb", fontName="Helvetica-Bold", fontSize=7.5, leading=10.5, textColor=BLACK
        ),
        "words": ParagraphStyle("ke_words", fontName="Helvetica", fontSize=8, leading=11, textColor=BLACK),
        "num": ParagraphStyle(
            "ke_num", fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=NAVY_DARK, alignment=TA_RIGHT
        ),
        "term": ParagraphStyle(
            "ke_term", fontName="Helvetica", fontSize=8.5, leading=12, alignment=TA_LEFT, textColor=BLACK
        ),
        "sec": ParagraphStyle(
            "ke_sec", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=NAVY_DARK
        ),
        "foot": ParagraphStyle(
            "ke_foot", fontName="Helvetica", fontSize=7.5, leading=10, alignment=TA_CENTER, textColor=BLACK
        ),
        "p2brand": ParagraphStyle(
            "ke_p2brand",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=NAVY_DARK,
        ),
    }


ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _rl_image(source, w, h):
    try:
        if isinstance(source, (bytes, bytearray)):
            return Image(BytesIO(source), width=w, height=h, lazy=0)
        return Image(str(source), width=w, height=h, lazy=0)
    except Exception:
        return ""


def _logo(name: str, w, h):
    candidates = [
        ASSETS_DIR / name,
        Path(dj_settings.MEDIA_ROOT) / "logos" / name,
        Path(dj_settings.BASE_DIR).parent / "frontend" / "public" / name,
    ]
    for p in candidates:
        if p.is_file():
            img = _rl_image(p, w, h)
            if img:
                return img
    return ""


def _company_logo(company, w, h):
    field = getattr(company, "logo", None)
    if not field:
        return ""
    try:
        with field.open("rb") as fh:
            data = fh.read()
        if data:
            return _rl_image(data, w, h)
    except Exception:
        pass
    try:
        url = field.url
        if url and str(url).startswith("http"):
            data = urlopen(url, timeout=12).read()
            if data:
                return _rl_image(data, w, h)
    except Exception:
        pass
    return ""


def _kv(pairs, s, w_label, w_val):
    data = [
        [Paragraph(k, s["lab"]), Paragraph(v or "—", s["val"])]
        for k, v in pairs
    ]
    t = Table(data, colWidths=[w_label, w_val])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ]
        )
    )
    return t


def _box(title, inner, s, width):
    head = Table([[Paragraph(title, s["hcell"])]], colWidths=[width])
    head.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    body = Table([[inner]], colWidths=[width])
    body.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    wrap = Table([[head], [body]], colWidths=[width])
    wrap.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return wrap


def _navy_bar(text, s, width=CONTENT_W, size=12):
    style = ParagraphStyle("barx", parent=s["bar"], fontSize=size)
    t = Table([[Paragraph(text, style)]], colWidths=[width])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _section_title(title: str, s) -> Table:
    t = Table([[Paragraph(title, s["sec"])]], colWidths=[CONTENT_W])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), HEAD_BG),
                ("LINEBEFORE", (0, 0), (0, 0), 2.2, NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _numbered_terms(items, s) -> Table:
    rows = [
        [Paragraph(f"{i}.", s["num"]), Paragraph(text, s["term"])]
        for i, text in enumerate(items, 1)
    ]
    t = Table(rows, colWidths=[10 * mm, CONTENT_W - 10 * mm])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, -1), 2),
                ("RIGHTPADDING", (0, 0), (0, -1), 4),
                ("LEFTPADDING", (1, 0), (1, -1), 2),
                ("RIGHTPADDING", (1, 0), (1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("LINEBELOW", (0, 0), (-1, -2), 0.15, colors.HexColor("#E5E7EB")),
            ]
        )
    )
    return t


def _header_block(company, s, page2=False):
    left = _logo("kalpna-header.png", 24 * mm, 24 * mm) or _company_logo(company, 24 * mm, 24 * mm)
    right = _logo("kila-header.png", 22 * mm, 22 * mm)
    addr = ", ".join(filter(None, [company.address, company.city, company.pincode]))
    gst_phone = "  |  ".join(
        filter(
            None,
            [
                f"GST: {company.gst_number}" if company.gst_number else "",
                f"Phone: {company.phone}" if company.phone else "",
            ],
        )
    )
    brand = (company.company_name or "Kalpna Traders").strip()
    if page2:
        center = [
            Paragraph(brand, s["p2brand"]),
            Paragraph(f"{addr}  |  {gst_phone}", s["meta"]),
        ]
    else:
        center = [
            Paragraph(brand, s["brand"]),
            Paragraph(company.tagline or "Trust · Quality · Growth", s["tag"]),
            Paragraph(addr, s["meta"]),
            Paragraph(gst_phone, s["meta"]),
            Paragraph(f"Email: {company.email}" if company.email else "", s["meta"]),
        ]
    t = Table([[left, center, right]], colWidths=[28 * mm, CONTENT_W - 56 * mm, 28 * mm])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


class NumberedCanvas(pdfcanvas.Canvas):
    def __init__(self, *args, quote_no="", quote_date="", no_label="Quotation No.", date_label="Quotation Date", **kwargs):
        pdfcanvas.Canvas.__init__(self, *args, **kwargs)
        self._saved = []
        self.quote_no = quote_no
        self.quote_date = quote_date
        self.no_label = no_label
        self.date_label = date_label

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            self.setFillColor(MUTED)
            self.setFont("Helvetica", 7)
            y = 8 * mm
            self.drawString(ML, y, f"{self.no_label} {self.quote_no}")
            self.drawCentredString(PAGE_W / 2, y, f"{self.date_label} {self.quote_date}")
            self.drawRightString(PAGE_W - MR, y, f"Page {self._pageNumber} of {total}")
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)


def build_pi_pdf(invoice, as_tax_invoice=False) -> bytes:
    company = CompanySettings.get_solo()
    s = _styles()
    items = list(invoice.items.all())
    cust = invoice.customer
    is_tax = bool(as_tax_invoice)
    doc_date_obj = invoice.tax_invoice_date if is_tax and invoice.tax_invoice_date else invoice.pi_date
    qdate = doc_date_obj.strftime("%d-%m-%Y")
    doc_no = invoice.tax_invoice_number if is_tax and invoice.tax_invoice_number else invoice.pi_number
    bar_title = "Tax Invoice" if is_tax else "Quotation"
    for_label = "Invoice for" if is_tax else "Quotation for"
    date_label = "Invoice Date :" if is_tax else "Quotation Date :"
    no_label = "Tax Invoice No. :" if is_tax else "Quotation No. :"
    foot_no = "Tax Invoice No." if is_tax else "Quotation No."
    foot_date = "Invoice Date" if is_tax else "Quotation Date"
    cust_id = f"CU{cust.id:08d}"
    cart_id = f"CT{invoice.id}"
    ship_from = "Noida (Sector-63A)"
    courier = "Self Pickup / Transport"
    mode = "By Hand / Courier"
    advance = Decimal(getattr(invoice, "advance_received", 0) or 0)
    balance = invoice.balance_due if is_tax else invoice.grand_total
    if is_tax:
        if advance <= 0:
            pay = "Due as per this invoice"
        elif Decimal(balance or 0) <= 0:
            pay = "Paid in Full"
        else:
            pay = "Advance received, balance due"
    else:
        pay = "100% Advance before Sales Order"
    gst_rates = [float(i.gst or 0) for i in items]
    common_gst = gst_rates[0] if gst_rates and len(set(gst_rates)) == 1 else None
    gst_label = f"GST Amount ({common_gst:g}%)" if common_gst is not None else "GST Amount"

    half = (CONTENT_W - 2 * mm) / 2

    # Page 1
    story = [_header_block(company, s, page2=False), Spacer(1, 2)]
    story.append(_navy_bar(bar_title, s))
    kind_label = PI_KIND_LABELS.get(getattr(invoice, "pi_kind", "") or "", "")
    if kind_label:
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"<b>{for_label} :</b>  {kind_label}", s["words"]))
    story.append(Spacer(1, 3))

    left_meta = _kv(
        [
            ("Customer Id :", cust_id),
            ("Customer Name :", cust.customer_name),
            ("Requested Mode Of Shipment :", mode),
        ],
        s,
        48 * mm,
        half - 48 * mm,
    )
    right_pairs = [
        (date_label, qdate),
        (no_label, doc_no),
    ]
    if is_tax:
        right_pairs.append(("Against PI :", invoice.pi_number))
    else:
        right_pairs.append(("Cart Id :", cart_id))
    right_pairs.append(("Payment Terms :", pay))
    right_meta = _kv(
        right_pairs,
        s,
        38 * mm,
        half - 38 * mm,
    )
    meta = Table([[left_meta, right_meta]], colWidths=[half, half + 2 * mm])
    meta.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEAFTER", (0, 0), (0, 0), 0.4, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(meta)
    story.append(Spacer(1, 3))

    bill_inner = [
        Paragraph(cust.customer_name, s["lab"]),
        Paragraph(cust.billing_address or "", s["val"]),
        Paragraph(f"{cust.city}, {cust.state} {cust.pincode}".strip(), s["val"]) if cust.city or cust.state else "",
        Paragraph(f"Phone: {cust.mobile or '—'}", s["val"]),
        Paragraph(f"Email: {cust.email or '—'}", s["val"]),
        Paragraph(f"GSTIN: {cust.gst_no or '—'}", s["val"]),
    ]
    ship_addr = cust.shipping_address or cust.billing_address
    ship_inner = [
        Paragraph(cust.customer_name, s["lab"]),
        Paragraph(ship_addr or "", s["val"]),
        Paragraph(f"{cust.city}, {cust.state} {cust.pincode}".strip(), s["val"]) if cust.city or cust.state else "",
        Paragraph(f"Phone: {cust.mobile or '—'}", s["val"]),
        Paragraph(f"Email: {cust.email or '—'}", s["val"]),
        Paragraph(f"GSTIN: {cust.gst_no or '—'}", s["val"]),
    ]
    parties = Table(
        [[_box("Buyer (Bill To)", bill_inner, s, half), _box("Consignee (Ship To)", ship_inner, s, half)]],
        colWidths=[half, half],
    )
    parties.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 1 * mm),
                ("LEFTPADDING", (1, 0), (1, 0), 1 * mm),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    story.append(parties)
    story.append(Spacer(1, 3))

    ship_row = Table(
        [
            [
                Paragraph(f"<b>Bill / Ship From :</b>  {ship_from}", s["val"]),
                Paragraph(f"<b>Courier :</b>  {courier}", s["val"]),
            ]
        ],
        colWidths=[half, half],
    )
    ship_row.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("LINEAFTER", (0, 0), (0, 0), 0.4, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(ship_row)
    story.append(Spacer(1, 3))

    col_w = [10 * mm, 28 * mm, 52 * mm, 22 * mm, 22 * mm, 26 * mm, 24 * mm]
    # 10+28+52+22+22+26+24 = 184mm ≈ CONTENT_W (190mm). tweak last
    col_w[-1] = CONTENT_W - sum(col_w[:-1])
    header_row = [
        Paragraph("SN", s["th"]),
        Paragraph("Item Code", s["th"]),
        Paragraph("Description of Goods", s["th"]),
        Paragraph("HSN / GST", s["th"]),
        Paragraph("Quantity", s["th"]),
        Paragraph("Rate / UOM", s["th"]),
        Paragraph("Amount", s["th"]),
    ]
    data = [header_row]
    for idx, item in enumerate(items, start=1):
        code = ""
        if item.product_id and getattr(item, "product", None):
            code = item.product.product_code or ""
        qty = item.qty
        qty_s = f"{float(qty):.1f} {item.unit or 'PCS'}"
        remark = (getattr(item, "remark", "") or "").strip()
        if remark:
            desc = [
                Paragraph(_esc(item.product_name or ""), s["tdl"]),
                Paragraph(_esc(remark), s["tdnote"]),
            ]
        else:
            desc = Paragraph(_esc(item.product_name or ""), s["tdl"])
        data.append(
            [
                Paragraph(str(idx), s["td"]),
                Paragraph(_esc(code), s["td"]),
                desc,
                Paragraph(f"{item.hsn_code or '—'} / {float(item.gst or 0):g}%", s["td"]),
                Paragraph(qty_s, s["td"]),
                Paragraph(indian_money(item.rate), s["tdr"]),
                Paragraph(indian_money(item.amount), s["tdr"]),
            ]
        )
    while len(data) < 4:
        data.append([""] * 7)

    items_t = Table(data, colWidths=col_w, repeatRows=1)
    item_style = [
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            item_style.append(("BACKGROUND", (0, i), (-1, i), ROW_H))
    items_t.setStyle(TableStyle(item_style))
    story.append(items_t)
    story.append(Spacer(1, 3))

    ship_sum = [
        Paragraph("Shipment Summary", s["boxh"]),
        Spacer(1, 3),
        Paragraph(f"Bill / Ship From : {ship_from}", s["small"]),
        Paragraph(f"Mode of Shipment : {mode}", s["small"]),
        Paragraph(f"Shipment Courier : {courier}", s["small"]),
    ]
    extras = Decimal(invoice.freight_charges or 0) + Decimal(invoice.packing_charges or 0)
    discount = Decimal(invoice.discount or 0)
    total_label = "Invoice Amount" if is_tax else "Total Amount"
    tax_rows = [
        [Paragraph("Taxable Amount", s["val"]), Paragraph(indian_money(invoice.subtotal), s["tdr"])],
    ]
    if extras > 0:
        tax_rows.append(
            [Paragraph("Freight / Packing", s["val"]), Paragraph(indian_money(extras), s["tdr"])]
        )
    if discount > 0:
        pct = Decimal(getattr(invoice, "discount_percent", 0) or 0)
        if pct:
            label = f"Less : Discount ({float(pct):g}%)"
        else:
            label = "Less : Discount"
        tax_rows.append(
            [Paragraph(f"<b>{label}</b>", s["lab"]), Paragraph(f"<b>- {indian_money(discount)}</b>", s["tdr"])]
        )
    tax_rows.append([Paragraph(gst_label, s["val"]), Paragraph(indian_money(invoice.gst_amount), s["tdr"])])
    tax_rows.append(
        [Paragraph(f"<b>{total_label}</b>", s["lab"]), Paragraph(f"<b>{indian_money(invoice.grand_total)}</b>", s["tdr"])]
    )
    if is_tax:
        tax_rows.extend(
            [
                [Paragraph("Advance Received", s["val"]), Paragraph(indian_money(advance), s["tdr"])],
                [
                    Paragraph("<b>Balance Due</b>", s["lab"]),
                    Paragraph(f"<b>{indian_money(balance)}</b>", s["tdr"]),
                ],
            ]
        )
    tax_t = Table(tax_rows, colWidths=[48 * mm, 36 * mm])
    last_row = len(tax_rows) - 1
    tax_t.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, max(0, last_row - 1)), 0.3, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("BACKGROUND", (0, last_row), (-1, last_row), HEAD_BG),
            ]
        )
    )
    mid = Table([[ship_sum, tax_t]], colWidths=[half, half])
    mid.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("LINEAFTER", (0, 0), (0, 0), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(mid)
    story.append(Spacer(1, 3))
    story.append(_navy_bar(f"Grand Total Amount :  {indian_money(invoice.grand_total)}", s, size=11))
    story.append(Spacer(1, 3))
    story.append(
        Paragraph(
            f"<b>Amount In Words :</b>  INR {amount_in_words(invoice.grand_total)}",
            s["words"],
        )
    )
    note_text = (invoice.notes or "").strip()
    if note_text:
        story.append(Spacer(1, 2))
        story.append(Paragraph(f"<b>Note :</b>  {_esc(note_text)}", s["words"]))
    story.append(Spacer(1, 3))

    bank_inner = _kv(
        [
            ("Account Name :", company.bank_account_name or company.company_name),
            ("Account Number :", company.bank_account_number),
            ("Bank Name :", company.bank_name),
            ("IFSC Code :", company.bank_ifsc),
            ("Branch :", company.bank_branch),
        ],
        s,
        36 * mm,
        half - 36 * mm - 4 * mm,
    )
    scan = Table(
        [[Paragraph("Scan to Pay<br/>UPI / NEFT", ParagraphStyle("scan", fontName="Helvetica", fontSize=7, alignment=TA_CENTER, leading=10, textColor=MUTED))]],
        colWidths=[28 * mm],
        rowHeights=[16 * mm],
    )
    scan.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    bank_body = Table([[bank_inner], [scan]], colWidths=[half])
    bank_body.setStyle(TableStyle([("TOPPADDING", (0, 1), (-1, 1), 6), ("ALIGN", (0, 1), (-1, 1), "LEFT")]))

    pan = company.pan_number or (company.gst_number[2:12] if company.gst_number and len(company.gst_number) >= 12 else "—")
    company_inner = _kv(
        [
            ("Company Name :", f"{company.company_name} (Kila Energy Battery Division)"),
            ("GSTIN :", company.gst_number),
            ("PAN :", pan),
            ("MSME :", "Available on request"),
            ("Email :", company.email),
            ("Phone :", company.phone),
        ],
        s,
        34 * mm,
        half - 34 * mm - 4 * mm,
    )
    bc = Table(
        [[_box("Bank Details", bank_body, s, half), _box("Company Details", company_inner, s, half)]],
        colWidths=[half, half],
    )
    bc.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 1 * mm),
                ("LEFTPADDING", (1, 0), (1, 0), 1 * mm),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    story.append(bc)
    story.append(Spacer(1, 3))

    bullets = [Paragraph("Additional Information", s["boxh"]), Spacer(1, 3)]
    for line in ADDITIONAL_INFO:
        bullets.append(Paragraph(f"• {line}", s["small"]))
    sign = [
        Paragraph(f"For {company.company_name.upper()}", s["lab"]),
        Paragraph("Kila Energy Battery Division", s["small"]),
        Spacer(1, 16),
        Paragraph("Authorized Signatory", s["small"]),
    ]
    foot2 = Table([[bullets, sign]], colWidths=[half, half])
    foot2.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("LINEAFTER", (0, 0), (0, 0), 0.4, BORDER),
                ("VALIGN", (0, 0), (0, 0), "TOP"),
                ("VALIGN", (1, 0), (1, 0), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(foot2)
    story.append(Spacer(1, 3))
    note = Table(
        [
            [
                Paragraph("<b>New Customer Terms and Conditions</b>", s["smallb"]),
            ],
            [
                Paragraph(
                    "Before placing order, read Kila Energy Terms &amp; Conditions and item-specific specs. "
                    "B2B / trade orders only unless stated otherwise.",
                    s["small"],
                )
            ],
        ],
        colWidths=[CONTENT_W],
    )
    note.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(note)

    # Page 2
    story.append(NextPageTemplate("page2"))
    story.append(PageBreak())
    story.append(_header_block(company, s, page2=True))
    story.append(Spacer(1, 3))
    story.append(_navy_bar("General Terms and Conditions", s))
    story.append(Spacer(1, 8))
    terms_body = (invoice.terms or "").strip() or terms_text_for_kind(getattr(invoice, "pi_kind", "") or "battery")
    sections, footer_lines = parse_terms_text(terms_body)
    contact = f"Contact: {company.email or 'hrbp@kalpanatraders.com'} | {company.phone or '9289975453'}"
    footer_lines = list(footer_lines) + [contact]
    for title, items in sections:
        story.append(_section_title(title.replace("&", "&amp;"), s))
        story.append(Spacer(1, 2))
        story.append(_numbered_terms(items, s))
        story.append(Spacer(1, 8))
    story.append(Spacer(1, 2))
    agree = Table(
        [
            [Paragraph(line.replace("&", "&amp;"), s["foot"])]
            for line in footer_lines
        ],
        colWidths=[CONTENT_W],
    )
    agree.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(agree)

    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=ML,
        rightMargin=MR,
        topMargin=MT,
        bottomMargin=MB,
        title=f"{bar_title} {doc_no}",
        author=company.company_name,
    )
    frame = Frame(ML, MB, CONTENT_W, PAGE_H - MT - MB, id="normal", showBoundary=0)
    doc.addPageTemplates(
        [
            PageTemplate(id="page1", frames=frame),
            PageTemplate(id="page2", frames=frame),
        ]
    )

    def _canvas_factory(filename, **kwargs):
        return NumberedCanvas(
            filename,
            quote_no=doc_no,
            quote_date=qdate,
            no_label=foot_no,
            date_label=foot_date,
            **kwargs,
        )

    doc.build(story, canvasmaker=_canvas_factory)
    return buffer.getvalue()
