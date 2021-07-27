import pytest
import stripe

from django_stripe.tests import assert_customer_id_exists, make_request
from django_stripe import signals
import subscriptions


@pytest.mark.django_db
def test_subscription_checkout(authenticated_client_with_without_customer_id, user, stripe_unsubscribed_price_id):
    response = make_request(authenticated_client_with_without_customer_id.post,
                            'checkout',
                            201,
                            signal=signals.checkout_created,
                            url_params={'price_id': stripe_unsubscribed_price_id})
    assert list(response.data.keys()) == ['id']
    assert response.data['id']
    assert_customer_id_exists(user)


@pytest.mark.django_db
def test_setup_checkout(authenticated_client_with_without_customer_id, user, stripe_unsubscribed_price_id):
    response = make_request(authenticated_client_with_without_customer_id.post,
                            'setup-checkout',
                            201,
                            signal=signals.checkout_created)
    assert list(response.data.keys()) == ['id']
    assert response.data['id']
    assert_customer_id_exists(user)


@pytest.mark.django_db
def test_checkout_non_existing_price(authenticated_client_with_without_customer_id, user,
                                     non_existing_price_id, non_existing_price_id_error):
    response = make_request(authenticated_client_with_without_customer_id.post,
                            'checkout',
                            500,
                            url_params={'price_id': non_existing_price_id})
    assert response.data == non_existing_price_id_error
    assert_customer_id_exists(user)


@pytest.mark.django_db
def test_billing_portal(authenticated_client_with_without_customer_id, user):
    response = make_request(authenticated_client_with_without_customer_id.post,
                            'billing',
                            201,
                            signal=signals.billing_portal_created)
    assert list(response.data.keys()) == ['url']
    assert "stripe.com" in response.data["url"]
    assert_customer_id_exists(user)


@pytest.mark.django_db
@pytest.mark.parametrize('method,view,price_id_as_url_params', [
    ('post', 'checkout', True),
    ('post', 'setup-checkout', False),
    ('get', 'payment-methods', False),
    ('post', 'billing', False),
    ('get', 'invoices', False),
    ('post', 'subscriptions', False),
    ('get', 'subscriptions', False),
    ('post', 'setup-intents', False)
])
def test_unauthenticated(api_client, method, view, price_id_as_url_params, stripe_price_id):
    method = getattr(api_client, method)
    url_params = {'price_id': stripe_price_id} if price_id_as_url_params else None
    response = make_request(method,
                            view,
                            403,
                            url_params=url_params)
    assert response.data == {'detail': 'Authentication credentials were not provided.'}


@pytest.mark.django_db
def test_price_list(client_no_user_and_user_with_and_without_stripe_id, expected_subscription_prices_unsubscribed, stripe_subscription_product_id,
                    stripe_price_currency):
    response = make_request(client_no_user_and_user_with_and_without_stripe_id.get, 'prices', 200,
                            product=stripe_subscription_product_id,
                            currency=stripe_price_currency)
    assert response.data == expected_subscription_prices_unsubscribed


@pytest.mark.django_db
def test_price_list_subscribed(authenticated_client_with_customer_id, expected_subscription_prices,
                               stripe_subscription_product_id, subscription):
    response = make_request(authenticated_client_with_customer_id.get, 'prices', 200,
                            product=stripe_subscription_product_id)
    assert response.data == expected_subscription_prices


@pytest.mark.django_db
def test_price_list_non_existing_product(client, non_existing_product_id, non_existing_product_id_error):
    response = make_request(client.get, 'prices', 500,
                            product=non_existing_product_id)
    assert response.data == non_existing_product_id_error


@pytest.mark.django_db
def test_price_list_non_existing_currency(client, non_existing_currency, non_existing_currency_error):
    response = make_request(client.get, 'prices', 500,
                            currency="ABC")
    assert response.data['detail'].startswith(non_existing_currency_error)


@pytest.mark.django_db
def test_price_get_one(client_no_user_and_user_with_and_without_stripe_id,
                       expected_subscription_prices_unsubscribed, stripe_price_id):
    response = make_request(client_no_user_and_user_with_and_without_stripe_id.get, 'prices', 200,
                            url_params={'id': stripe_price_id})
    assert response.data == expected_subscription_prices_unsubscribed[0]


@pytest.mark.django_db
def test_product_list(client_no_user_and_user_with_and_without_stripe_id,
                      expected_subscription_products_and_prices_unsubscribed,
                      stripe_subscription_product_id, stripe_unsubscribed_product_id):
    response = make_request(client_no_user_and_user_with_and_without_stripe_id.get, 'products', 200,
                            ids=[stripe_subscription_product_id,
                                 stripe_unsubscribed_product_id])
    assert response.data == expected_subscription_products_and_prices_unsubscribed


@pytest.mark.django_db
def test_product_get_one(client_no_user_and_user_with_and_without_stripe_id,
                         expected_subscription_products_and_prices_unsubscribed, stripe_subscription_product_id):
    response = make_request(client_no_user_and_user_with_and_without_stripe_id.get, 'products', 200,
                            url_params={'id': stripe_subscription_product_id})
    assert response.data == expected_subscription_products_and_prices_unsubscribed[1]


@pytest.mark.django_db
def test_product_list_subscribed(authenticated_client_with_customer_id, expected_subscription_products_and_prices,
                                 stripe_subscription_product_id, stripe_unsubscribed_product_id,
                                 subscription):
    response = make_request(authenticated_client_with_customer_id.get, 'products', 200,
                            ids=[stripe_subscription_product_id,
                                 stripe_unsubscribed_product_id])
    assert response.data == expected_subscription_products_and_prices


@pytest.mark.django_db
def test_product_list_non_existing_product(client, non_existing_product_id):
    response = make_request(client.get, 'products', 200,
                            ids=[non_existing_product_id])
    assert response.data == []


@pytest.mark.django_db
def test_new_setup_intent(authenticated_client_with_without_customer_id):
    response = make_request(authenticated_client_with_without_customer_id.post, "setup-intents", 201,
                            signal=signals.setup_intent_created)
    data = response.data
    assert data['id']
    assert data['client_secret']
    assert data['payment_method_types'] == ['card']


@pytest.mark.django_db
def test_list_payment_methods(authenticated_client_with_customer_id, default_payment_method_from_api,
                              payment_method_from_api):
    response = make_request(authenticated_client_with_customer_id.get, "payment-methods", 200)
    data = response.data
    assert data == [default_payment_method_from_api, payment_method_from_api]


@pytest.mark.django_db
def test_get_one_payment_method(authenticated_client_with_customer_id, default_payment_method_retrieved):
    response = make_request(authenticated_client_with_customer_id.get, "payment-methods", 200,
                            url_params={'id': default_payment_method_retrieved['id']})
    data = response.data
    assert data == default_payment_method_retrieved


@pytest.mark.django_db
def test_change_default_payment_method(authenticated_client_with_customer_id,
                                       user_with_customer_id,
                                       default_payment_method_from_api,
                                       payment_method_from_api):
    pm_id = payment_method_from_api['id']
    response = make_request(authenticated_client_with_customer_id.put, "payment-methods", 200,
                            url_params={'id': pm_id}, set_as_default=True)
    data = response.data
    payment_method_from_api.pop('default')
    assert data == payment_method_from_api
    assert stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)['invoice_settings']['default_payment_method'] == pm_id


@pytest.mark.django_db
def test_change_default_payment_method_non_existing(authenticated_client_with_customer_id,
                                                    non_existing_payment_method_id,
                                                    non_existing_payment_method_error_2):
    response = make_request(authenticated_client_with_customer_id.put, "payment-methods", 500,
                            url_params={'id': non_existing_payment_method_id})
    assert response.data == non_existing_payment_method_error_2


@pytest.mark.django_db
def test_detach_payment_method(authenticated_client_with_customer_id,
                               payment_method_from_api,
                               default_payment_method_from_api):
    response = make_request(authenticated_client_with_customer_id.delete, "payment-methods", 204,
                            url_params={'id': default_payment_method_from_api['id']})
    assert response.data is None


@pytest.mark.django_db
def test_detach_payment_method_all(authenticated_client_with_customer_id,
                                   payment_method_from_api,
                                   default_payment_method_from_api):
    response = make_request(authenticated_client_with_customer_id.delete, "payment-methods", 204,
                            url_params={'id': "*"})
    assert response.data is None


@pytest.mark.django_db
def test_detach_no_payment_method(authenticated_client_with_customer_id,
                                  non_existing_payment_method_id,
                                  non_existing_payment_method_error_2):
    response = make_request(authenticated_client_with_customer_id.delete, "payment-methods", 500,
                            url_params={'id': non_existing_payment_method_id})
    assert response.data == non_existing_payment_method_error_2


@pytest.mark.django_db
def test_detach_other_user_payment_method(authenticated_client_second_user,
                                          default_payment_method_id,
                                          non_existing_payment_method_error_other_user):
    response = make_request(authenticated_client_second_user.delete, "payment-methods", 500,
                            url_params={'id': default_payment_method_id})
    assert response.data == non_existing_payment_method_error_other_user


@pytest.mark.django_db
@pytest.mark.parametrize('data,customer_default_payment_method_or_none',
                         [({}, None),
                         ({'set_as_default_payment_method': True}, 'payment_method_id')],
                         indirect=('customer_default_payment_method_or_none',))
def test_new_subscription(authenticated_client_with_customer_id, stripe_price_id, stripe_subscription_product_id,
                          payment_method_id, user_with_customer_id, subscription_response, data,
                          customer_default_payment_method_or_none):
    response = make_request(authenticated_client_with_customer_id.post, "subscriptions", 201,
                            signal=signals.subscription_created, price_id=stripe_price_id,
                            default_payment_method=payment_method_id, **data)
    assert response.data.pop('current_period_end') is not None
    assert response.data.pop('current_period_start') is not None
    assert response.data.pop('id') is not None
    assert response.data.pop('latest_invoice') is not None
    assert response.data.pop('start_date') is not None
    assert response.data == subscription_response
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_customer_id, stripe_subscription_product_id)
    assert response['subscribed'] is True
    assert response['cancel_at'] is None
    customer = stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)
    assert customer['invoice_settings']['default_payment_method'] == customer_default_payment_method_or_none


@pytest.mark.django_db
def test_new_subscription_change_default_payment_method_with_no_payment_method(
        authenticated_client_with_customer_id, stripe_price_id,
        stripe_subscription_product_id, user_with_customer_id, no_default_payment_method_to_set_as_default_error):
    response = make_request(authenticated_client_with_customer_id.post, "subscriptions", 400,
                            price_id=stripe_price_id, set_as_default_payment_method=True)
    assert response.data == no_default_payment_method_to_set_as_default_error
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_customer_id, stripe_subscription_product_id)
    assert response['subscribed'] is False
    assert response['cancel_at'] is None
    customer = stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)
    assert customer['invoice_settings']['default_payment_method'] == None


@pytest.mark.django_db
def test_new_subscription_no_price_id(authenticated_client_with_customer_id, non_existing_price_id,
                                      stripe_subscription_product_id, payment_method_id, non_existing_price_id_error):
    response = make_request(authenticated_client_with_customer_id.post, "subscriptions", 500,
                            price_id=non_existing_price_id, default_payment_method=payment_method_id)
    assert response.data == non_existing_price_id_error


@pytest.mark.django_db
def test_new_subscription_non_existing_payment_method(authenticated_client_with_customer_id, stripe_price_id,
                                                      stripe_subscription_product_id, non_existing_payment_method_id,
                                                      non_existing_payment_method_error_2):
    response = make_request(authenticated_client_with_customer_id.post, "subscriptions", 500,
                            price_id=stripe_price_id, default_payment_method=non_existing_payment_method_id)
    assert response.data == non_existing_payment_method_error_2


@pytest.mark.django_db
def test_new_subscription_no_payment_method(authenticated_client_with_customer_id, user_with_customer_id,
                                            stripe_price_id, stripe_subscription_product_id,
                                            no_default_payment_method_error):
    response = make_request(authenticated_client_with_customer_id.post, "subscriptions", 500,
                            price_id=stripe_price_id)
    assert response.data == no_default_payment_method_error
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_customer_id,
                                                              stripe_subscription_product_id)
    assert response['subscribed'] is False
    assert response['cancel_at'] is None


@pytest.mark.django_db
@pytest.mark.parametrize('data,customer_default_payment_methods',
                         [({}, 'default_payment_method_id'),
                         ({'set_as_default_payment_method': True}, 'payment_method_id')],
                         indirect=('customer_default_payment_methods',))
def test_modify_subscription(authenticated_client_with_customer_id, stripe_subscription_product_id,
                             payment_method_id, user_with_customer_id, subscription,
                             subscription_response_alternative_payment_method,
                             data, customer_default_payment_methods):
    response = make_request(authenticated_client_with_customer_id.put, "subscriptions", 200,
                            signal=signals.subscription_modified, url_params={'id': subscription['id']},
                            default_payment_method=payment_method_id, **data)
    assert response.data.pop('current_period_end') is not None
    assert response.data.pop('current_period_start') is not None
    assert response.data.pop('id') is not None
    assert response.data.pop('latest_invoice') is not None
    assert response.data.pop('start_date') is not None
    assert response.data == subscription_response_alternative_payment_method
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_customer_id, stripe_subscription_product_id)
    assert response['subscribed'] is True
    assert response['cancel_at'] is None
    customer = stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)
    assert customer['invoice_settings']['default_payment_method'] == customer_default_payment_methods


@pytest.mark.django_db
def test_modify_subscription_change_default_payment_method_with_no_payment_method(
        authenticated_client_with_customer_id, subscription, default_payment_method_id,
        user_with_customer_id, no_default_payment_method_to_set_as_default_error):
    response = make_request(authenticated_client_with_customer_id.post, "subscriptions", 400,
                            set_as_default_payment_method=True)
    assert response.data == no_default_payment_method_to_set_as_default_error
    customer = stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)
    assert customer['invoice_settings']['default_payment_method'] == default_payment_method_id


@pytest.mark.django_db
def test_modify_subscription_non_existing_payment_method(authenticated_client_with_customer_id,
                                                         non_existing_payment_method_id,
                                                         non_existing_payment_method_error_2, subscription):
    response = make_request(authenticated_client_with_customer_id.put, "subscriptions", 500,
                            url_params={'id': subscription['id']},
                            default_payment_method=non_existing_payment_method_id)
    assert response.data == non_existing_payment_method_error_2


@pytest.mark.django_db
def test_modify_non_existing_subscription(authenticated_client_with_customer_id,
                                          stripe_subscription_product_id, payment_method_id,
                                          non_existing_subscription_id, no_such_subscription_error):
    response = make_request(authenticated_client_with_customer_id.put, "subscriptions", 500,
                            url_params={'id': non_existing_subscription_id},
                            default_payment_method=payment_method_id)
    assert response.data == no_such_subscription_error


@pytest.mark.django_db
def test_modify_other_user_subscription(authenticated_client_second_user,
                                        stripe_subscription_product_id, payment_method_id,
                                        subscription, not_owned_subscription_error):
    response = make_request(authenticated_client_second_user.put, "subscriptions", 500,
                            url_params={'id': subscription['id']},
                            default_payment_method=payment_method_id)
    assert response.data == not_owned_subscription_error


@pytest.mark.django_db
def test_delete_subscription(authenticated_client_with_customer_id, stripe_subscription_product_id,
                             user_with_customer_id, subscription):
    response = make_request(authenticated_client_with_customer_id.delete, "subscriptions", 204,
                            signal=signals.subscription_cancelled, url_params={'id': subscription['id']})
    assert response.data is None
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_customer_id, stripe_subscription_product_id)
    assert response['subscribed'] is False
    assert response['cancel_at'] is None


@pytest.mark.django_db
def test_delete_non_existing_subscription(authenticated_client_with_customer_id,
                                          non_existing_subscription_id, no_such_subscription_error):
    response = make_request(authenticated_client_with_customer_id.delete, "subscriptions", 500,
                            url_params={'id': non_existing_subscription_id})
    assert response.data == no_such_subscription_error


@pytest.mark.django_db
def test_delete_other_user_subscription(authenticated_client_second_user, user_with_customer_id,
                                        stripe_subscription_product_id, payment_method_id,
                                        subscription, not_owned_subscription_error):
    response = make_request(authenticated_client_second_user.delete, "subscriptions", 500,
                            url_params={'id': subscription['id']})
    assert response.data == not_owned_subscription_error
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_customer_id, stripe_subscription_product_id)
    assert response['subscribed'] is True
    assert response['cancel_at'] is None


@pytest.mark.django_db
def test_invoice_list(authenticated_client_with_customer_id, invoice_filters):
    response = make_request(authenticated_client_with_customer_id.get, "invoices", 200, **invoice_filters)
    invoice = response.data[0]
    assert invoice["status"] == 'paid'
    assert invoice['billing_reason'] == 'subscription_create'
    assert invoice['hosted_invoice_url']
    assert invoice['invoice_pdf']
    assert tuple(invoice.keys()) == ('id', "amount_due", "amount_paid", "amount_remaining", "billing_reason", "created",
                                     "hosted_invoice_url", "invoice_pdf", "next_payment_attempt", "status",
                                     "subscription")


@pytest.mark.django_db
def test_invoice_list_none_for_filter(authenticated_client_with_customer_id, subscription):
    response = make_request(authenticated_client_with_customer_id.get, "invoices", 200, status="open")
    assert response.data == []


@pytest.mark.django_db
def test_invoice_list_none_for_non_existing_subscription(authenticated_client_with_customer_id,
                                                                non_existing_subscription_id,
                                                                no_such_subscription_error):
    response = make_request(authenticated_client_with_customer_id.get, "invoices", 500,
                            subscription=non_existing_subscription_id)
    assert response.data == no_such_subscription_error


@pytest.mark.django_db
def test_invoice_list_none_for_user(authenticated_client_second_user, subscription):
    response = make_request(authenticated_client_second_user.get, "invoices", 200)
    assert response.data == []


@pytest.mark.django_db
def test_invoice_get_one(authenticated_client_with_customer_id, invoice):
    response = make_request(authenticated_client_with_customer_id.get, "invoices", 200,
                            url_params={'id': invoice['id']})
    data = response.data
    assert data['hosted_invoice_url'] == invoice['hosted_invoice_url']
    assert tuple(data.keys()) == ('id', "amount_due", "amount_paid", "amount_remaining", "billing_reason",
                                  "created","hosted_invoice_url", "invoice_pdf",  "next_payment_attempt", "status",
                                  "subscription")


@pytest.mark.django_db
def test_invoice_get_one_wrong_user(authenticated_client_second_user, invoice, invoice_not_owned_error):
    response = make_request(authenticated_client_second_user.get, "invoices", 500,
                            url_params={'id': invoice['id']})
    assert response.data == invoice_not_owned_error


@pytest.mark.django_db
def test_non_existing_invoice(authenticated_client_with_customer_id, non_existing_invoice_id, invoice_not_exist_error):
    response = make_request(authenticated_client_with_customer_id.get, "invoices", 500,
                            url_params={'id': non_existing_invoice_id})
    assert response.data == invoice_not_exist_error


@pytest.mark.django_db
def test_list_subscriptions(authenticated_client_with_customer_id, subscription):
    response = make_request(authenticated_client_with_customer_id.get, "subscriptions", 200)
    assert response.data == []


@pytest.mark.django_db
def test_get_one_subscription(authenticated_client_with_customer_id, subscription):
    response = make_request(authenticated_client_with_customer_id.get, "subscriptions", 200,
                            url_params={'id': subscription['id']})
    assert response.data == []


@pytest.mark.django_db
def test_check_subscription():
    pass


@pytest.mark.django_db
def test_view_subscribed_permission():
    pass


@pytest.mark.django_db
def test_view_not_subscribed_permission():
    pass


@pytest.mark.django_db
def test_user_change_email():
    pass
