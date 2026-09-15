from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from company.terms import PI_KIND_LABELS
from core.utils import amount_in_words, indian_money

BORDER = colors.HexColor("#9AA4B2")
HEAD_BG = colors.HexColor("#EEF1F4")
LINE = colors.HexColor("#E5E7EB")


def _esc(text) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _scope_for_kind(kind: str):
    kind = (kind or "battery").strip().lower()
    battery = [
        "Lithium-ion and LiFePO4 battery packs for EV, inverter, solar and OEM use.",
        "Pack voltage, capacity (Ah), BMS type and connectors as per confirmed specification.",
        "LED / inverter batteries with GST-ready HSN billing for dealer and B2B orders.",
    ]
    scooter = [
        "EV scooter models with motor, controller, charger and colour as confirmed on this quotation.",
        "Range and performance figures follow manufacturer datasheet and actual riding conditions.",
        "Registration, insurance and RTO charges extra unless specifically included.",
    ]
    if kind == "ev_scooter":
        return scooter
    if kind == "both":
        return battery + scooter
    return battery


def build_proposal_story(invoice, company, s, *, navy_bar, section_title, content_w):
    """Extra PDF pages: business proposal, only when include_proposal is on."""
    cust = invoice.customer
    kind_label = PI_KIND_LABELS.get(getattr(invoice, "pi_kind", "") or "", "Lithium Battery")
    doc_no = invoice.pi_number
    qdate = invoice.pi_date.strftime("%d-%m-%Y") if invoice.pi_date else "—"
    valid = invoice.valid_till.strftime("%d-%m-%Y") if invoice.valid_till else "—"
    party = cust.company_name or cust.customer_name or "Valued Partner"
    city = ", ".join(p for p in [cust.city, cust.state] if p) or "—"
    phone = company.phone or "9289975453"
    email = company.email or "hrbp@kalpanatraders.com"
    addr = " ".join(p for p in [company.address, company.city, company.state, company.pincode] if p) or "Noida (Sector-63A), Uttar Pradesh"

    story = [
        navy_bar("BUSINESS PROPOSAL", s, size=14),
        Spacer(1, 6),
        Paragraph(
            f"Prepared for <b>{_esc(party)}</b> along with quotation <b>{_esc(doc_no)}</b>.",
            s["words"],
        ),
        Spacer(1, 6),
    ]

    intro = Table(
        [
            [Paragraph("Customer", s["lab"]), Paragraph(_esc(cust.customer_name), s["val"])],
            [Paragraph("Company", s["lab"]), Paragraph(_esc(cust.company_name or "—"), s["val"])],
            [Paragraph("Location", s["lab"]), Paragraph(_esc(city), s["val"])],
            [Paragraph("Quotation No.", s["lab"]), Paragraph(_esc(doc_no), s["val"])],
            [Paragraph("Date / Validity", s["lab"]), Paragraph(f"{qdate}  ·  Valid till {valid}", s["val"])],
            [Paragraph("Proposal for", s["lab"]), Paragraph(_esc(kind_label), s["val"])],
        ],
        colWidths=[42 * mm, content_w - 42 * mm],
    )
    intro.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, LINE),
                ("BACKGROUND", (0, 0), (0, -1), HEAD_BG),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(intro)
    story.append(Spacer(1, 10))

    story.append(section_title("1. Introduction", s))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"{_esc(company.company_name)} (Kila Energy Battery Division) is pleased to submit this "
            f"business proposal with the attached quotation for <b>{_esc(kind_label)}</b> supply. "
            "This document covers who we are, what we propose to supply, and how to confirm the order.",
            s["term"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(section_title("2. About the company", s))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"{_esc(company.company_name)} is a Noida-based trading house for EV scooters, lithium battery packs "
            f"and LED / inverter batteries. GSTIN: {_esc(company.gst_number or '—')}. "
            f"Office: {_esc(addr)}. We issue GST-ready quotations and support dealers on specification, "
            "dispatch and after-sales as per the confirmed product datasheet.",
            s["term"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(section_title("3. Proposed supply", s))
    story.append(Spacer(1, 4))
    for line in _scope_for_kind(getattr(invoice, "pi_kind", "") or "battery"):
        story.append(Paragraph(f"• {_esc(line)}", s["term"]))
        story.append(Spacer(1, 2))
    story.append(
        Paragraph(
            "Item-wise rates, HSN, GST and quantities are given on the quotation page of this PDF.",
            s["term"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(section_title("4. Commercial snapshot", s))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"<b>Quoted value:</b> {indian_money(invoice.grand_total)} "
            f"(INR {amount_in_words(invoice.grand_total)}). "
            f"Validity: {valid}. Payment: as printed on the quotation. "
            "Prices are Ex-Works Noida unless otherwise stated.",
            s["term"],
        )
    )
    story.append(Spacer(1, 8))

    story.append(section_title("5. Why partner with us", s))
    story.append(Spacer(1, 4))
    for line in [
        "Single Noida desk for EV, lithium packs and LED batteries.",
        "GST invoices, HSN-wise billing and dealer-ready quotations.",
        "Custom packs only against a signed specification sheet.",
        "Dispatch typically 7–15 working days after payment and spec approval.",
    ]:
        story.append(Paragraph(f"• {_esc(line)}", s["term"]))
        story.append(Spacer(1, 2))

    extra = (getattr(invoice, "proposal_note", "") or "").strip()
    if extra:
        story.append(Spacer(1, 6))
        story.append(section_title("6. Additional proposal note", s))
        story.append(Spacer(1, 4))
        story.append(Paragraph(_esc(extra).replace("\n", "<br/>"), s["term"]))

    story.append(Spacer(1, 8))
    story.append(section_title("Next steps", s))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "1. Confirm this quotation and any specification / colour / BMS details.<br/>"
            "2. Share advance as per payment terms on the quotation.<br/>"
            "3. We schedule production / allotment and dispatch from Noida.<br/>"
            f"Contact: {_esc(email)} | {_esc(phone)}",
            s["term"],
        )
    )
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            f"We look forward to your confirmation.<br/><b>{_esc(company.company_name)}</b> · Kila Energy Battery Division",
            s["words"],
        )
    )
    return story
