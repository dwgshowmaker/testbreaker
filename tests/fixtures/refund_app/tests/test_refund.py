from refund import can_refund


def test_refund():
    assert can_refund(10)
    assert not can_refund(40)

