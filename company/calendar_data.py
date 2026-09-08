from datetime import date

# Public company calendar defaults (seeded once).
CALENDAR_EVENTS = [
    {
        "title": "SPARS Dealer Meet — Noida",
        "kind": "event",
        "date": date(2026, 9, 15),
        "description": "Quarterly dealer meet for EV scooter, lithium and LED battery range.",
    },
    {
        "title": "Battery packing & QC training",
        "kind": "event",
        "date": date(2026, 9, 25),
        "description": "In-house training on pack assembly, BMS checks and dispatch quality.",
    },
    {
        "title": "Rahul Sharma — Birthday",
        "kind": "birthday",
        "date": date(2026, 9, 18),
        "description": "Wish our Sales Executive a happy birthday!",
    },
    {
        "title": "Priya Mehta — Birthday",
        "kind": "birthday",
        "date": date(2026, 10, 5),
        "description": "Accounts team birthday celebration.",
    },
    {
        "title": "Neha Verma — Birthday",
        "kind": "birthday",
        "date": date(2026, 11, 12),
        "description": "Team birthday — cake at office 4 PM.",
    },
    {
        "title": "Dussehra",
        "kind": "festival",
        "date": date(2026, 10, 20),
        "description": "Vijayadashami — office closed after noon puja.",
    },
    {
        "title": "Diwali",
        "kind": "festival",
        "date": date(2026, 11, 8),
        "end_date": date(2026, 11, 9),
        "description": "Deepavali & Govardhan — office closed. Happy Diwali from Kalpna Traders.",
    },
    {
        "title": "Guru Nanak Jayanti",
        "kind": "festival",
        "date": date(2026, 11, 24),
        "description": "Gurpurab — office closed.",
    },
    {
        "title": "Christmas",
        "kind": "festival",
        "date": date(2026, 12, 25),
        "description": "Christmas — office closed.",
    },
    {
        "title": "Gandhi Jayanti",
        "kind": "holiday",
        "date": date(2026, 10, 2),
        "description": "National holiday — office closed.",
    },
    {
        "title": "Christmas Eve half day",
        "kind": "holiday",
        "date": date(2026, 12, 24),
        "description": "Office closes at 2 PM.",
    },
    {
        "title": "New Year",
        "kind": "holiday",
        "date": date(2027, 1, 1),
        "description": "New Year holiday — office closed.",
    },
    {
        "title": "Republic Day",
        "kind": "holiday",
        "date": date(2027, 1, 26),
        "description": "National holiday — office closed.",
    },
    {
        "title": "Holi",
        "kind": "festival",
        "date": date(2027, 3, 3),
        "description": "Holi — office closed. Stay safe and colourful!",
    },
    {
        "title": "Year-end stock & accounts close",
        "kind": "event",
        "date": date(2026, 12, 31),
        "description": "Inventory count and books close with Accounts team.",
    },
]


DEFAULT_EVENTS = CALENDAR_EVENTS


def seed_calendar_events(EventModel):
    created = 0
    for row in CALENDAR_EVENTS:
        _, was_created = EventModel.objects.get_or_create(
            title=row["title"],
            date=row["date"],
            defaults={
                "kind": row["kind"],
                "end_date": row.get("end_date"),
                "description": row.get("description") or "",
                "is_public": True,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
    return created
