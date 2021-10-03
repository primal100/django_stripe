from rest_framework.response import Response
from typing import Callable
from unittest import mock
from django.db import models
from django.dispatch import Signal
from django.urls import reverse_lazy

# So functions can be used by django_stripe user without needing to import from subscriptions
from subscriptions.tests import *


import stripe
from typing import Dict, Any


signal_mock = mock.Mock()


def assert_customer_id_exists(user):
    user.refresh_from_db()
    assert user.stripe_customer_id


def assert_status_code_equals(response: Response, expected_status_code: int):
    try:
        assert response.status_code == expected_status_code
    except AssertionError as e:
        raise AssertionError(f"Status code: {response.status_code}\n{getattr(response, 'data')}")


def assert_signal_called(signal: Signal):
    signal_mock.assert_called()
    kwargs = signal_mock.call_args.kwargs
    assert isinstance(kwargs['sender'], models.Model)
    assert kwargs['signal'] == signal


def get_url(view, **url_params: Dict[str, Any]):
    return reverse_lazy(view, kwargs=url_params or None)


def make_request(method: Callable, view: str, expected_status_code: int, url_params: Dict[str, Any] = None,
                 signal: Signal = None, **kwargs):
    url = get_url(view, **url_params or {})
    response = method(url, data=kwargs or None)
    assert_status_code_equals(response, expected_status_code)
    if signal:
        assert_signal_called(signal)
    return response


def assert_customer_email(user, email: str):
    customer = stripe.Customer.retrieve(user.stripe_customer_id)
    assert customer['email'] == email


def assert_customer_description(user, description: str):
    customer = stripe.Customer.retrieve(user.stripe_customer_id)
    assert customer['description'] == description


def get_expected_checkout_html(stripe_public_key: str, session_id: str) -> str:
    return f'<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <title>Redirect To Stripe Checkout</title>\n    <script src="https://js.stripe.com/v3/"></script>\n</head>\n<body>\n    <script>\n        var stripe = Stripe(\'{stripe_public_key}\');\n        var sessionId = \'{session_id}\';\n        stripe.redirectToCheckout({{sessionId: sessionId}})\n    </script>\n</body>\n</html>'
