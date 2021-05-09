from . import payments
from django import forms
from typing import List, Tuple
import stripe


products = stripe.Product.list(url="http://localhost/paywall", active=True, limit=1)
product_id = products['data'][0]['id']


def get_prices() -> List[Tuple[str, str]]:
    prices = payments.get_subscription_prices(None, product_id)
    return [(p['id'], f'${p["unit_amount"] / 10:.2f} / {p["recurring"]["interval"]}') for p in prices]


class SubscriptionForm(forms.Form):
    price_id = forms.ChoiceField(choices=get_prices)


