"""Amazon Grocery address selection and delivery-brand extraction."""

from __future__ import annotations

import time
from uuid import uuid4

from lxml import html

from ..models import DeliveryState, Observation
from ..postcodes import normalize_postcode
from .base import new_http_session

HOST = "https://www.amazon.co.uk"
GATEWAY = HOST + "/fmc/grocery-gateway"
ADDRESS_CHANGE = HOST + "/portal-migration/hz/glow/address-change"


def extract_delivery_brands(document: str) -> tuple[str, ...]:
    try:
        root = html.fromstring(document)
    except (ValueError, TypeError):
        return ()
    brands: list[str] = []
    for anchor in root.xpath("//a[contains(@href, '/alm/storefront')]"):
        text = " ".join(part.strip() for part in anchor.itertext() if part.strip())
        if "delivery available" not in text.casefold():
            continue
        alts = [value.strip() for value in anchor.xpath(".//img/@alt") if value.strip()]
        candidate = alts[-1] if alts else text
        candidate = candidate.replace("Delivery available", "").strip(" -|")
        if candidate and candidate not in brands:
            brands.append(candidate)
    return tuple(brands)


class AmazonFreshChecker:
    retailer = "Amazon Fresh"

    def __init__(
        self,
        *,
        timeout_seconds: float = 30,
        address_settle_seconds: float = 5,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.address_settle_seconds = address_settle_seconds
        self.session = new_http_session()
        self._ready = False

    def _bootstrap(self) -> None:
        if self._ready:
            return
        response = self.session.get(GATEWAY, timeout=self.timeout_seconds)
        response.raise_for_status()
        self._ready = True

    def check(self, postcode: str) -> Observation:
        postcode = normalize_postcode(postcode)
        try:
            self._bootstrap()
        except Exception as exc:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"Gateway bootstrap failed: {type(exc).__name__}: {exc}",
                endpoint=GATEWAY,
            )

        response = self.session.post(
            ADDRESS_CHANGE,
            params={"actionSource": "glow"},
            headers={
                "Accept": "application/json,text/html,*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": HOST,
                "Referer": GATEWAY,
                "X-Requested-With": "XMLHttpRequest",
            },
            data={
                "locationType": "LOCATION_INPUT",
                "zipCode": postcode,
                "storeContext": "generic",
                "deviceType": "web",
                "pageType": "Gateway",
                "actionSource": "glow",
            },
            timeout=self.timeout_seconds,
        )
        if response.status_code != 200:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"Address selection returned HTTP {response.status_code}.",
                http_status=response.status_code,
                endpoint=response.url,
            )
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not payload.get("successful") or not payload.get("isValidAddress"):
            return Observation.unknown(
                postcode,
                self.retailer,
                "Amazon did not resolve the postcode to a valid address.",
                http_status=200,
                endpoint=response.url,
                address_valid=DeliveryState.NO.value,
            )
        resolved = normalize_postcode(payload.get("address", {}).get("zipCode", ""))
        if resolved != postcode:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"Amazon returned a different postcode: {resolved!r}.",
                http_status=200,
                endpoint=response.url,
                address_valid=DeliveryState.UNKNOWN.value,
            )

        if self.address_settle_seconds:
            time.sleep(self.address_settle_seconds)
        gateway = self.session.get(
            GATEWAY,
            params={"request": uuid4().hex},
            headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            timeout=self.timeout_seconds,
        )
        if gateway.status_code != 200:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"The grocery gateway returned HTTP {gateway.status_code}.",
                http_status=gateway.status_code,
                endpoint=gateway.url,
                address_valid=DeliveryState.YES.value,
            )

        brands = extract_delivery_brands(gateway.text)
        available = "Amazon Fresh" in brands
        return Observation(
            postcode,
            self.retailer,
            DeliveryState.YES if available else DeliveryState.NO,
            (
                "The Amazon Fresh brand was displayed as delivery-available."
                if available
                else "The accepted address displayed no delivery-available Amazon Fresh brand."
            ),
            http_status=200,
            endpoint=gateway.url,
            address_valid=DeliveryState.YES.value,
            brands=brands,
        )

    def close(self) -> None:
        self.session.close()
