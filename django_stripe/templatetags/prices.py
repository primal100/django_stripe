from django import template
from forex_python.converter import CurrencyCodes

register = template.Library()


c = CurrencyCodes()


def to_decimal_currency(value):
    # This probably not valid for some currencies. Price block can be overridden.
    return value / 100


def currency_symbol(value) -> str:
    if value == "USD":
        return "$"      # Forex-python return US$, prefer to use just $ for US dollars
    return c.get_symbol(value.upper())


register.filter('to_decimal_currency', to_decimal_currency)
register.filter('currency_symbol', currency_symbol)
