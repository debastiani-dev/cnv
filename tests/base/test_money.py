from decimal import Decimal

from apps.base.utils.money import Money


class TestMoney:
    def test_initialization(self):
        m = Money("10.555")
        assert isinstance(m, Decimal)
        # Should round to 2 decimals by default
        assert m == Decimal("10.56")

    def test_precision(self):
        m = Money(10.555, decimal_precision=3)
        assert m == Decimal("10.555")

    def test_string_representation(self):
        m = Money(1000.50)
        # BRL format expectation: 1.000,50
        assert str(m) == "1.000,50"

    def test_repr(self):
        m = Money(10)
        assert repr(m) == "Money('10.00')"
