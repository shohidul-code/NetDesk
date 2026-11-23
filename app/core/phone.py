"""Bangladeshi mobile numbers, validated and stored in E.164 form (+8801XXXXXXXXX)."""

import re
from typing import Annotated

from pydantic import AfterValidator

# 01 + operator digit 3-9 + 8 more digits = 11 national digits.
_NATIONAL = re.compile(r"^01[3-9]\d{8}$")


def normalize_bd_phone(raw: str) -> str:
    """Accept 01XXXXXXXXX, 8801XXXXXXXXX or +8801XXXXXXXXX, with spaces or dashes."""
    digits = re.sub(r"[\s\-()]", "", raw)
    if digits.startswith("+880"):
        digits = digits[4:]
    elif digits.startswith("880"):
        digits = digits[3:]
    if digits.startswith("1"):
        digits = "0" + digits
    if not _NATIONAL.match(digits):
        raise ValueError("Enter a Bangladeshi mobile number, e.g. 01712345678.")
    return "+88" + digits


# Use as a field type: `phone: BDPhone`. Invalid input becomes a 422 naming the field.
BDPhone = Annotated[str, AfterValidator(normalize_bd_phone)]
