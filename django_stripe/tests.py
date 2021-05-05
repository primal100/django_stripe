from rest_framework.response import Response
from typing import Callable
from unittest import mock
from django.db import models
from django.dispatch import Signal
from django.urls import reverse_lazy
import stripe


signal_mock = mock.Mock()


def assert_customer_id_exists(user):
    user.refresh_from_db()
    assert user.stripe_customer_id


def assert_status_code_equals(response: Response, expected_status_code: int):
    try:
        assert response.status_code == expected_status_code
    except AssertionError as e:
        raise AssertionError(f"Status code: {response.status_code}\n{response.data}")


def assert_signal_called(signal: Signal):
    signal_mock.assert_called()
    kwargs = signal_mock.call_args.kwargs
    assert isinstance(kwargs['sender'], models.Model)
    assert kwargs['signal'] == signal


def make_request(method: Callable, view: str, expected_status_code: int, signal: Signal = None, **kwargs):
    response = method(reverse_lazy(view), data=kwargs)
    assert_status_code_equals(response, expected_status_code)
    if signal:
        assert_signal_called(signal)
    return response


def assert_customer_email(user, email: str):
    customer = stripe.Customer.retrieve(user.stripe_customer_id)
    assert customer['email'] == email