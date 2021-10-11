from datetime import datetime
from django import template


register = template.Library()


@register.filter("timestamp_to_date")
def timestamp_to_date(value):
    """
    Template filter to change seconds since epoch to human readable format
    """
    return datetime.fromtimestamp(value).strftime("%d %B %Y")


@register.filter("two_digit_year")
def two_digit_year(value):
    """
    Template filter to display last two characters only
    """
    return str(value)[2:]
