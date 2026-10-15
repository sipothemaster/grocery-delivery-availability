"""UK postcode normalization and conservative syntax validation."""

from __future__ import annotations

import re

_POSTCODE = re.compile(r"^(?:GIR 0AA|[A-Z]{1,2}[0-9][A-Z0-9]? [0-9][A-Z]{2})$")


def normalize_postcode(value: object) -> str:
    """Return an uppercase postcode with one space before the inward code."""

    compact = re.sub(r"\s+", "", str(value or "")).upper()
    if len(compact) < 4:
        return compact
    return f"{compact[:-3]} {compact[-3:]}"


def is_valid_postcode(value: object) -> bool:
    """Check basic UK unit-postcode syntax without claiming current validity."""

    return bool(_POSTCODE.fullmatch(normalize_postcode(value)))
