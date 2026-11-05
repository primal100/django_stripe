import pytest
import stripe


@pytest.fixture(scope='session', autouse=True)
def stripe_subscription_product_id():
    return 'prod_test'


@pytest.fixture(scope='session')
def stripe_public_key():
    return 'pk_test_offline'


@pytest.fixture(autouse=True)
def set_default_product_id(settings):
    settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID = 'prod_test'
    settings.STRIPE_PUBLISHABLE_KEY = 'pk_test_offline'


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def fail(*args, **kwargs):
        pytest.fail('Offline regression tests must not call Stripe')
    monkeypatch.setattr(stripe._api_requestor._APIRequestor, 'request', fail)
