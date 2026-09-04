ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _two_digits(n: int) -> str:
    if n < 20:
        return ONES[n]
    return f"{TENS[n // 10]} {ONES[n % 10]}".strip()


def _three_digits(n: int) -> str:
    hundred = n // 100
    rest = n % 100
    if hundred and rest:
        return f"{ONES[hundred]} Hundred {_two_digits(rest)}"
    if hundred:
        return f"{ONES[hundred]} Hundred"
    return _two_digits(rest)


def indian_number(value) -> str:
    """Format 342000 as 3,42,000 (Indian grouping, no paise if whole)."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "0"
    negative = amount < 0
    amount = abs(amount)
    whole = int(round(amount)) if abs(amount - round(amount)) < 0.001 else None
    if whole is not None:
        s = str(whole)
        if len(s) <= 3:
            out = s
        else:
            last3, rest = s[-3:], s[:-3]
            groups = []
            while rest:
                groups.append(rest[-2:])
                rest = rest[:-2]
            out = ",".join(reversed(groups)) + "," + last3
        return ("-" if negative else "") + out
    formatted = f"{amount:,.2f}"
    return formatted


def indian_money(value) -> str:
    """Indian grouping with 2 decimal places: 1,22,996.00"""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "0.00"
    negative = amount < 0
    amount = abs(round(amount + 1e-9, 2))
    whole = int(amount)
    paise = int(round((amount - whole) * 100))
    s = str(whole)
    if len(s) <= 3:
        out = s
    else:
        last3, rest = s[-3:], s[:-3]
        groups = []
        while rest:
            groups.append(rest[-2:])
            rest = rest[:-2]
        out = ",".join(reversed(groups)) + "," + last3
    return ("-" if negative else "") + f"{out}.{paise:02d}"


def amount_in_words(value, include_rupees: bool = True) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "Zero Only" if not include_rupees else "Zero Rupees Only"

    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))

    if rupees == 0:
        words = "Zero"
    else:
        crore = rupees // 10000000
        lakh = (rupees % 10000000) // 100000
        thousand = (rupees % 100000) // 1000
        remainder = rupees % 1000
        parts = []
        if crore:
            parts.append(f"{_three_digits(crore)} Crore")
        if lakh:
            parts.append(f"{_three_digits(lakh)} Lakh")
        if thousand:
            parts.append(f"{_three_digits(thousand)} Thousand")
        if remainder:
            parts.append(_three_digits(remainder))
        words = " ".join(parts)

    if include_rupees:
        result = f"{words} Rupees"
        if paise:
            result += f" and {_two_digits(paise)} Paise"
        return result + " Only"
    if paise:
        return f"{words} and {_two_digits(paise)} Paise Only"
    return f"{words} Only"
