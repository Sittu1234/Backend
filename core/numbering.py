from django.db.models import Max
from django.utils import timezone


def next_code(model, field: str, prefix: str, width: int = 4) -> str:
    """Generate PREFIX-YYYY-0001 style codes. Safe for high-volume inserts with unique constraint."""
    year = timezone.now().year
    start = f"{prefix}-{year}-"
    last = (
        model.objects.filter(**{f"{field}__startswith": start})
        .aggregate(m=Max(field))
        .get("m")
    )
    seq = 1
    if last:
        try:
            seq = int(str(last).split("-")[-1]) + 1
        except (TypeError, ValueError):
            seq = 1
    return f"{prefix}-{year}-{seq:0{width}d}"
