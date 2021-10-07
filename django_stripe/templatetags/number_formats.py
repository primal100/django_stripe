from datetime import datetime
from django import template


register = template.Library()


@register.filter("timestamp_to_date")
def timestamp_to_date(value):
    return datetime.fromtimestamp(value).strftime("%d %B %Y")


@register.filter("two_digit_year")
def two_digit_year(value):
    return str(value)[2:]
