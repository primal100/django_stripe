import json
from unittest.mock import Mock

import pytest
import stripe
from rest_framework.test import APIRequestFactory, force_authenticate

from django_stripe import payments, signals
from django_stripe.utils import resource_dict
from django_stripe.views import (
    StripeSubscriptionView, StripeInvoiceView, StripePaymentMethodView,
    StripeSetupIntentView, SubscriptionHistoryView,
)
from tests.django_stripe_testapp.models import User


def customer():
    return User(id=1, stripe_customer_id='cus_test')


def subscription(count=1):
    data = dict(id='sub_test', object='subscription', customer='cus_test',
                created=1, cancel_at=None, days_until_due=None,
                default_payment_method=None, latest_invoice='in_test',
                start_date=1, status='active', trial_start=None, trial_end=None)
    data['items'] = {'data': [
        dict(id=f'si_{i}', current_period_start=10 + i, current_period_end=20 + i,
             price=dict(id=f'price_{i}', product=f'prod_{i}'))
        for i in range(count)
    ]}
    return stripe.Subscription.construct_from(data, 'sk_test_offline')


def test_single_item_subscription_response():
    response = StripeSubscriptionView().make_response(subscription())
    assert response['price'] == 'price_0'
    assert response['product'] == 'prod_0'
    assert response['current_period_start'] == 10
    assert response['current_period_end'] == 20
    json.dumps(response)


def test_multiple_item_periods_are_not_conflated():
    response = StripeSubscriptionView().make_response(subscription(2))
    assert response['price'] is None
    assert response['current_period_end'] is None
    assert [item['current_period_end'] for item in response['items']] == [20, 21]


def test_payment_method_response_is_json_serializable():
    resource = stripe.PaymentMethod.construct_from(
        {'id': 'pm_test', 'object': 'payment_method', 'customer': 'cus_test',
         'customer_account': 'acct_private', 'shared_payment_granted_token': 'private_token',
         'card': {'last4': '4242'}, 'metadata': {}}, 'sk_test_offline')
    response = StripePaymentMethodView().make_response(resource)
    assert response == {'id': 'pm_test', 'card': {'last4': '4242'}}
    json.dumps(response)


@pytest.mark.parametrize('parent,expected', [
    (None, None),
    ({'subscription_details': {'subscription': 'sub_test'}}, 'sub_test'),
])
def test_invoice_subscription_location(parent, expected):
    data = dict.fromkeys(StripeInvoiceView.response_keys)
    del data['subscription']
    data.update(id='in_test', parent=parent)
    response = StripeInvoiceView().make_response(stripe.Invoice.construct_from(data, None))
    assert response['subscription'] == expected


@pytest.mark.parametrize('helper', [payments.create_setup_intent, payments.create_setup_checkout])
@pytest.mark.parametrize('kwargs,expected', [
    ({}, ['card']),
    ({'payment_method_types': ['sepa_debit']}, ['sepa_debit']),
    ({'allowed_payment_method_types': ['card']}, ['card']),
])
def test_supported_payment_method_parameters(monkeypatch, helper, kwargs, expected):
    create = Mock(return_value={'id': 'created'})
    resource = stripe.SetupIntent if helper is payments.create_setup_intent else stripe.checkout.Session
    monkeypatch.setattr(resource, 'create', create)
    helper(customer(), **kwargs)
    assert create.call_args.kwargs['allowed_payment_method_types'] == expected
    assert 'payment_method_types' not in create.call_args.kwargs


@pytest.mark.parametrize('helper', [payments.create_setup_intent, payments.create_setup_checkout])
def test_conflicting_parameter_names_rejected(helper):
    with pytest.raises(TypeError, match='not both'):
        helper(customer(), payment_method_types=['card'], allowed_payment_method_types=['card'])


def test_subscription_checkout_uses_supported_parameter(monkeypatch):
    monkeypatch.setattr(payments, 'retrieve_price', Mock())
    create = Mock(return_value={'id': 'cs_test'})
    monkeypatch.setattr(stripe.checkout.Session, 'create', create)
    payments.create_subscription_checkout(customer(), 'price_0')
    assert create.call_args.kwargs['allowed_payment_method_types'] == ['card']
    assert create.call_args.kwargs['line_items'] == [{'price': 'price_0', 'quantity': 1}]


@pytest.mark.parametrize('owned', [True, False])
def test_subscription_cancellation_checks_owner(monkeypatch, owned):
    sub = subscription()
    if not owned:
        sub['customer'] = 'cus_someone_else'
    monkeypatch.setattr(stripe.Subscription, 'retrieve', Mock(return_value=sub))
    cancel = Mock(return_value=sub)
    monkeypatch.setattr(stripe.Subscription, 'cancel', cancel)
    send = Mock()
    monkeypatch.setattr(signals, 'send_signal_on_delete', send)
    if owned:
        assert payments.delete(customer(), stripe.Subscription, 'sub_test') is sub
        cancel.assert_called_once_with('sub_test')
        send.assert_called_once()
    else:
        from subscriptions.exceptions import StripeWrongCustomer
        with pytest.raises(StripeWrongCustomer):
            payments.delete(customer(), stripe.Subscription, 'sub_test')
        cancel.assert_not_called()
        send.assert_not_called()


def test_stripe_exception_converted_to_api_response(monkeypatch):
    monkeypatch.setattr(stripe.SetupIntent, 'create', Mock(side_effect=stripe.InvalidRequestError('Bad request', 'field')))
    request = APIRequestFactory().post('/setup-intents', {}, format='json')
    force_authenticate(request, user=customer())
    response = StripeSetupIntentView.as_view()(request)
    assert response.status_code == 500
    assert str(response.data['detail']) == 'Bad request'


def test_history_with_no_subscription(monkeypatch):
    monkeypatch.setattr(payments, 'list_customer_resource', Mock(return_value=[]))
    view = SubscriptionHistoryView()
    request = APIRequestFactory().get('/')
    request.user = customer()
    view.setup(request)
    context = view.get_context_data()
    assert context['subscription'] is None


def test_subscription_price_filter_is_translated(monkeypatch):
    list_resources = Mock(return_value=[])
    monkeypatch.setattr(payments, 'list_customer_resource', list_resources)
    request = APIRequestFactory().get('/')
    request.user = customer()
    StripeSubscriptionView().list(request, price_id='price_test', status='active')
    list_resources.assert_called_once_with(request.user, stripe.Subscription, price='price_test', status='active')


@pytest.mark.parametrize('method,status_code', [('get', 200), ('post', 201), ('put', 200), ('delete', 200)])
def test_subscription_api_renders_sdk_resources(monkeypatch, method, status_code):
    sub = subscription()
    for operation in ('retrieve', 'create', 'modify', 'cancel'):
        monkeypatch.setattr(stripe.Subscription, operation, Mock(return_value=sub))
    request = getattr(APIRequestFactory(), method)('/subscriptions/sub_test/',
                                                   {'price_id': 'price_0'} if method == 'post' else {},
                                                   format='json')
    force_authenticate(request, user=customer())
    response = StripeSubscriptionView.as_view()(request, **({} if method == 'post' else {'obj_id': 'sub_test'}))
    assert response.status_code == status_code
    assert response.data['current_period_end'] == 20
    response.render()
    assert json.loads(response.content)['price'] == 'price_0'


def test_history_renders_multiple_items(monkeypatch):
    from django.template.loader import render_to_string
    sub = subscription(2)
    for item in sub['items']['data']:
        item['price']['currency'] = 'eur'
        item['price']['unit_amount'] = 1200
        item['price']['recurring'] = {'interval': 'month'}
    monkeypatch.setattr(payments, 'list_customer_resource',
                        lambda user, resource: [sub] if resource is stripe.Subscription else [])
    view = SubscriptionHistoryView()
    request = APIRequestFactory().get('/')
    request.user = customer()
    view.setup(request)
    html = render_to_string(view.template_name, view.get_context_data())
    assert html.count('eur 1200 / month') == 2
