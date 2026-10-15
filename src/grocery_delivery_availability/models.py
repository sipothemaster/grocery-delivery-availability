"""Stable public result model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class DeliveryState(StrEnum):
    YES = "Yes"
    NO = "No"
    UNKNOWN = "Unknown"


@dataclass(slots=True)
class Observation:
    postcode: str
    retailer: str
    deliverable: DeliveryState
    reason: str
    checked_at_utc: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    query_started_at_utc: str = ""
    response_completed_at_utc: str = ""
    http_status: int | None = None
    endpoint: str = ""
    returned_postcode: str = ""
    address_valid: str = ""
    delivery_coverage: str = ""
    collection_coverage: str = ""
    current_slot: str = ""
    first_slot_starts_at_utc: str = ""
    first_slot_ends_at_utc: str = ""
    first_slot_service_type: str = ""
    wait_minutes: float | None = None
    fast_delivery: str = ""
    scheduled_delivery: str = ""
    brands: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def unknown(
        cls,
        postcode: str,
        retailer: str,
        reason: str,
        **kwargs: Any,
    ) -> Observation:
        return cls(postcode, retailer, DeliveryState.UNKNOWN, reason, **kwargs)

    def as_csv_row(self) -> dict[str, object]:
        return {
            "postcode": self.postcode,
            "retailer": self.retailer,
            "deliverable": self.deliverable.value,
            "reason": self.reason,
            "query_started_at_utc": self.query_started_at_utc,
            "response_completed_at_utc": self.response_completed_at_utc,
            "http_status": "" if self.http_status is None else self.http_status,
            "endpoint": self.endpoint,
            "returned_postcode": self.returned_postcode,
            "address_valid": self.address_valid,
            "delivery_coverage": self.delivery_coverage,
            "collection_coverage": self.collection_coverage,
            "current_slot": self.current_slot,
            "first_slot_starts_at_utc": self.first_slot_starts_at_utc,
            "first_slot_ends_at_utc": self.first_slot_ends_at_utc,
            "first_slot_service_type": self.first_slot_service_type,
            "wait_minutes": "" if self.wait_minutes is None else self.wait_minutes,
            "fast_delivery": self.fast_delivery,
            "scheduled_delivery": self.scheduled_delivery,
            "brands": " | ".join(self.brands),
            "details_json": json.dumps(
                self.details, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
            "checked_at_utc": self.checked_at_utc,
        }


CSV_FIELDS = tuple(
    Observation(
        postcode="",
        retailer="",
        deliverable=DeliveryState.UNKNOWN,
        reason="",
    ).as_csv_row()
)
