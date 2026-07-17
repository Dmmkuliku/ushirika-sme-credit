from app.utils.pseudonymization import pseudonymize


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
