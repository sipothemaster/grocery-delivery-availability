"""First-party session clients for the Ocado-platform grocery sites."""

from __future__ import annotations

import re
import time
from typing import Any
from uuid import uuid4

from ..browser import BrowserSession
from ..models import DeliveryState, Observation
from ..postcodes import normalize_postcode


def _json(response: Any) -> Any:
    try:
        return response.json()
    except Exception:
        return None


class EcomPlatformChecker:
    retailer = ""
    host = ""
    rotate_after = 100

    def __init__(
        self,
        *,
        headless: bool = True,
        channel: str | None = None,
        executable_path: str | None = None,
    ) -> None:
        self._browser_options = {
            "headless": headless,
            "channel": channel,
            "executable_path": executable_path,
        }
        self.browser: BrowserSession
        self.headers: dict[str, str]
        self._checks = 0
        self._open_session()

    def _open_session(self) -> None:
        self.browser = BrowserSession(**self._browser_options)
        response = self.browser.page.goto(self.host + "/", wait_until="domcontentloaded")
        if response is None or response.status >= 400:
            self.browser.close()
            raise RuntimeError(f"{self.retailer} homepage bootstrap failed")
        self.browser.page.wait_for_timeout(2000)
        document = self.browser.page.content()
        csrf_match = re.search(r'"csrf"\s*:\s*\{\s*"token"\s*:\s*"([^"]+)"', document)
        version_match = re.search(r'"assetVersion"\s*:\s*"([^"]+)"', document)
        cookies = {item["name"]: item["value"] for item in self.browser.context.cookies(self.host)}
        visitor = cookies.get("VISITORID", "")
        if not csrf_match or not visitor:
            self.browser.close()
            raise RuntimeError(f"{self.retailer} session tokens were not exposed")
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "Origin": self.host,
            "Referer": self.host + "/",
            "ecom-request-source": "web",
            "x-csrf-token": csrf_match.group(1),
            "visitor-id": visitor,
        }
        if version_match:
            self.headers["ecom-request-source-version"] = version_match.group(1)
        self._checks = 0

    def _rotate_if_needed(self) -> None:
        if self._checks < self.rotate_after:
            return
        self.browser.close()
        self._open_session()

    def _resolve_address(self, postcode: str) -> tuple[dict[str, Any] | None, Observation | None]:
        search_url = self.host + "/api/address/v1/addresses/by-search-term"
        response = self.browser.context.request.put(
            search_url,
            headers=self.headers,
            data={"query": postcode},
            timeout=15_000,
        )
        if response.status != 200:
            return None, Observation.unknown(
                postcode,
                self.retailer,
                f"Address search returned HTTP {response.status}.",
                http_status=response.status,
                endpoint=response.url,
                address_valid=DeliveryState.NO.value if response.status == 404 else "",
            )
        candidates = _json(response)
        if not isinstance(candidates, list) or not candidates:
            return None, Observation.unknown(
                postcode,
                self.retailer,
                "Address search returned no candidate.",
                http_status=200,
                endpoint=response.url,
                address_valid=DeliveryState.NO.value,
            )
        identifier = candidates[0].get("id") if isinstance(candidates[0], dict) else None
        if not identifier:
            return None, Observation.unknown(
                postcode,
                self.retailer,
                "The first address candidate had no identifier.",
                http_status=200,
                endpoint=response.url,
            )
        details_url = self.host + f"/api/address/v1/addresses/lookup/{identifier}/details"
        detail_response = self.browser.context.request.get(
            details_url, headers=self.headers, timeout=15_000
        )
        details = _json(detail_response)
        if detail_response.status != 200 or not isinstance(details, dict):
            return None, Observation.unknown(
                postcode,
                self.retailer,
                f"Address details returned HTTP {detail_response.status} or invalid JSON.",
                http_status=detail_response.status,
                endpoint=detail_response.url,
            )
        returned = normalize_postcode(details.get("postcode", ""))
        if returned != postcode:
            return None, Observation.unknown(
                postcode,
                self.retailer,
                f"The address resolver returned a different postcode: {returned!r}.",
                http_status=200,
                endpoint=detail_response.url,
                address_valid=DeliveryState.UNKNOWN.value,
            )
        return details, None

    def close(self) -> None:
        self.browser.close()


class OcadoChecker(EcomPlatformChecker):
    retailer = "Ocado"
    host = "https://www.ocado.com"
    rotate_after = 100

    def check(self, postcode: str) -> Observation:
        postcode = normalize_postcode(postcode)
        self._rotate_if_needed()
        self._checks += 1
        try:
            details, error = self._resolve_address(postcode)
            if error:
                return error
            assert details is not None
            response = self.browser.context.request.put(
                self.host + "/api/ecomdeliverydestinations/v2/deliverability",
                headers=self.headers,
                data={
                    "latitude": details.get("latitude"),
                    "longitude": details.get("longitude"),
                    "postalCode": postcode.replace(" ", ""),
                },
                timeout=15_000,
            )
            payload = _json(response)
            if response.status != 200 or not isinstance(payload, dict):
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    f"Deliverability returned HTTP {response.status} or invalid JSON.",
                    http_status=response.status,
                    endpoint=response.url,
                    address_valid=DeliveryState.YES.value,
                )
            decision = str(payload.get("deliverability", "")).upper()
            if decision == "DELIVERABLE":
                state = DeliveryState.YES
            elif decision in {"NOT_DELIVERABLE", "UNDELIVERABLE"}:
                state = DeliveryState.NO
            else:
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    f"Unrecognised deliverability decision: {decision!r}.",
                    http_status=200,
                    endpoint=response.url,
                    address_valid=DeliveryState.YES.value,
                )
            return Observation(
                postcode,
                self.retailer,
                state,
                f"Ocado returned {decision} for the resolved postcode.",
                http_status=200,
                endpoint=response.url,
                address_valid=DeliveryState.YES.value,
                delivery_coverage=state.value,
                details={"decision": decision},
            )
        except Exception as exc:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"Ocado session request failed: {type(exc).__name__}: {exc}",
                endpoint=self.host,
            )


class MorrisonsChecker(EcomPlatformChecker):
    retailer = "Morrisons"
    host = "https://groceries.morrisons.com"
    rotate_after = 25

    def __init__(self, *, catalog_settle_seconds: float = 1, **kwargs: Any) -> None:
        self.catalog_settle_seconds = catalog_settle_seconds
        super().__init__(**kwargs)

    def _catalogue(
        self, destination_id: str, region_id: str
    ) -> tuple[bool | None, int | None, dict[str, Any]]:
        session_data = {
            "deliveryDestinationId": destination_id,
            "regionId": region_id,
        }
        proposition = self.browser.context.request.post(
            self.host + "/api/customersessions/v2/sessions/proposition",
            headers=self.headers,
            data={
                "destinationRegionId": region_id,
                "deliveryDestinationId": destination_id,
            },
            timeout=15_000,
        )
        if not 200 <= proposition.status < 300:
            raise RuntimeError(f"proposition session returned HTTP {proposition.status}")
        active_url = self.host + "/api/customersessions/v2/sessions/active"
        active = self.browser.context.request.put(
            active_url, headers=self.headers, data=session_data, timeout=15_000
        )
        if not 200 <= active.status < 300:
            active = self.browser.context.request.post(
                active_url, headers=self.headers, data=session_data, timeout=15_000
            )
        if not 200 <= active.status < 300:
            raise RuntimeError(f"active session returned HTTP {active.status}")
        if self.catalog_settle_seconds:
            time.sleep(self.catalog_settle_seconds)

        url = (
            self.host
            + "/api/webproductpagews/v5/product-pages"
            + "?decoratedOnly=true&limit=1&tag=web&tag=lohp&request="
            + uuid4().hex
        )
        response = self.browser.context.request.get(
            url,
            headers={**self.headers, "Cache-Control": "no-cache", "Pragma": "no-cache"},
            timeout=15_000,
        )
        if response.status != 200:
            raise RuntimeError(f"product catalogue returned HTTP {response.status}")
        payload = _json(response)
        if not isinstance(payload, dict):
            raise RuntimeError("product catalogue returned invalid JSON")
        total_value = payload.get("totalProducts")
        try:
            total = int(total_value) if total_value is not None else None
        except (TypeError, ValueError):
            total = None
        groups = payload.get("productGroups")
        cache_header = str(response.headers.get("x-cache", ""))
        try:
            age = int(response.headers.get("age", "0"))
        except (TypeError, ValueError):
            age = 0
        evidence = {
            "region_id": region_id,
            "catalogue_total_products": total,
            "cache_header": cache_header,
            "cache_age": age,
        }
        if "hit" in cache_header.casefold() or age > 0:
            return None, total, evidence
        available = bool(isinstance(groups, list) and groups) or bool(total and total > 0)
        return available, total, evidence

    def check(self, postcode: str) -> Observation:
        postcode = normalize_postcode(postcode)
        self._rotate_if_needed()
        self._checks += 1
        try:
            details, error = self._resolve_address(postcode)
            if error:
                return error
            assert details is not None
            temporary = self.browser.context.request.post(
                self.host + "/api/ecomdeliverydestinations/v2/temporary-delivery-destinations",
                headers=self.headers,
                data={
                    "visitorId": self.headers["visitor-id"],
                    "latitude": details.get("latitude"),
                    "longitude": details.get("longitude"),
                    "postalCode": postcode.replace(" ", ""),
                    "formattedAddress": details.get("formattedAddress"),
                },
                timeout=15_000,
            )
            destination_payload = _json(temporary)
            if temporary.status != 200:
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    f"Temporary destination returned HTTP {temporary.status}.",
                    http_status=temporary.status,
                    endpoint=temporary.url,
                    address_valid=DeliveryState.YES.value,
                )
            if isinstance(destination_payload, str):
                destination_id = destination_payload
            elif isinstance(destination_payload, dict):
                destination_id = str(
                    destination_payload.get("id")
                    or destination_payload.get("deliveryDestinationId")
                    or ""
                )
            else:
                destination_id = ""
            if not destination_id:
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    "Temporary destination returned no identifier.",
                    http_status=200,
                    endpoint=temporary.url,
                )

            decision_url = (
                self.host + f"/api/ecomdeliverydestinations/v4/delivery-addresses/{destination_id}"
            )
            decision_response = self.browser.context.request.get(
                decision_url, headers=self.headers, timeout=15_000
            )
            payload = _json(decision_response)
            if decision_response.status != 200 or not isinstance(payload, dict):
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    f"Delivery decision returned HTTP {decision_response.status} or invalid JSON.",
                    http_status=decision_response.status,
                    endpoint=decision_response.url,
                )
            returned = normalize_postcode(payload.get("postalCode", ""))
            if returned != postcode:
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    f"Delivery decision returned a different postcode: {returned!r}.",
                    http_status=200,
                    endpoint=decision_response.url,
                )
            decision = str(payload.get("deliverability", "")).upper()
            propositions = [
                item for item in payload.get("propositions", []) if isinstance(item, dict)
            ]
            kinds = {
                str(item.get("propositionType", "")).upper()
                for item in propositions
                if item.get("propositionType")
            }
            raw_region = next(
                (
                    item.get("regionId")
                    for item in propositions
                    if str(item.get("propositionType", "")).upper() == "SCHEDULED"
                    and item.get("regionId")
                ),
                payload.get("resolvedRegionId"),
            )
            region_id = str(raw_region or "")
            evidence: dict[str, Any] = {
                "decision": decision,
                "propositions": sorted(kinds),
                "region_id": region_id,
            }
            if decision in {"NOT_DELIVERABLE", "UNDELIVERABLE"}:
                return Observation(
                    postcode,
                    self.retailer,
                    DeliveryState.NO,
                    f"Morrisons returned {decision} for the resolved postcode.",
                    http_status=200,
                    endpoint=decision_response.url,
                    address_valid=DeliveryState.YES.value,
                    delivery_coverage=DeliveryState.NO.value,
                    fast_delivery=DeliveryState.NO.value,
                    scheduled_delivery=DeliveryState.NO.value,
                    details=evidence,
                )
            if decision != "DELIVERABLE" or not region_id:
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    "Morrisons did not return a usable deliverable decision and region.",
                    http_status=200,
                    endpoint=decision_response.url,
                    address_valid=DeliveryState.YES.value,
                    details=evidence,
                )
            try:
                catalogue, _total, catalog_evidence = self._catalogue(destination_id, region_id)
            except Exception as exc:
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    f"Product catalogue validation failed: {type(exc).__name__}: {exc}",
                    http_status=200,
                    endpoint=decision_response.url,
                    address_valid=DeliveryState.YES.value,
                    fast_delivery=DeliveryState.UNKNOWN.value,
                    scheduled_delivery=DeliveryState.UNKNOWN.value,
                    details=evidence,
                )
            evidence.update(catalog_evidence)
            if catalogue is None:
                return Observation.unknown(
                    postcode,
                    self.retailer,
                    "The product response reported cache reuse and was not accepted.",
                    http_status=200,
                    endpoint=decision_response.url,
                    address_valid=DeliveryState.YES.value,
                    details=evidence,
                )
            if not catalogue:
                return Observation(
                    postcode,
                    self.retailer,
                    DeliveryState.NO,
                    "The selected destination's product catalogue contained no usable products.",
                    http_status=200,
                    endpoint=decision_response.url,
                    address_valid=DeliveryState.YES.value,
                    delivery_coverage=DeliveryState.NO.value,
                    fast_delivery=DeliveryState.NO.value,
                    scheduled_delivery=DeliveryState.NO.value,
                    details=evidence,
                )
            return Observation(
                postcode,
                self.retailer,
                DeliveryState.YES,
                "The accepted destination returned a usable product catalogue.",
                http_status=200,
                endpoint=decision_response.url,
                address_valid=DeliveryState.YES.value,
                delivery_coverage=DeliveryState.YES.value,
                fast_delivery=(
                    DeliveryState.YES.value if "FAST" in kinds else DeliveryState.NO.value
                ),
                scheduled_delivery=(
                    DeliveryState.YES.value if "SCHEDULED" in kinds else DeliveryState.NO.value
                ),
                details=evidence,
            )
        except Exception as exc:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"Morrisons session request failed: {type(exc).__name__}: {exc}",
                endpoint=self.host,
            )
