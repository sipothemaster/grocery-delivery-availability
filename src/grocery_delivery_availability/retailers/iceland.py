"""Iceland postcode delivery decision through a browser-created session."""

from __future__ import annotations

from typing import Any

from ..browser import BrowserSession
from ..models import DeliveryState, Observation
from ..postcodes import normalize_postcode

HOST = "https://www.iceland.co.uk"
ENDPOINT = (
    HOST
    + "/mobify/proxy/ocapi/on/demandware.store/"
    + "Sites-icelandfoodsuk-Site/default/Delivery-GetDeliveryStatus"
)


def delivery_code(payload: Any) -> bool | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    value = data.get("code")
    return value if isinstance(value, bool) else None


class IcelandChecker:
    retailer = "Iceland"

    def __init__(
        self,
        *,
        headless: bool = True,
        channel: str | None = None,
        executable_path: str | None = None,
    ) -> None:
        self.browser = BrowserSession(
            headless=headless, channel=channel, executable_path=executable_path
        )
        response = self.browser.page.goto(HOST + "/", wait_until="domcontentloaded")
        if response is None or response.status >= 400:
            self.close()
            raise RuntimeError("Iceland homepage bootstrap failed")
        self.browser.page.wait_for_timeout(3000)

    def check(self, postcode: str) -> Observation:
        postcode = normalize_postcode(postcode)
        try:
            response = self.browser.context.request.get(
                ENDPOINT,
                params={"postcode": postcode},
                headers={"Accept": "application/json", "Referer": HOST + "/"},
                timeout=45_000,
            )
        except Exception as exc:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"Iceland request failed: {type(exc).__name__}: {exc}",
                endpoint=ENDPOINT,
            )
        if response.status != 200:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"Iceland returned HTTP {response.status}.",
                http_status=response.status,
                endpoint=response.url,
            )
        try:
            payload = response.json()
        except Exception:
            payload = None
        code = delivery_code(payload)
        if code is None:
            return Observation.unknown(
                postcode,
                self.retailer,
                "Iceland returned no boolean delivery code.",
                http_status=200,
                endpoint=response.url,
            )
        return Observation(
            postcode,
            self.retailer,
            DeliveryState.YES if code else DeliveryState.NO,
            f"Iceland returned the explicit delivery code {str(code).lower()}.",
            http_status=200,
            endpoint=response.url,
            delivery_coverage=(DeliveryState.YES.value if code else DeliveryState.NO.value),
        )

    def close(self) -> None:
        self.browser.close()
