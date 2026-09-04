TERMS_SALE = [
    "This quotation and any resulting sale are governed by Kila Energy (Kalpna Traders) standard terms unless a separate written agreement is signed.",
    "Unless expressly stated on the quotation or product datasheet, lithium battery products carry manufacturing-defect warranty only for the period mentioned on the invoice. No implied warranty of fitness for a particular purpose.",
    "All prices are Ex-Works (EXW) from our Noida facility. Freight, loading, handling, insurance, octroi and taxes (other than GST shown) are borne by the buyer.",
    "Kalpna Traders / Kila Energy is not responsible for loss, damage, delay, theft or shortage after goods are handed over to the transporter or courier.",
    "Transit insurance is not included unless specifically requested, quoted and confirmed in writing before dispatch.",
    "Claims for shortage or transit damage must be reported within 24 hours of delivery with a continuous, unedited unboxing video from sealed outer packaging.",
    "Product specifications, BMS configuration, cell grade, prices and availability are subject to change without prior notice until order is confirmed in writing.",
    "Confirmed orders cannot be cancelled or modified without written consent. Advance payments are non-refundable once production or procurement has started.",
]

TERMS_BATTERY = [
    "Buyer is responsible for correct selection of voltage, capacity (Ah), BMS type and connector for the intended application (EV, inverter, solar, UPS, OEM).",
    "Custom battery packs are built strictly as per the signed specification sheet. Changes after confirmation may attract revision charges and lead-time extension.",
    "Payment terms: 100% advance before dispatch unless credit is approved in writing. Cheque / NEFT / RTGS / UPI as per bank details on quotation.",
    "GST will be charged as applicable under HSN 8507. Buyer must provide valid GSTIN for tax invoice where applicable.",
    "Installation, commissioning and load testing at buyer premises are buyer's responsibility unless separately quoted.",
    "Reverse polarity, over-charge, over-discharge, physical damage or unauthorized repair voids warranty.",
    "Export or resale of products is buyer's responsibility for compliance with local regulations and transport rules for lithium batteries.",
    "Disputes subject to jurisdiction of courts at Gautam Buddha Nagar (Greater Noida), Uttar Pradesh, India.",
]

TERMS_EV_SCOOTER = [
    "Buyer must confirm model, motor wattage, battery voltage/capacity, charger type, colour and any RTO / registration requirement before order confirmation.",
    "Range, speed, charging time and performance vary with rider weight, terrain, tyre pressure, load and battery condition. Figures on this quotation are as per manufacturer datasheet.",
    "Registration, insurance, number plate, hypothecation and RTO charges are extra unless specifically included in this quotation.",
    "Payment terms: 100% advance before dispatch unless credit is approved in writing. Cheque / NEFT / RTGS / UPI as per bank details on quotation.",
    "GST will be charged as applicable under the HSN mentioned on this quotation. Buyer must provide valid GSTIN for tax invoice.",
    "Warranty on scooter, motor, controller and charger follows OEM / manufacturer policy on the invoice or warranty card. Accident, water ingress, overload or unauthorized repair voids warranty.",
    "Pre-delivery inspection at our warehouse is available on request. After handover to transporter, claims for transit damage must be raised within 24 hours with unboxing video.",
    "Disputes subject to jurisdiction of courts at Gautam Buddha Nagar (Greater Noida), Uttar Pradesh, India.",
]

# Backward compatible alias used by older PDF code
TERMS_PRODUCT = TERMS_BATTERY

ADDITIONAL_INFO = [
    "Quotation validity: 7 calendar days from quotation date.",
    "Delivery: 7–15 working days after payment confirmation & spec approval.",
    "Custom Li-ion / LiFePO4 packs require signed specification sheet.",
    "BMS, cell grade and warranty as per confirmed product datasheet.",
]

PI_KINDS = (
    ("battery", "Battery"),
    ("ev_scooter", "EV Scooter"),
    ("both", "Both"),
)

PI_KIND_LABELS = {
    "battery": "Lithium Battery",
    "ev_scooter": "EV Scooter",
    "both": "Battery + EV Scooter",
}

FOOTER_LINES = [
    "By accepting this quotation or making advance payment, the buyer agrees to the above terms.",
    "Subject to jurisdiction: Gautam Buddha Nagar (Greater Noida), Uttar Pradesh.",
]


def terms_sections_for_kind(kind: str):
    kind = (kind or "battery").strip().lower()
    sections = [("Terms & Conditions of Sale", TERMS_SALE)]
    if kind in ("battery", "both", ""):
        sections.append(("Battery Product & B2B Conditions", TERMS_BATTERY))
    if kind in ("ev_scooter", "both"):
        sections.append(("EV Scooter Conditions", TERMS_EV_SCOOTER))
    if kind not in ("battery", "ev_scooter", "both", ""):
        sections.append(("Battery Product & B2B Conditions", TERMS_BATTERY))
    return sections


def terms_text_for_kind(kind: str) -> str:
    lines = []
    for title, items in terms_sections_for_kind(kind):
        if lines:
            lines.append("")
        lines.append(title)
        lines += [f"{i}. {t}" for i, t in enumerate(items, 1)]
    lines += ["", *FOOTER_LINES]
    return "\n".join(lines)


def default_terms_text() -> str:
    return terms_text_for_kind("both")


def parse_terms_text(text: str):
    """Turn saved terms into titled sections for the PDF."""
    import re

    sections = []
    title = None
    items = []
    footer = []
    numbered = re.compile(r"^\d+[.)]\s+(.*)$")

    def flush():
        nonlocal title, items
        if title or items:
            sections.append((title or "Terms & Conditions", items))
        title = None
        items = []

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("by accepting") or low.startswith("subject to jurisdiction"):
            footer.append(line)
            continue
        match = numbered.match(line)
        if match:
            items.append(match.group(1).strip())
            continue
        flush()
        title = line
        items = []
    flush()
    if not sections:
        sections = terms_sections_for_kind("battery")
    if not footer:
        footer = list(FOOTER_LINES)
    return sections, footer
