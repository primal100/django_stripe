import os

import sys
import pytest
import stripe

import subscriptions
from subscriptions import UserProtocol
from tests.django_stripe_testapp.models import User

from typing import List

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


@pytest.fixture(scope="session")
def stripe_subscription_product_url() -> str:
    return "http://localhost/paywall"


@pytest.fixture(scope="session")
def stripe_unsubscribed_product_url() -> str:
    return "http://localhost/second_paywall"


@pytest.fixture(scope="session")
def checkout_success_url(settings) -> str:
    return "http://localhost"


@pytest.fixture(scope="session")
def checkout_cancel_url() -> str:
    return "http://localhost/cancel"


@pytest.fixture
def user_email() -> str:
    return f'stripe-subscriptions-{ci_string}@example.com'


@pytest.fixture
def user(user_email) -> UserProtocol:
    user = User(id=1, email=user_email, first_name='Test', last_name="User")
    user.save()
    yield user
    if user.stripe_customer_id and stripe.Customer.retrieve(user.stripe_customer_id):
        subscriptions.delete_customer(user)


@pytest.fixture
def user_with_customer_id(user, user_email) -> UserProtocol:
    customers = stripe.Customer.list(email=user_email)
    for customer in customers:
        stripe.Customer.delete(customer['id'])
    subscriptions.create_customer(user, description="stripe-subscriptions test runner user")
    return user


@pytest.fixture
def subscribed_user(user_with_customer_id, stripe_price_id) -> UserProtocol:
    subscriptions.tests.create_payment_method(user_with_customer_id)
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
def stripe_price_id(stripe_subscription_product_id) -> str:
    prices = stripe.Price.list(product=stripe_subscription_product_id, active=True, limit=1)
    if prices:
        price = prices.data[0]
    else:
        price = stripe.Price.create(
            unit_amount=129,
            currency="usd",
            recurring={"interval": "month"},
            product=stripe_subscription_product_id,
        )
    return price['id']


@pytest.fixture(scope="session")
def stripe_unsubscribed_price_id(stripe_unsubscribed_product_id) -> str:
    prices = stripe.Price.list(product=stripe_unsubscribed_product_id, active=True, limit=1)
    if prices:
        price = prices.data[0]
    else:
        price = stripe.Price.create(
            unit_amount=9999,
            currency="usd",
            recurring={"interval": "year"},
            product=stripe_unsubscribed_product_id,
        )
    return price['id']


@pytest.fixture
def expected_subscription_prices(stripe_subscription_product_id, stripe_price_id) -> List:
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
         'currency': 'usd',
         'unit_amount': 129,
         'unit_amount_decimal': '129',
         'nickname': None,
         'metadata': {},
         'product': stripe_subscription_product_id,
         'subscription_info': {'subscribed': True, 'cancel_at': None}}]


@pytest.fixture
def expected_subscription_products_and_prices(stripe_subscription_product_id, stripe_price_id,
                                              subscribed_product_name, stripe_unsubscribed_product_id,
                                              unsubscribed_product_name, stripe_unsubscribed_price_id,
                                              stripe_subscription_product_url,
                                              stripe_unsubscribed_product_url) -> List:
    return [
        {'id': stripe_unsubscribed_product_id,
         'images': [],
         'metadata': {},
         'name': unsubscribed_product_name,
            'prices': [{'currency': 'usd',
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
                     'currency': 'usd',
                     'unit_amount': 129,
                     'unit_amount_decimal': '129',
                     'nickname': None,
                     'metadata': {},
                     'subscription_info': {'subscribed': True, 'cancel_at': None}}],
         'subscription_info': {'subscribed': True, 'cancel_at': None}}
    ]
