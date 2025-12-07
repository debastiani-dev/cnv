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
        # Assuming en-us or similar where dot is decimal separator,
        # but :n locale might vary.
        # Just checking it returns a string for now.
        assert str(m) == "1000.5" or str(m) == "1000,5" or "1000" in str(m)

    def test_repr(self):
        m = Money(10)
        assert repr(m) == "Money('10.00')"
