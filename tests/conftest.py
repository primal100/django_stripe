import os

import sys
import pytest
from pytest_django.live_server_helper import LiveServer
import stripe
from stripe.error import InvalidRequestError
from unittest import mock

from urllib.parse import urljoin
from django.dispatch import Signal
from django_stripe import payments, signals
from django_stripe.tests import signal_mock, get_url
from seleniumlogin import force_login
import subscriptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tests.django_stripe_testapp.models import User

from typing import List, Dict, Any, Optional

python_version = sys.version_info
ci_string = f'{os.name}-{python_version.major}{python_version.minor}'


def pytest_addoption(parser):
    parser.addoption("--apikey", action="store", default=os.environ.get('STRIPE_TEST_SECRET_KEY'))
    parser.addoption("--publickey", action="store", default=os.environ.get('STRIPE_TEST_PUBLIC_KEY'))


@pytest.fixture(scope="session", autouse=True)
def stripe_api_key(pytestconfig):
    stripe.api_key = pytestconfig.getoption("apikey")
    return stripe_api_key


@pytest.fixture(scope="session", autouse=True)
def stripe_public_key(pytestconfig):
    return pytestconfig.getoption("publickey")


@pytest.fixture(autouse=True)
def setup_settings(stripe_api_key, stripe_public_key, settings):
    settings.STRIPE_API_KEY = stripe_api_key
    settings.STRIPE_PUBLIC_KEY = stripe_public_key


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
def authenticated_client(api_client, user_with_customer_id):
    api_client.force_login(user_with_customer_id)
    return api_client


@pytest.fixture
def authenticated_client_with_customer_id(api_client, user_with_customer_id):
    api_client.force_login(user_with_customer_id)
    return api_client


@pytest.fixture
def authenticated_client_second_user(api_client, second_user):
    api_client.force_login(second_user)
    return api_client


@pytest.fixture(params=[('no-user', 'second-user')])
def authenticated_client_no_user_or_second_user(request, api_client, second_user):
    if request.param == 'second-user':
        api_client.force_login(second_user)
    return api_client


@pytest.fixture
def authenticated_client_with_without_customer_id(api_client, user_with_and_without_customer_id):
    api_client.force_login(user_with_and_without_customer_id)
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
def default_payment_method_retrieved(default_payment_method_from_api) -> stripe.PaymentMethod:
    del default_payment_method_from_api['default']
    return default_payment_method_from_api


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
def subscription(user_with_customer_id, stripe_price_id, default_payment_method_id) -> stripe.Subscription:
    return subscriptions.create_subscription(user_with_customer_id, stripe_price_id)


@pytest.fixture
def non_existing_subscription_id(user_with_customer_id) -> str:
    return 'sub_ABCD1234'


def get_no_such_subscription_error(subscription_id) -> Dict[str, str]:
    return {'detail': f"No such subscription: '{subscription_id}'"}


@pytest.fixture
def no_such_subscription_error(non_existing_subscription_id) -> Dict[str, str]:
    return get_no_such_subscription_error(non_existing_subscription_id)


@pytest.fixture
def not_owned_subscription_error(subscription) -> Dict[str, str]:
    return get_no_such_subscription_error(subscription['id'])


@pytest.fixture(params=[('no-filters', 'all-filters')])
def invoice_filters(request, subscription) -> Dict[str, Any]:
    if request.param == 'no-filters':
        return {}
    return {'subscription': subscription['id'], 'status': 'paid'}


@pytest.fixture
def invoice(user_with_customer_id, subscription) -> stripe.Invoice:
    return stripe.Invoice.list(customer=user_with_customer_id.stripe_customer_id).data[0]


@pytest.fixture
def non_existing_invoice_id() -> str:
    return 'in_ABCD123456'


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
def subscription_response(default_payment_method_id) -> Dict[str, Any]:
    """current_period_end, current_period_start, id, latest_invoice and start_date
    have been removed as they are not consistent values"""
    return {'cancel_at': None,
            'days_until_due': None,
            'default_payment_method': default_payment_method_id,
            'status': 'active',
            'trial_end': None,
            'trial_start': None}


@pytest.fixture
def subscription_response_alternative_payment_method(subscription_response, payment_method_id) -> Dict[str, Any]:
    """current_period_end, current_period_start, id, latest_invoice and start_date
    have been removed as they are not consistent values"""
    subscription_response['default_payment_method'] = payment_method_id
    return subscription_response


@pytest.fixture
def non_existing_price_id() -> str:
    return 'price_1In1oOCz06et8VuzMAGHcXYZ'


@pytest.fixture
def non_existing_price_id_error(non_existing_price_id) -> Dict[str, str]:
    return {'detail': f"No such price: '{non_existing_price_id}'"}


def get_invoice_error(invoice_id: str) -> Dict[str, Any]:
    return {'detail': f"No such invoice: '{invoice_id}'"}


@pytest.fixture
def invoice_not_owned_error(invoice) -> Dict[str, str]:
    return get_invoice_error(invoice['id'])


@pytest.fixture
def invoice_not_exist_error(non_existing_invoice_id) -> Dict[str, str]:
    return get_invoice_error(non_existing_invoice_id)


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
def no_default_payment_method_error() -> Dict[str, str]:
    return {'detail': 'This customer has no attached payment source or default payment method.'}


@pytest.fixture
def no_default_payment_method_to_set_as_default_error() -> Dict[str, List[str]]:
    return {'non_field_errors': ['The default_payment_method field must be set if set_as_default_payment_method is True.']}


@pytest.fixture
def customer_default_payment_method_or_none(request, payment_method_id) -> Optional[str]:
    if request.param == 'payment_method_id':
        return payment_method_id
    return None


@pytest.fixture
def customer_default_payment_methods(request, default_payment_method_id, payment_method_id) -> Optional[str]:
    if request.param == 'default_payment_method_id':
        return default_payment_method_id
    return payment_method_id


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


def get_data_from_signal(signal: Signal) -> Dict[str, Any]:
    data_holder = {}

    def receiver(**kwargs):
        data_holder.update(kwargs)

    signal.connect(receiver)

    yield data_holder


@pytest.fixture
def checkout_session_data() -> Dict[str, Any]:
    yield from get_data_from_signal(signals.checkout_created)


@pytest.fixture
def billing_portal_data() -> Dict[str, Any]:
    yield from get_data_from_signal(signals.billing_portal_created)


@pytest.fixture
def url_params(request, stripe_unsubscribed_price_id, subscription) -> Optional[Dict[str, str]]:
    if request.param == 'price_id':
        return {'price_id': stripe_unsubscribed_price_id}
    if request.param == 'subscription_id':
        return {'subscription_id': subscription['id']}
    return None


@pytest.fixture
def selenium(selenium: WebDriver, live_server: LiveServer) -> WebDriver:
    selenium.maximize_window()
    return selenium


def get_full_url(base_url: str, view: str, **url_params: Dict[str, Any]) -> str:
    return urljoin(base_url, str(get_url(view, **url_params)))


def selenium_go_to_view(selenium: WebDriver, live_server: LiveServer, view: str,
                        **kwargs: Dict[str, Any]) -> WebDriver:
    url = get_full_url(live_server.url, view, **kwargs)
    selenium.get(url)
    return selenium


def selenium_go_to_view_wait_stripe(selenium: WebDriver, live_server: LiveServer, view: str,
                                    **kwargs) -> WebDriver:
    selenium = selenium_go_to_view(selenium, live_server, view, **kwargs)
    wait = WebDriverWait(selenium, 10)
    wait.until(EC.url_contains("stripe.com"))
    return selenium


@pytest.fixture
def selenium_authenticated(selenium: WebDriver, live_server: LiveServer, user) -> WebDriver:
    force_login(user, selenium, live_server.url)
    return selenium


@pytest.fixture
def selenium_go_to_checkout(selenium_authenticated: WebDriver, live_server: LiveServer,
                            stripe_price_id: str) -> WebDriver:
    return selenium_go_to_view_wait_stripe(
        selenium_authenticated, live_server, "go-to-checkout", price_id=stripe_price_id)


@pytest.fixture
def selenium_go_to_setup_checkout(selenium_authenticated: WebDriver, live_server: LiveServer) -> WebDriver:
    return selenium_go_to_view_wait_stripe(selenium_authenticated, live_server, "go-to-setup-checkout")


@pytest.fixture
def selenium_go_to_setup_checkout_subscription(selenium_authenticated: WebDriver, live_server: LiveServer,
                                               subscription: stripe.Subscription) -> WebDriver:
    return selenium_go_to_view_wait_stripe(selenium_authenticated,
                                           live_server, "go-to-setup-checkout", subscription_id=subscription["id"])


@pytest.fixture
def selenium_go_to_billing_portal(selenium_authenticated: WebDriver, live_server: LiveServer) -> WebDriver:
    return selenium_go_to_view_wait_stripe(selenium_authenticated, live_server, "go-to-billing-portal")
