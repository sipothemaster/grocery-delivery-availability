"""Sainsbury's Chop Chop postcode service."""

from __future__ import annotations

from typing import Any

from ..models import DeliveryState, Observation
from ..postcodes import normalize_postcode
from .base import new_http_session

ENDPOINT = "https://raider-api.chopchopapp.co.uk/postcodes/"


def serving_store(payload: Any) -> str:
    if isinstance(payload, list):
        for item in payload:
            found = serving_store(item)
            if found:
                return found
        return ""
    if not isinstance(payload, dict):
        return ""
    for key in ("name", "storeName", "store_name"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for value in payload.values():
        found = serving_store(value)
        if found:
            return found
    return ""


class ChopChopChecker:
    retailer = "Chop Chop"

    def __init__(self, *, timeout_seconds: float = 20) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = new_http_session()

    def check(self, postcode: str) -> Observation:
        postcode = normalize_postcode(postcode)
        url = ENDPOINT + postcode.replace(" ", "").lower()
        response = self.session.get(url, timeout=self.timeout_seconds)
        if response.status_code == 404:
            return Observation(
                postcode,
                self.retailer,
                DeliveryState.NO,
                "The postcode service returned NOT_FOUND.",
                http_status=404,
                endpoint=url,
                delivery_coverage=DeliveryState.NO.value,
            )
        if response.status_code != 200:
            return Observation.unknown(
                postcode,
                self.retailer,
                f"The postcode service returned HTTP {response.status_code}.",
                http_status=response.status_code,
                endpoint=url,
            )
        try:
            payload = response.json()
        except ValueError:
            return Observation.unknown(
                postcode,
                self.retailer,
                "The postcode service returned non-JSON content.",
                http_status=200,
                endpoint=url,
            )
        store = serving_store(payload)
        return Observation(
            postcode,
            self.retailer,
            DeliveryState.YES,
            "A serving Chop Chop store was returned.",
            http_status=200,
            endpoint=url,
            delivery_coverage=DeliveryState.YES.value,
            details={"serving_store": store},
        )

    def close(self) -> None:
        self.session.close()
