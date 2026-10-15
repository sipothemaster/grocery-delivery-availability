import json

from grocery_delivery_availability.io import observation_from_row
from grocery_delivery_availability.models import DeliveryState, Observation


def test_observation_csv_round_trip() -> None:
    original = Observation(
        "E1 6HQ",
        "Example",
        DeliveryState.YES,
        "Explicit evidence.",
        returned_postcode="E1 6HQ",
        collection_coverage="No",
        first_slot_starts_at_utc="2026-10-15T10:00:00+00:00",
        first_slot_ends_at_utc="2026-10-15T11:00:00+00:00",
        first_slot_service_type="delivery",
        wait_minutes=42.5,
        brands=("Amazon Fresh", "Example Brand"),
        details={"count": 3},
    )
    row = {key: str(value) for key, value in original.as_csv_row().items()}
    restored = observation_from_row(row)
    assert restored.deliverable is DeliveryState.YES
    assert restored.brands == ("Amazon Fresh", "Example Brand")
    assert restored.returned_postcode == "E1 6HQ"
    assert restored.collection_coverage == "No"
    assert restored.first_slot_service_type == "delivery"
    assert restored.wait_minutes == 42.5
    assert json.loads(restored.as_csv_row()["details_json"]) == {"count": 3}


def test_unknown_factory_preserves_three_state_model() -> None:
    result = Observation.unknown("E1 6HQ", "Example", "Technical failure")
    assert result.deliverable is DeliveryState.UNKNOWN
