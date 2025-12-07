# pylint: disable=consider-using-f-string
# pylint: disable=no-member

"""
Class to represent money with specific decimal precision and rounding
Reference: https://gist.github.com/henriquebastos/2591d1e223bd573dba9ee0bdb1b8f662
"""

from decimal import ROUND_HALF_UP, Decimal

CURRENCY_CHOICES = [
    ("BRL", "Real Brasileiro"),
    ("USD", "US Dollar"),
    ("EUR", "Euro"),
    ("GBP", "British Pound"),
    ("JPY", "Japanese Yen"),
]

DEFAULT_CURRENCY = "BRL"


class Money(Decimal):
    def __new__(cls, value=0, decimal_precision=2):
        number = super().__new__(cls, value)
        if not number._is_precise(decimal_precision):
            number = number._round(decimal_precision)
        return number

    def __repr__(self):
        return "{0}({1!r})".format(self.__class__.__name__, super().__str__())

    def __str__(self):
        return "{:n}".format(self)

    def _is_precise(self, precision):
        return abs(self.as_tuple().exponent) == precision

    def _round(self, decimal_precision=2):
        number = self.quantize(
            Decimal(str(1 / 10**decimal_precision)), rounding=ROUND_HALF_UP
        )
        return Money(number, decimal_precision)
