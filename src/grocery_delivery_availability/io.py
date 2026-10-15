"""Small, dependency-free CSV input and atomic output helpers."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path

from .models import CSV_FIELDS, Observation
from .postcodes import normalize_postcode


def read_postcodes(path: Path, column: str) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header: {path}")
        names = {name.casefold(): name for name in reader.fieldnames}
        actual = names.get(column.casefold())
        if actual is None:
            raise ValueError(f"CSV file {path} has no column named {column!r}")
        return [
            normalize_postcode(row.get(actual, ""))
            for row in reader
            if str(row.get(actual, "")).strip()
        ]


def read_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {
            normalize_postcode(row.get("postcode", "")): row
            for row in csv.DictReader(handle)
            if row.get("postcode")
        }


def write_observations(path: Path, observations: Iterable[Observation]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(item.as_csv_row() for item in observations)
    temporary.replace(path)


def observation_from_row(row: dict[str, str]) -> Observation:
    from .models import DeliveryState

    try:
        details = json.loads(row.get("details_json", "{}") or "{}")
    except json.JSONDecodeError:
        details = {"unparsed_details_json": row.get("details_json", "")}
    brands = tuple(part.strip() for part in row.get("brands", "").split("|") if part.strip())
    status = row.get("http_status", "").strip()
    wait_minutes = row.get("wait_minutes", "").strip()
    try:
        parsed_wait_minutes = float(wait_minutes) if wait_minutes else None
    except ValueError:
        parsed_wait_minutes = None
    return Observation(
        postcode=normalize_postcode(row.get("postcode", "")),
        retailer=row.get("retailer", ""),
        deliverable=DeliveryState(row.get("deliverable", "Unknown")),
        reason=row.get("reason", ""),
        checked_at_utc=row.get("checked_at_utc", ""),
        query_started_at_utc=row.get("query_started_at_utc", ""),
        response_completed_at_utc=row.get("response_completed_at_utc", ""),
        http_status=int(status) if status.isdigit() else None,
        endpoint=row.get("endpoint", ""),
        returned_postcode=row.get("returned_postcode", ""),
        address_valid=row.get("address_valid", ""),
        delivery_coverage=row.get("delivery_coverage", ""),
        collection_coverage=row.get("collection_coverage", ""),
        current_slot=row.get("current_slot", ""),
        first_slot_starts_at_utc=row.get("first_slot_starts_at_utc", ""),
        first_slot_ends_at_utc=row.get("first_slot_ends_at_utc", ""),
        first_slot_service_type=row.get("first_slot_service_type", ""),
        wait_minutes=parsed_wait_minutes,
        fast_delivery=row.get("fast_delivery", ""),
        scheduled_delivery=row.get("scheduled_delivery", ""),
        brands=brands,
        details=details,
    )
