import base64
import json
from datetime import UTC, datetime
from pathlib import Path

from grocery_delivery_availability.models import DeliveryState
from grocery_delivery_availability.retailers import coop
from grocery_delivery_availability.retailers.coop import (
    CoopChecker,
    decode_slot_id,
    first_delivery_slot,
    observation_from_coop_response,
)


class _Body:
    def inner_text(self, *, timeout: int) -> str:
        assert timeout == 5_000
        return "Co-op groceries"


class _Page:
    url = "https://shop.coop.co.uk/"

    def __init__(self, result: dict[str, object]) -> None:
        self.result = result

    def wait_for_timeout(self, milliseconds: int) -> None:
        assert milliseconds == 2_000

    def locator(self, selector: str) -> _Body:
        assert selector == "body"
        return _Body()

    def content(self) -> str:
        return '<script src="/_next/static/example.js"></script>'

    def evaluate(self, _script: str, argument: dict[str, str]) -> dict[str, object]:
        assert argument == {"postcode": "E1 6HQ"}
        return self.result


class _Browser:
    def __init__(self, result: dict[str, object]) -> None:
        self.page = _Page(result)
        self.closed = False

    def close(self) -> None:
        self.closed = True


def encoded_slot(service_type: str = "delivery") -> str:
    value = (
        "2026-07-29T23:00:00.000Z|2026-07-30T00:00:00.000Z|"
        f"7290|2.99|{service_type}"
    )
    return base64.b64encode(value.encode()).decode()


def test_slot_id_supplies_authoritative_utc_instants() -> None:
    decoded = decode_slot_id(encoded_slot())

    assert decoded is not None
    assert decoded["schema_recognised"] is True
    assert decoded["starts_at_utc"] == "2026-07-29T23:00:00+00:00"
    assert decoded["ends_at_utc"] == "2026-07-30T00:00:00+00:00"
    assert decoded["service_type"] == "delivery"


def test_display_date_is_not_used_to_construct_midnight_slot() -> None:
    payload = {
        "firstSlot": {
            "id": encoded_slot(),
            "date": "2026-07-29",
            "startsAt": "00:00",
            "endsAt": "01:00",
        }
    }

    slot = first_delivery_slot(payload, datetime(2026, 7, 29, 21, 15, tzinfo=UTC))

    assert slot is not None
    assert slot["starts_at_uk"] == "2026-07-30T00:00:00+01:00"
    assert slot["ends_at_uk"] == "2026-07-30T01:00:00+01:00"
    assert slot["wait_minutes"] == 105.0
    assert slot["display_date"] == "2026-07-29"


def test_collection_first_slot_is_not_treated_as_delivery() -> None:
    payload = {"firstSlot": {"id": encoded_slot("collection")}}

    slot = first_delivery_slot(payload, datetime(2026, 7, 29, 21, 15, tzinfo=UTC))

    assert slot is not None
    assert slot["service_type"] == "collection"
    assert slot["usable_delivery_time"] is False


def test_postcode_matched_response_records_coverage_and_delivery_time() -> None:
    started = datetime(2026, 7, 29, 21, 15, tzinfo=UTC)
    completed = datetime(2026, 7, 29, 21, 15, 1, tzinfo=UTC)
    payload = {
        "formattedPostcode": "E1 6HQ",
        "name": "Synthetic Co-op",
        "storeAvailability": ["delivery", "collection"],
        "slotAvailability": ["delivery"],
        "firstSlot": {"id": encoded_slot()},
    }

    result = observation_from_coop_response(
        "E1 6HQ",
        status=200,
        payload=payload,
        endpoint="https://shop.coop.co.uk/api/store/set?postcode=E1%206HQ",
        query_started=started,
        response_completed=completed,
    )

    assert result.deliverable is DeliveryState.YES
    assert result.returned_postcode == "E1 6HQ"
    assert result.delivery_coverage == "Yes"
    assert result.collection_coverage == "Yes"
    assert result.current_slot == "Yes"
    assert result.first_slot_service_type == "delivery"
    assert result.first_slot_starts_at_utc == "2026-07-29T23:00:00+00:00"
    assert result.first_slot_ends_at_utc == "2026-07-30T00:00:00+00:00"
    assert result.wait_minutes == 105.0
    assert result.query_started_at_utc == "2026-07-29T21:15:00+00:00"
    assert result.response_completed_at_utc == "2026-07-29T21:15:01+00:00"


def test_missing_or_mismatched_returned_postcode_is_unknown() -> None:
    started = datetime(2026, 7, 29, 21, 15, tzinfo=UTC)
    completed = datetime(2026, 7, 29, 21, 15, 1, tzinfo=UTC)
    common = {
        "status": 200,
        "endpoint": "https://shop.coop.co.uk/api/store/set",
        "query_started": started,
        "response_completed": completed,
    }

    missing = observation_from_coop_response(
        "E1 6HQ",
        payload={"storeAvailability": ["delivery"]},
        **common,
    )
    mismatch = observation_from_coop_response(
        "E1 6HQ",
        payload={
            "formattedPostcode": "LS2 9JT",
            "storeAvailability": ["delivery"],
        },
        **common,
    )

    assert missing.deliverable is DeliveryState.UNKNOWN
    assert mismatch.deliverable is DeliveryState.UNKNOWN
    assert mismatch.returned_postcode == "LS2 9JT"


def test_checker_uses_page_session_and_writes_business_evidence(
    monkeypatch, tmp_path: Path
) -> None:
    payload = {
        "formattedPostcode": "E1 6HQ",
        "storeAvailability": ["delivery"],
        "slotAvailability": ["delivery"],
        "firstSlot": {"id": encoded_slot()},
    }
    browser = _Browser(
        {
            "status": 200,
            "url": "https://shop.coop.co.uk/api/store/set?postcode=E1%206HQ",
            "text": json.dumps(payload),
            "error": None,
        }
    )
    monkeypatch.setattr(coop, "BrowserSession", lambda **_kwargs: browser)
    checker = CoopChecker(
        cdp_url="http://127.0.0.1:9222",
        evidence_dir=tmp_path / "evidence",
    )

    result = checker.check("E1 6HQ")
    checker.close()

    assert result.deliverable is DeliveryState.YES
    assert result.returned_postcode == "E1 6HQ"
    assert result.first_slot_service_type == "delivery"
    assert checker.stop_reason is None
    assert browser.closed
    evidence_files = list((tmp_path / "evidence").glob("*.json"))
    assert len(evidence_files) == 1
    evidence = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert evidence["business_response"] == payload


def test_checker_requests_checkpointed_stop_after_403(monkeypatch) -> None:
    browser = _Browser(
        {
            "status": 403,
            "url": "https://shop.coop.co.uk/api/store/set?postcode=E1%206HQ",
            "text": "Access denied",
            "error": None,
        }
    )
    monkeypatch.setattr(coop, "BrowserSession", lambda **_kwargs: browser)
    checker = CoopChecker(cdp_url="http://127.0.0.1:9222")

    result = checker.check("E1 6HQ")
    checker.close()

    assert result.deliverable is DeliveryState.UNKNOWN
    assert result.http_status == 403
    assert checker.stop_reason == "Co-op access-control stop after HTTP 403."
