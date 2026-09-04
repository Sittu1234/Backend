from decimal import Decimal

from .models import Category, Product

CATEGORIES = [
    ("EV Scooter", "Electric scooters for dealer supply"),
    ("Lithium Battery", "Lithium-ion packs for EV and inverter"),
    ("LED Battery", "LED inverter, SMF and tubular batteries"),
]

# name, code, category, hsn, unit, gst, price, description
TODAY_PRICE_LIST = [
    (
        "SPARS EV Scooter 60V 28Ah",
        "KT-EV-60-28",
        "EV Scooter",
        "871160",
        "NOS",
        5,
        "62490",
        "60V electric scooter with 28Ah battery, city range model.",
    ),
    (
        "SPARS EV Scooter 60V 32Ah",
        "KT-EV-60-32",
        "EV Scooter",
        "871160",
        "NOS",
        5,
        "68990",
        "60V electric scooter with 32Ah lithium pack.",
    ),
    (
        "SPARS EV Scooter 72V 40Ah",
        "KT-EV-72-40",
        "EV Scooter",
        "871160",
        "NOS",
        5,
        "84990",
        "72V high-range electric scooter with 40Ah lithium pack.",
    ),
    (
        "SPARS EV Cargo Scooter 60V",
        "KT-EV-CG-60",
        "EV Scooter",
        "871160",
        "NOS",
        5,
        "79990",
        "Cargo / loading EV scooter for last-mile delivery.",
    ),
    (
        "Lithium Battery 48V 20Ah",
        "KT-LI-48-20",
        "Lithium Battery",
        "850760",
        "NOS",
        18,
        "14500",
        "48V 20Ah lithium pack for e-scooter / e-rickshaw.",
    ),
    (
        "Lithium Battery 60V 24Ah",
        "KT-LI-60-24",
        "Lithium Battery",
        "850760",
        "NOS",
        18,
        "18500",
        "60V 24Ah lithium battery, BMS protected.",
    ),
    (
        "Lithium Battery 60V 30Ah",
        "KT-LI-60-30",
        "Lithium Battery",
        "850760",
        "NOS",
        18,
        "22500",
        "60V 30Ah lithium battery for EV scooter.",
    ),
    (
        "Lithium Battery 60V 36Ah",
        "KT-LI-60-36",
        "Lithium Battery",
        "850760",
        "NOS",
        18,
        "26800",
        "60V 36Ah lithium battery, longer range pack.",
    ),
    (
        "Lithium Battery 72V 40Ah",
        "KT-LI-72-40",
        "Lithium Battery",
        "850760",
        "NOS",
        18,
        "34500",
        "72V 40Ah lithium battery for high-power EV.",
    ),
    (
        "Lithium Inverter Battery 12.8V 100Ah",
        "KT-LI-INV-100",
        "Lithium Battery",
        "850760",
        "NOS",
        18,
        "28900",
        "12.8V 100Ah lithium battery for home / LED inverter.",
    ),
    (
        "LED Emergency Battery 12V 7Ah SMF",
        "KT-LED-7AH",
        "LED Battery",
        "850710",
        "NOS",
        18,
        "950",
        "12V 7Ah SMF battery for LED emergency lights.",
    ),
    (
        "LED Inverter Battery 12V 26Ah SMF",
        "KT-LED-26AH",
        "LED Battery",
        "850710",
        "NOS",
        18,
        "2850",
        "12V 26Ah SMF battery for LED inverter systems.",
    ),
    (
        "LED Tubular Battery 150Ah",
        "KT-LED-TB-150",
        "LED Battery",
        "850710",
        "NOS",
        18,
        "13500",
        "150Ah tubular battery for LED inverter / home backup.",
    ),
    (
        "LED Tubular Battery 180Ah",
        "KT-LED-TB-180",
        "LED Battery",
        "850710",
        "NOS",
        18,
        "15800",
        "180Ah tubular battery for LED inverter.",
    ),
    (
        "LED Tubular Battery 200Ah",
        "KT-LED-TB-200",
        "LED Battery",
        "850710",
        "NOS",
        18,
        "17800",
        "200Ah tubular battery, heavy backup.",
    ),
]


def sync_today_price_list():
    cats = {}
    for name, desc in CATEGORIES:
        obj, _ = Category.objects.get_or_create(name=name, defaults={"description": desc})
        if not obj.description:
            obj.description = desc
            obj.save(update_fields=["description"])
        cats[name] = obj

    created = 0
    updated = 0
    for name, code, cat, hsn, unit, gst, price, desc in TODAY_PRICE_LIST:
        obj, was_created = Product.objects.update_or_create(
            product_code=code,
            defaults={
                "product_name": name,
                "category": cats[cat],
                "hsn_code": hsn,
                "unit": unit,
                "gst": Decimal(str(gst)),
                "price": Decimal(price),
                "description": desc,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "total": created + updated}
