from grocery_delivery_availability.postcodes import is_valid_postcode, normalize_postcode


def test_normalize_postcode() -> None:
    assert normalize_postcode(" e1  6hq ") == "E1 6HQ"
    assert normalize_postcode("GIR0AA") == "GIR 0AA"


def test_basic_validation_does_not_claim_current_existence() -> None:
    assert is_valid_postcode("SW1A 1AA")
    assert is_valid_postcode("YO16 5SL")
    assert not is_valid_postcode("not a postcode")
