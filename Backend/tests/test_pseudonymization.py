from app.utils.pseudonymization import pseudonymize, strip_pii_from_record


def test_pseudonymize_stable():
    a = pseudonymize("John Doe", "name")
    b = pseudonymize("John Doe", "name")
    c = pseudonymize("john doe", "name")
    assert a == b == c
    assert len(a) == 64


def test_pseudonymize_field_specific():
    a = pseudonymize("value", "field_a")
    b = pseudonymize("value", "field_b")
    assert a != b


def test_strip_pii_from_record():
    cleaned = strip_pii_from_record(
        {"nida": "123", "payment_consistency": 0.9, "phone": "+255", "turnover_tzs": 1000}
    )
    assert "nida" not in cleaned and "phone" not in cleaned
    assert cleaned["payment_consistency"] == 0.9
