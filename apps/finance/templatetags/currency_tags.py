from django import template

from apps.base.utils.money import Money

register = template.Library()


@register.filter(name="to_money")
def to_money(value):
    """Output Example: '1.250,50'"""
    if value is None:
        return "0,00"
    return str(Money(value))
