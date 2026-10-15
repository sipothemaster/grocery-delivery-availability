from grocery_delivery_availability.models import DeliveryState
from grocery_delivery_availability.retailers.amazon_fresh import extract_delivery_brands
from grocery_delivery_availability.retailers.chopchop import serving_store
from grocery_delivery_availability.retailers.coop import classify_coop_payload
from grocery_delivery_availability.retailers.iceland import delivery_code


def test_extract_amazon_delivery_brands() -> None:
    document = """
    <a href="/alm/storefront?almBrandId=fresh">
      <img alt="Amazon Fresh">Delivery available
    </a>
    <a href="/alm/storefront?almBrandId=other">
      <img alt="Whole Foods Market">Delivery unavailable
    </a>
    """
    assert extract_delivery_brands(document) == ("Amazon Fresh",)


def test_coop_coverage_is_not_inferred_from_a_current_slot() -> None:
    state, _reason, coverage, current_slot = classify_coop_payload(
        {"storeAvailability": ["delivery"], "slotAvailability": []}
    )
    assert state is DeliveryState.YES
    assert coverage == "Yes"
    assert current_slot == "No"


def test_coop_unknown_schema_is_not_no() -> None:
    state, _reason, coverage, _slot = classify_coop_payload({"message": "changed"})
    assert state is DeliveryState.UNKNOWN
    assert coverage == "Unknown"


def test_iceland_requires_a_boolean_code() -> None:
    assert delivery_code({"data": {"code": True}}) is True
    assert delivery_code({"data": {"code": "true"}}) is None


def test_chopchop_store_name_can_be_nested() -> None:
    payload = {
        "data": {"relationships": {"store": {"id": "example"}}},
        "included": [{"attributes": {"name": "Leeds Local"}}],
    }
    assert serving_store(payload) == "Leeds Local"
