import os

import sys
import pytest
import stripe
from stripe.error import InvalidRequestError
from unittest import mock

from django_stripe import payments, signals
from django_stripe.tests import signal_mock
import subscriptions
from tests.django_stripe_testapp.models import User

from typing import List, Dict, Any

python_version = sys.version_info
ci_string = f'{os.name}-{python_version.major}{python_version.minor}'


def pytest_addoption(parser):
    parser.addoption("--apikey", action="store", default=os.environ.get('STRIPE_TEST_SECRET_KEY'))


@pytest.fixture(scope="session", autouse=True)
def stripe_api_key(pytestconfig):
    stripe.api_key = pytestconfig.getoption("apikey")
    return stripe_api_key


@pytest.fixture(autouse=True)
def setup_settings(stripe_api_key, settings):
    settings.STRIPE_API_KEY = stripe_api_key


@pytest.fixture(autouse=True)
def mock_signals():
    for s in signals.all_signals:
        s.connect(signal_mock)
    yield
    signal_mock.reset_mock()


@pytest.fixture(scope="session")
def stripe_subscription_product_url() -> str:
    return "http://localhost/paywall"


@pytest.fixture(scope="session")
def stripe_unsubscribed_product_url() -> str:
    return "http://localhost/second_paywall"


@pytest.fixture(scope="session")
def checkout_success_url() -> str:
    return "http://localhost"


@pytest.fixture(scope="session")
def checkout_cancel_url() -> str:
    return "http://localhost/cancel"


@pytest.fixture(scope="session")
def user_email() -> str:
    return f'stripe-subscriptions-{ci_string}@example.com'


@pytest.fixture(scope="session")
def user_alternative_email() -> str:
    return f'stripe-subscriptions-alternative-{ci_string}@example.com'


@pytest.fixture
def user(user_email):
    user = User(id=1, email=user_email, first_name='Test', last_name="User", username="test_user")
    user.save()
    yield user
    if user.stripe_customer_id:
        try:
            subscriptions.delete_customer(user)
        except InvalidRequestError:
            pass


@pytest.fixture()
def second_user(user_alternative_email):
    user = User(id=2, email=user_alternative_email, first_name='Second', last_name="User", username="second_user")
    user.save()
    payments.create_customer(user)
    yield user
    try:
        subscriptions.delete_customer(user)
    except InvalidRequestError:
        pass


def create_customer_id(user):
    customers = stripe.Customer.list(email=user.email)
    for customer in customers:
        stripe.Customer.delete(customer['id'])
    payments.create_customer(user)
    return user


@pytest.fixture
def user_with_customer_id(user):
    return create_customer_id(user)


@pytest.fixture(params=["no-customer-id", "with-customer-id"])
def user_with_and_without_customer_id(request, user):
    if request.param == "no-customer-id":
        return user
    return create_customer_id(user)


@pytest.fixture(params=["no-user", "user"])
def no_user_or_user(request, user):
    if request.param == "no-user":
        return None
    return user


@pytest.fixture
def permission_error(no_user_or_user) -> str:
    if no_user_or_user:
        return 'You do not have permission to perform this action.'
    return 'Authentication credentials were not provided.'


@pytest.fixture(params=["no-user", "no-customer-id", "with-customer-id"])
def no_user_and_user_with_and_without_customer_id(request, user):
   if request.param == "no-user":
        return None
   elif request.param == "no-customer-id":
        return user
   return create_customer_id(user)


@pytest.fixture
def mock_customer_retrieve(monkeypatch):
    monkeypatch.setattr(stripe.Customer, "retrieve", mock.Mock())


@pytest.fixture
def disable_keep_customer_email_updated(settings):
    settings.STRIPE_KEEP_CUSTOMER_DETAILS_UPDATED = False


@pytest.fixture()
def api_client():

    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def client_no_user_and_user_with_and_without_stripe_id(api_client, no_user_and_user_with_and_without_customer_id):
    if no_user_and_user_with_and_without_customer_id:
        api_client.force_login(no_user_and_user_with_and_without_customer_id)
    return api_client


@pytest.fixture
def client_no_user_and_without_stripe_id(api_client, no_user_or_user):
    if no_user_or_user:
        api_client.force_login(no_user_or_user)
    return api_client


@pytest.fixture
def authenticated_client_with_customer_id(api_client, user_with_customer_id):
    api_client.force_login(user_with_customer_id)
    return api_client


@pytest.fixture
def authenticated_client_second_user(api_client, second_user):
    api_client.force_login(second_user)
    return api_client


@pytest.fixture
def authenticated_client_with_without_customer_id(api_client, user_with_and_without_customer_id):
    api_client.force_login(user_with_and_without_customer_id)
    return api_client


@pytest.fixture
def authenticated_client_with_subscribed_user(api_client, subscribed_user):
    api_client.force_login(subscribed_user)
    return api_client


@pytest.fixture
def payment_method(user_with_customer_id) -> stripe.PaymentMethod:
    payment_method = subscriptions.tests.create_payment_method_for_customer(user_with_customer_id)
    return payment_method


@pytest.fixture
def payment_method_id(payment_method) -> str:
    return payment_method['id']


@pytest.fixture
def payment_method_saved(user_with_customer_id, payment_method) -> stripe.PaymentMethod:
    payment_method['customer'] = user_with_customer_id.stripe_customer_id
    payment_method['card']['checks']['cvc_check'] = "pass"
    return payment_method


payment_method_api_keys = ["billing_details", "card", "created", "id", "type"]


def get_payment_method_from_api(payment_method: stripe.PaymentMethod, default: bool) -> Dict[str, Any]:
    pm = {k: payment_method[k] for k in payment_method_api_keys}
    pm["default"] = default
    return pm


@pytest.fixture
def payment_method_from_api(payment_method_saved) -> Dict[str, Any]:
    return get_payment_method_from_api(payment_method_saved, False)


@pytest.fixture
def default_payment_method_for_customer(user_with_customer_id) -> stripe.PaymentMethod:
    return subscriptions.tests.create_default_payment_method_for_customer(user_with_customer_id)


@pytest.fixture
def default_payment_method_id(default_payment_method_for_customer) -> str:
    return default_payment_method_for_customer['id']


@pytest.fixture
def default_payment_method_saved(user_with_customer_id, default_payment_method_for_customer) -> stripe.PaymentMethod:
    default_payment_method_for_customer['customer'] = user_with_customer_id.stripe_customer_id
    default_payment_method_for_customer['card']['checks']['cvc_check'] = "pass"
    return default_payment_method_for_customer


@pytest.fixture
def default_payment_method_from_api(default_payment_method_saved) -> Dict[str, Any]:
    return get_payment_method_from_api(default_payment_method_saved, True)


@pytest.fixture
def non_existing_payment_method_id(user_with_customer_id) -> str:
    return 'pm_1IpWttCz06et8Vuzx4IABCD'


@pytest.fixture
def subscribed_user(user_with_customer_id, stripe_price_id, default_payment_method_id):
    subscriptions.create_subscription(user_with_customer_id, stripe_price_id)
    return user_with_customer_id


@pytest.fixture(scope="session")
def subscribed_product_name() -> str:
    return 'Gold'


@pytest.fixture(scope="session")
def stripe_subscription_product_id(stripe_subscription_product_url, subscribed_product_name) -> str:
    products = stripe.Product.list(url=stripe_subscription_product_url, active=True, limit=1)
    if products:
        product = products['data'][0]
    else:
        product = stripe.Product.create(name=subscribed_product_name, url=stripe_subscription_product_url)
    return product['id']


@pytest.fixture(scope="session")
def stripe_price_currency() -> str:
    return "usd"


@pytest.fixture(scope="session")
def unsubscribed_product_name() -> str:
    return 'Silver'


@pytest.fixture(scope="session")
def stripe_unsubscribed_product_id(unsubscribed_product_name, stripe_unsubscribed_product_url) -> str:
    products = stripe.Product.list(url=stripe_unsubscribed_product_url, active=True, limit=1)
    if products:
        product = products['data'][0]
    else:
        product = stripe.Product.create(name=unsubscribed_product_name, url=stripe_unsubscribed_product_url)
    return product['id']


@pytest.fixture(scope="session")
def stripe_price_id(stripe_subscription_product_id, stripe_price_currency) -> str:
    prices = stripe.Price.list(product=stripe_subscription_product_id, active=True, limit=1)
    if prices:
        price = prices.data[0]
    else:
        price = stripe.Price.create(
            unit_amount=129,
            currency=stripe_price_currency,
            recurring={"interval": "month"},
            product=stripe_subscription_product_id,
        )
    return price['id']


@pytest.fixture(scope="session")
def stripe_unsubscribed_price_id(stripe_unsubscribed_product_id, stripe_price_currency) -> str:
    prices = stripe.Price.list(product=stripe_unsubscribed_product_id, active=True, limit=1)
    if prices:
        price = prices.data[0]
    else:
        price = stripe.Price.create(
            unit_amount=9999,
            currency=stripe_price_currency,
            recurring={"interval": "year"},
            product=stripe_unsubscribed_product_id,
        )
    return price['id']


@pytest.fixture
def expected_subscription_prices(stripe_subscription_product_id, stripe_price_id, stripe_price_currency) -> List:
    return [
        {'id': stripe_price_id,
         'recurring': {
              "aggregate_usage": None,
              "interval": "month",
              "interval_count": 1,
              "trial_period_days": None,
              "usage_type": "licensed",
         },
         'type': 'recurring',
         'currency': stripe_price_currency,
         'unit_amount': 129,
         'unit_amount_decimal': '129',
         'nickname': None,
         'metadata': {},
         'product': stripe_subscription_product_id,
         'subscription_info': {'subscribed': True, 'cancel_at': None}}]



@pytest.fixture
def expected_subscription_prices_unsubscribed(stripe_subscription_product_id, stripe_price_id,
                                              stripe_price_currency) -> List:
    return [
        {'id': stripe_price_id,
         'recurring': {
              "aggregate_usage": None,
              "interval": "month",
              "interval_count": 1,
              "trial_period_days": None,
              "usage_type": "licensed",
         },
         'type': 'recurring',
         'currency': stripe_price_currency,
         'unit_amount': 129,
         'unit_amount_decimal': '129',
         'nickname': None,
         'metadata': {},
         'product': stripe_subscription_product_id,
         'subscription_info': {'subscribed': False, 'cancel_at': None}}]


@pytest.fixture
def expected_subscription_products_and_prices(stripe_subscription_product_id, stripe_price_id,
                                              subscribed_product_name, stripe_unsubscribed_product_id,
                                              unsubscribed_product_name, stripe_unsubscribed_price_id,
                                              stripe_subscription_product_url,
                                              stripe_unsubscribed_product_url,
                                              stripe_price_currency) -> List:
    return [
        {'id': stripe_unsubscribed_product_id,
         'images': [],
         'metadata': {},
         'name': unsubscribed_product_name,
            'prices': [{'currency': stripe_price_currency,
                  'id': stripe_unsubscribed_price_id,
                  'metadata': {},
                  'nickname': None,
                  'recurring': {'aggregate_usage': None,
                                'interval': 'year',
                                'interval_count': 1,
                                'trial_period_days': None,
                                'usage_type': 'licensed'},
                  'subscription_info': {'cancel_at': None, 'subscribed': False},
                  'type': 'recurring',
                  'unit_amount': 9999,
                  'unit_amount_decimal': '9999'}],
         'shippable': None,
         'subscription_info': {'cancel_at': None, 'subscribed': False},
         'type': 'service',
         'unit_label': None,
         'url': stripe_unsubscribed_product_url},
        {'id': stripe_subscription_product_id,
         'images': [],
         'type': 'service',
         'name': subscribed_product_name,
         'shippable': None,
         'unit_label': None,
         'url': stripe_subscription_product_url,
         'metadata': {},
         'prices': [{'id': stripe_price_id,
                     'recurring': {
                      "aggregate_usage": None,
                      "interval": "month",
                      "interval_count": 1,
                      "trial_period_days": None,
                      "usage_type": "licensed"
                    },
                     'type': 'recurring',
                     'currency': stripe_price_currency,
                     'unit_amount': 129,
                     'unit_amount_decimal': '129',
                     'nickname': None,
                     'metadata': {},
                     'subscription_info': {'subscribed': True, 'cancel_at': None}}],
         'subscription_info': {'subscribed': True, 'cancel_at': None}}
    ]


@pytest.fixture
def expected_subscription_products_and_prices_unsubscribed(stripe_subscription_product_id, stripe_price_id,
                                              subscribed_product_name, stripe_unsubscribed_product_id,
                                              unsubscribed_product_name, stripe_unsubscribed_price_id,
                                              stripe_subscription_product_url,
                                              stripe_unsubscribed_product_url,
                                              stripe_price_currency) -> List:
    return [
        {'id': stripe_unsubscribed_product_id,
         'images': [],
         'metadata': {},
         'name': unsubscribed_product_name,
            'prices': [{'currency': stripe_price_currency,
                  'id': stripe_unsubscribed_price_id,
                  'metadata': {},
                  'nickname': None,
                  'recurring': {'aggregate_usage': None,
                                'interval': 'year',
                                'interval_count': 1,
                                'trial_period_days': None,
                                'usage_type': 'licensed'},
                  'subscription_info': {'cancel_at': None, 'subscribed': False},
                  'type': 'recurring',
                  'unit_amount': 9999,
                  'unit_amount_decimal': '9999'}],
         'shippable': None,
         'subscription_info': {'cancel_at': None, 'subscribed': False},
         'type': 'service',
         'unit_label': None,
         'url': stripe_unsubscribed_product_url},
        {'id': stripe_subscription_product_id,
         'images': [],
         'type': 'service',
         'name': subscribed_product_name,
         'shippable': None,
         'unit_label': None,
         'url': stripe_subscription_product_url,
         'metadata': {},
         'prices': [{'id': stripe_price_id,
                     'recurring': {
                      "aggregate_usage": None,
                      "interval": "month",
                      "interval_count": 1,
                      "trial_period_days": None,
                      "usage_type": "licensed"
                    },
                     'type': 'recurring',
                     'currency': stripe_price_currency,
                     'unit_amount': 129,
                     'unit_amount_decimal': '129',
                     'nickname': None,
                     'metadata': {},
                     'subscription_info': {'subscribed': False, 'cancel_at': None}}],
         'subscription_info': {'subscribed': False, 'cancel_at': None}}
    ]


@pytest.fixture
def subscription_response() -> Dict[str, Any]:
    """current_period_end, current_period_start, id, latest_invoice and start_date
    have been removed as they are not consistent values"""
    return {'cancel_at': None,
             'days_until_due': None,
             'status': 'active',
             'trial_end': None,
            'trial_start': None}


@pytest.fixture
def non_existing_price_id() -> str:
    return 'price_1In1oOCz06et8VuzMAGHcXYZ'


@pytest.fixture
def non_existing_price_id_error(non_existing_price_id) -> Dict[str, str]:
    return {'detail': f"No such price: '{non_existing_price_id}'"}


@pytest.fixture
def non_existing_payment_method_error(non_existing_payment_method_id) -> Dict[str, str]:
    return {'detail': f"No such payment method: '{non_existing_payment_method_id}'"}


def get_payment_method_error(payment_method_id) -> Dict[str, str]:
    return {'detail': f"No such PaymentMethod: '{payment_method_id}'"}


@pytest.fixture
def non_existing_payment_method_error_2(non_existing_payment_method_id) -> Dict[str, str]:
    return get_payment_method_error(non_existing_payment_method_id)


@pytest.fixture
def non_existing_payment_method_error_other_user(default_payment_method_id) -> Dict[str, str]:
    return get_payment_method_error(default_payment_method_id)


@pytest.fixture
def non_existing_product_id() -> str:
    return 'prod_JPrXuHkkBJ3ABC'


@pytest.fixture
def non_existing_product_id_error(non_existing_product_id) -> Dict[str, str]:
    return {'detail': f"No such product: '{non_existing_product_id}'"}


@pytest.fixture
def non_existing_currency() -> str:
    return 'ABC'


@pytest.fixture
def non_existing_currency_error(non_existing_currency) -> str:
    return f"Invalid currency: {non_existing_currency.lower()}. Stripe currently supports these currencies:"

