"""Co-op coverage and delivery-slot evidence from a first-party browser session."""

from __future__ import annotations

import base64
import calendar
import json
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from ..browser import BrowserSession
from ..models import DeliveryState, Observation
from ..postcodes import normalize_postcode

HOST = "https://shop.coop.co.uk"
WELCOME_URL = HOST + "/welcome"
ENDPOINT = HOST + "/api/store/set"


def iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def uk_local(value: datetime) -> datetime:
    """Convert an aware datetime using the UK's current DST rule."""

    value = value.astimezone(UTC)

    def last_sunday(year: int, month: int) -> int:
        return max(
            day
            for day in range(1, calendar.monthrange(year, month)[1] + 1)
            if datetime(year, month, day).weekday() == calendar.SUNDAY
        )

    starts = datetime(value.year, 3, last_sunday(value.year, 3), 1, tzinfo=UTC)
    ends = datetime(value.year, 10, last_sunday(value.year, 10), 1, tzinfo=UTC)
    local_zone = timezone(timedelta(hours=1), "BST") if starts <= value < ends else UTC
    return value.astimezone(local_zone)


def decode_slot_id(value: object) -> dict[str, Any] | None:
    """Decode the observed pipe-delimited Co-op slot identifier."""

    if not isinstance(value, str) or not value:
        return None
    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(padded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    parts = decoded.split("|")
    if len(parts) < 5:
        return {"raw": decoded, "schema_recognised": False}
    try:
        starts_at = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
        ends_at = datetime.fromisoformat(parts[1].replace("Z", "+00:00"))
    except ValueError:
        return {"raw": decoded, "schema_recognised": False}
    if starts_at.tzinfo is None or ends_at.tzinfo is None:
        return {"raw": decoded, "schema_recognised": False}
    return {
        "raw": decoded,
        "schema_recognised": True,
        "starts_at_utc": iso_utc(starts_at),
        "ends_at_utc": iso_utc(ends_at),
        "store_id": parts[2],
        "charge": parts[3],
        "service_type": parts[4],
    }


def first_delivery_slot(payload: Any, query_started: datetime) -> dict[str, Any] | None:
    """Return decoded first-slot evidence without treating collection as delivery."""

    if not isinstance(payload, dict):
        return None
    first_slot = payload.get("firstSlot")
    if not isinstance(first_slot, dict):
        return None
    decoded = decode_slot_id(first_slot.get("id"))
    service_type = first_slot.get("serviceType") or first_slot.get("type")
    if decoded and decoded.get("schema_recognised"):
        service_type = decoded["service_type"]
    result: dict[str, Any] = {
        "service_type": service_type,
        "slot_id_decoded": decoded,
        "usable_delivery_time": False,
        "display_date": first_slot.get("date"),
        "display_starts_at": first_slot.get("startsAt"),
        "display_ends_at": first_slot.get("endsAt"),
    }
    if (
        not isinstance(service_type, str)
        or service_type.casefold() != "delivery"
        or not decoded
        or not decoded.get("schema_recognised")
    ):
        return result
    starts_at = datetime.fromisoformat(decoded["starts_at_utc"])
    ends_at = datetime.fromisoformat(decoded["ends_at_utc"])
    result.update(
        {
            "usable_delivery_time": True,
            "starts_at_utc": iso_utc(starts_at),
            "ends_at_utc": iso_utc(ends_at),
            "starts_at_uk": uk_local(starts_at).isoformat(),
            "ends_at_uk": uk_local(ends_at).isoformat(),
            "wait_minutes": round((starts_at - query_started).total_seconds() / 60, 3),
        }
    )
    return result


def _service_state(value: Any, service: str) -> str:
    if isinstance(value, list):
        return DeliveryState.YES.value if service in value else DeliveryState.NO.value
    if value == "none":
        return DeliveryState.NO.value
    return DeliveryState.UNKNOWN.value


def classify_coop_payload(payload: Any) -> tuple[DeliveryState, str, str, str]:
    """Return state, reason, coverage and current delivery-slot fields."""

    if not isinstance(payload, dict):
        return DeliveryState.UNKNOWN, "Response was not a JSON object.", "Unknown", "Unknown"
    stores = payload.get("storeAvailability")
    slots = payload.get("slotAvailability")
    coverage = _service_state(stores, "delivery")
    current_slot = _service_state(slots, "delivery")
    if coverage == DeliveryState.YES.value:
        return (
            DeliveryState.YES,
            "The serving store explicitly offers delivery to this postcode.",
            coverage,
            current_slot,
        )
    if coverage == DeliveryState.NO.value:
        return (
            DeliveryState.NO,
            "No serving Co-op store offers delivery to this postcode.",
            coverage,
            current_slot,
        )
    return (
        DeliveryState.UNKNOWN,
        "The response contained an unrecognised storeAvailability value.",
        coverage,
        current_slot,
    )


def observation_from_coop_response(
    postcode: str,
    *,
    status: int | None,
    payload: Any,
    endpoint: str,
    query_started: datetime,
    response_completed: datetime,
    request_error: str | None = None,
    response_preview: str = "",
    evidence_path: str = "",
) -> Observation:
    """Build one conservative observation from first-party Co-op evidence."""

    postcode = normalize_postcode(postcode)
    common: dict[str, Any] = {
        "checked_at_utc": iso_utc(response_completed),
        "query_started_at_utc": iso_utc(query_started),
        "response_completed_at_utc": iso_utc(response_completed),
        "http_status": status,
        "endpoint": endpoint,
    }
    if status != 200:
        reason = request_error or f"Co-op returned HTTP {status} without a coverage decision."
        details = {"response_preview": response_preview[:500]}
        if evidence_path:
            details["business_response_path"] = evidence_path
        return Observation.unknown(postcode, "Co-op", reason, details=details, **common)
    if not isinstance(payload, dict):
        details = {"response_preview": response_preview[:500]}
        if evidence_path:
            details["business_response_path"] = evidence_path
        return Observation.unknown(
            postcode,
            "Co-op",
            "Co-op returned HTTP 200 but not a recognised JSON object.",
            details=details,
            **common,
        )

    returned = normalize_postcode(payload.get("formattedPostcode", ""))
    evidence_details = {"business_response_path": evidence_path} if evidence_path else {}
    if not returned:
        return Observation.unknown(
            postcode,
            "Co-op",
            "The response did not confirm the requested postcode.",
            details=evidence_details,
            **common,
        )
    if returned != postcode:
        return Observation.unknown(
            postcode,
            "Co-op",
            f"Co-op returned a different postcode: {returned!r}.",
            returned_postcode=returned,
            details=evidence_details,
            **common,
        )

    state, reason, coverage, current_slot = classify_coop_payload(payload)
    stores = payload.get("storeAvailability")
    first_slot = first_delivery_slot(payload, query_started)
    slot_is_delivery = bool(first_slot and first_slot.get("usable_delivery_time"))
    details = {
        "store_name": payload.get("name"),
        "store_availability": stores,
        "slot_availability": payload.get("slotAvailability"),
        "first_slot": payload.get("firstSlot")
        if isinstance(payload.get("firstSlot"), dict)
        else None,
        "decoded_first_slot": first_slot,
    }
    if evidence_path:
        details["business_response_path"] = evidence_path
    return Observation(
        postcode,
        "Co-op",
        state,
        reason,
        returned_postcode=returned,
        address_valid=DeliveryState.YES.value,
        delivery_coverage=coverage,
        collection_coverage=_service_state(stores, "collection"),
        current_slot=current_slot,
        first_slot_starts_at_utc=(first_slot or {}).get("starts_at_utc", "")
        if slot_is_delivery
        else "",
        first_slot_ends_at_utc=(first_slot or {}).get("ends_at_utc", "")
        if slot_is_delivery
        else "",
        first_slot_service_type=(first_slot or {}).get("service_type", ""),
        wait_minutes=(first_slot or {}).get("wait_minutes") if slot_is_delivery else None,
        details=details,
        **common,
    )


class CoopChecker:
    retailer = "Co-op"

    def __init__(
        self,
        *,
        headless: bool = True,
        channel: str | None = None,
        executable_path: str | None = None,
        cdp_url: str | None = None,
        evidence_dir: Path | None = None,
        bootstrap_attempts: int = 1,
    ) -> None:
        self.stop_reason: str | None = None
        self._sequence = 0
        self.evidence_dir = evidence_dir
        if self.evidence_dir is not None:
            self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.browser = BrowserSession(
            headless=headless,
            channel=channel,
            executable_path=executable_path,
            cdp_url=cdp_url,
            preferred_page_url="shop.coop.co.uk",
        )
        try:
            self._bootstrap(bootstrap_attempts)
        except Exception:
            self.browser.close()
            raise

    def _bootstrap(self, attempts: int) -> None:
        last_error = ""
        for attempt in range(1, attempts + 1):
            try:
                response = None
                if "shop.coop.co.uk" not in self.browser.page.url:
                    response = self.browser.page.goto(WELCOME_URL, wait_until="domcontentloaded")
                self.browser.page.wait_for_timeout(2_000)
                body = self.browser.page.locator("body").inner_text(timeout=5_000)
                content = self.browser.page.content()
                blocked = (
                    "something went wrong" in body.casefold()
                    or "outside the uk" in body.casefold()
                )
                status = response.status if response else None
                if "shop.coop.co.uk" in self.browser.page.url and not blocked and (
                    "/_next/static/" in content or status is None or status < 400
                ):
                    return
                last_error = f"HTTP {status if status is not None else 'existing page'}"
                if blocked:
                    last_error += " with a storefront access-control error"
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                time.sleep(5 * attempt)
        raise RuntimeError(f"Co-op browser bootstrap did not become usable: {last_error}")

    def _save_evidence(
        self,
        postcode: str,
        *,
        query_started: datetime,
        response_completed: datetime,
        result: dict[str, Any],
        payload: Any,
        parse_error: str | None,
    ) -> str:
        if self.evidence_dir is None:
            return ""
        self._sequence += 1
        safe_postcode = postcode.replace(" ", "_")
        filename = (
            f"{self._sequence:06d}-{query_started.strftime('%Y%m%dT%H%M%S%fZ')}-"
            f"{safe_postcode}.json"
        )
        path = self.evidence_dir / filename
        record = {
            "requested_postcode": postcode,
            "query_started_at_utc": iso_utc(query_started),
            "response_completed_at_utc": iso_utc(response_completed),
            "http_status": result.get("status"),
            "endpoint": result.get("url"),
            "fetch_error": result.get("error"),
            "parse_error": parse_error,
            "business_response": payload,
            "response_text": result.get("text") if payload is None else None,
        }
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(path)

    def check(self, postcode: str) -> Observation:
        postcode = normalize_postcode(postcode)
        url = ENDPOINT + "?postcode=" + quote(postcode)
        query_started = datetime.now(UTC)
        try:
            result = self.browser.page.evaluate(
                """async ({ postcode }) => {
                    const url = `/api/store/set?postcode=${encodeURIComponent(postcode)}`;
                    try {
                        const response = await fetch(url, {
                            method: 'POST',
                            credentials: 'include',
                            headers: {Accept: 'application/json'},
                            cache: 'no-store'
                        });
                        return {
                            status: response.status,
                            url: response.url,
                            text: await response.text(),
                            error: null
                        };
                    } catch (error) {
                        return {status: null, url, text: '', error: String(error)};
                    }
                }""",
                {"postcode": postcode},
            )
        except Exception as exc:
            result = {
                "status": None,
                "url": url,
                "text": "",
                "error": f"{type(exc).__name__}: {exc}",
            }
        response_completed = datetime.now(UTC)
        if not isinstance(result, dict):
            result = {
                "status": None,
                "url": url,
                "text": "",
                "error": "Browser evaluation returned an unrecognised result.",
            }
        status = result.get("status") if isinstance(result.get("status"), int) else None
        text = result.get("text") if isinstance(result.get("text"), str) else ""
        try:
            payload = json.loads(text)
            parse_error = None
        except json.JSONDecodeError as exc:
            payload = None
            parse_error = str(exc)

        evidence_path = ""
        evidence_error = ""
        try:
            evidence_path = self._save_evidence(
                postcode,
                query_started=query_started,
                response_completed=response_completed,
                result=result,
                payload=payload,
                parse_error=parse_error,
            )
        except OSError as exc:
            evidence_error = f"{type(exc).__name__}: {exc}"

        observation = observation_from_coop_response(
            postcode,
            status=status,
            payload=payload,
            endpoint=result.get("url") or url,
            query_started=query_started,
            response_completed=response_completed,
            request_error=result.get("error") or (parse_error if status == 200 else None),
            response_preview=text,
            evidence_path=evidence_path,
        )
        if evidence_error:
            observation.details["evidence_write_error"] = evidence_error

        if status in {403, 429}:
            self.stop_reason = f"Co-op access-control stop after HTTP {status}."
        elif status is None or status not in {200, 400}:
            self.stop_reason = f"Co-op stopped after unexpected HTTP status {status}."
        elif status == 200 and (
            not observation.returned_postcode
            or observation.returned_postcode != postcode
            or observation.delivery_coverage == DeliveryState.UNKNOWN.value
        ):
            self.stop_reason = "Co-op stopped after a postcode mismatch or schema change."
        return observation

    def close(self) -> None:
        self.browser.close()
