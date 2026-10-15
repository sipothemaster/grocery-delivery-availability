"""Run one conservative, UI-driven Co-op workflow probe.

This diagnostic intentionally accepts one postcode and entry URL, performs no
retries, and writes all live evidence below an ignored runtime directory.  It
does not save browser storage, cookies, request headers, or authentication
material.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Response, sync_playwright

from grocery_delivery_availability.retailers.coop import (
    first_delivery_slot,
    iso_utc,
)

HOST = "https://shop.coop.co.uk"
WELCOME_URL = HOST + "/welcome"


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postcode", default="LS2 9JT")
    parser.add_argument("--url", default=WELCOME_URL)
    parser.add_argument("--output-root", type=Path, default=Path(".tmp/coop-probe"))
    parser.add_argument("--browser-channel", default="chrome")
    parser.add_argument("--headless", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_started = utc_now()
    run_dir = args.output_root / run_started.strftime("%Y%m%dT%H%M%SZ")
    responses_dir = run_dir / "business-responses"
    responses_dir.mkdir(parents=True, exist_ok=False)

    requested_postcode = " ".join(args.postcode.upper().split())
    api_responses: list[dict[str, Any]] = []
    network_failures: list[dict[str, Any]] = []
    business_payloads: list[dict[str, Any]] = []
    console_errors: list[dict[str, str]] = []

    def capture_response(response: Response) -> None:
        parsed = urlparse(response.url)
        if parsed.netloc != "shop.coop.co.uk":
            return
        completed = utc_now()
        if response.status >= 400:
            network_failures.append(
                {
                    "method": response.request.method,
                    "url": response.url,
                    "status": response.status,
                    "completed_at_utc": iso_utc(completed),
                }
            )
        if not parsed.path.startswith("/api/"):
            return
        content_type = response.headers.get("content-type", "")
        record: dict[str, Any] = {
            "method": response.request.method,
            "url": response.url,
            "status": response.status,
            "completed_at_utc": iso_utc(completed),
            "content_type": content_type,
        }
        try:
            body = response.text()
        except Exception as exc:
            record["body_error"] = f"{type(exc).__name__}: {exc}"
        else:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                record["response_preview"] = body[:500]
            else:
                filename = f"{len(api_responses) + 1:02d}-{parsed.path.rsplit('/', 1)[-1]}.json"
                path = responses_dir / filename
                path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                record["business_json_path"] = str(path.relative_to(run_dir))
                business_payloads.append(
                    {
                        "url": response.url,
                        "status": response.status,
                        "payload": payload,
                    }
                )
        api_responses.append(record)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel=args.browser_channel or None,
            headless=args.headless,
        )
        context = browser.new_context(locale="en-GB", timezone_id="Europe/London")
        page = context.new_page()
        page.on("response", capture_response)

        def capture_failed_request(request: Any) -> None:
            parsed = urlparse(request.url)
            if parsed.netloc == "shop.coop.co.uk":
                network_failures.append(
                    {
                        "method": request.method,
                        "url": request.url,
                        "status": None,
                        "failure": request.failure,
                        "completed_at_utc": iso_utc(utc_now()),
                    }
                )

        page.on("requestfailed", capture_failed_request)

        def capture_console(message: Any) -> None:
            text = message.text
            if message.type == "error" or "imperva" in text.casefold():
                console_errors.append(
                    {
                        "level": message.type,
                        "message": text[:2000],
                        "source_url": str(message.location.get("url", "")),
                    }
                )

        page.on("console", capture_console)
        navigation_status: int | None = None
        page_error: str | None = None
        postcode_submitted = False
        try:
            navigation = page.goto(args.url, wait_until="domcontentloaded", timeout=45_000)
            navigation_status = navigation.status if navigation else None
            page.wait_for_timeout(4_000)
            field = page.locator("#postcode")
            if field.is_visible(timeout=2_000):
                field.fill(requested_postcode)
                page.get_by_role("button", name="Continue to shop").click(timeout=10_000)
                postcode_submitted = True
                page.wait_for_timeout(6_000)
        except Exception as exc:
            page_error = f"{type(exc).__name__}: {exc}"
        finally:
            final_title = page.title()
            final_url = page.url
            body_text = page.locator("body").inner_text(timeout=5_000)[:2000]
            page.screenshot(path=run_dir / "final-page.png", full_page=True)
            response_completed = utc_now()
            context.close()
            browser.close()

    store_response = next(
        (
            item
            for item in reversed(business_payloads)
            if urlparse(item["url"]).path == "/api/store/set"
        ),
        None,
    )
    store_payload = store_response["payload"] if store_response else None
    confirmed_postcode = (
        store_payload.get("formattedPostcode") if isinstance(store_payload, dict) else None
    )
    postcode_matches = confirmed_postcode == requested_postcode if confirmed_postcode else None
    store_availability = (
        store_payload.get("storeAvailability") if isinstance(store_payload, dict) else None
    )
    slot_availability = (
        store_payload.get("slotAvailability") if isinstance(store_payload, dict) else None
    )
    coverage = (
        "Yes"
        if isinstance(store_availability, list) and "delivery" in store_availability
        else "No"
        if store_availability == "none"
        or (isinstance(store_availability, list) and "delivery" not in store_availability)
        else "Unknown"
    )
    first_slot = first_delivery_slot(store_payload, run_started)
    delivery_slot_known = bool(first_slot and first_slot.get("usable_delivery_time"))
    feasible = bool(
        store_response
        and store_response["status"] == 200
        and postcode_matches
        and coverage in {"Yes", "No"}
        and (coverage == "No" or delivery_slot_known or "delivery" not in (slot_availability or []))
    )
    blocker = None
    if not feasible:
        if any(item.get("status") in {403, 429} for item in network_failures):
            blocker = "A required first-party page or API request was access-controlled."
        elif any("imperva" in item["message"].casefold() for item in console_errors):
            blocker = "Imperva blocked a required first-party API request."
        elif not postcode_submitted:
            blocker = "The normal page did not remain usable long enough to submit the postcode."
        elif not store_response:
            blocker = "No JSON response from /api/store/set was observed."
        else:
            blocker = "The response did not provide a postcode-matched, recognised workflow result."

    summary = {
        "query_started_at_utc": iso_utc(run_started),
        "response_completed_at_utc": iso_utc(response_completed),
        "requested_postcode": requested_postcode,
        "entry_url": args.url,
        "confirmed_postcode": confirmed_postcode,
        "postcode_matches": postcode_matches,
        "navigation_status": navigation_status,
        "postcode_submitted": postcode_submitted,
        "final_url": final_url,
        "final_title": final_title,
        "page_error": page_error,
        "page_text_preview": body_text,
        "api_responses": api_responses,
        "network_failures": network_failures,
        "console_errors": console_errors,
        "delivery_coverage": coverage,
        "collection_coverage": (
            "Yes"
            if isinstance(store_availability, list) and "collection" in store_availability
            else "No"
            if store_availability == "none" or isinstance(store_availability, list)
            else "Unknown"
        ),
        "store_availability": store_availability,
        "slot_availability": slot_availability,
        "first_delivery_slot": first_slot,
        "feasible": feasible,
        "blocker": blocker,
    }
    summary_path = run_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(summary_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if feasible else 2


if __name__ == "__main__":
    raise SystemExit(main())
