import pytest
import stripe
import subscriptions
from django.core import exceptions
from django_stripe import payments
from django_stripe import signals
from django_stripe.tests import assert_customer_id_exists, assert_signal_called, assert_customer_email, assert_customer_description


@pytest.mark.django_db
def test_create_customer(user_with_and_without_customer_id, mock_customer_retrieve):
    payments.create_customer(user_with_and_without_customer_id)
    assert_customer_id_exists(user_with_and_without_customer_id)
    assert_signal_called(signals.new_customer)
    stripe.Customer.retrieve.assert_not_called()


@pytest.mark.django_db
def test_modify_customer(user_with_customer_id, user_alternative_email):
    payments.modify_customer(user_with_customer_id, email=user_alternative_email)
    assert_customer_email(user_with_customer_id, user_alternative_email)


@pytest.mark.django_db
@pytest.mark.parametrize('update_fields', [None, ('email',)])
def test_modify_customer_on_save_email_update(user_with_customer_id, user_alternative_email, update_fields):
    user_with_customer_id.email = user_alternative_email
    user_with_customer_id.save(update_fields=update_fields)
    assert_customer_email(user_with_customer_id, user_alternative_email)


@pytest.mark.django_db
@pytest.mark.parametrize('update_fields', [None, ('first_name',)])
def test_modify_customer_on_save_first_name_update(user_with_customer_id, update_fields):
    assert_customer_description(user_with_customer_id, "Test User")
    user_with_customer_id.first_name = "John"
    user_with_customer_id.save(update_fields=update_fields)
    assert_customer_description(user_with_customer_id, "John User")


@pytest.mark.django_db
def test_modify_customer_on_save_no_update(user_with_customer_id, user_alternative_email, user_email):
    user_with_customer_id.email = user_alternative_email
    user_with_customer_id.save(update_fields=('is_active',))
    assert_customer_email(user_with_customer_id, user_email)


@pytest.mark.django_db
@pytest.mark.parametrize('update_fields', [None, ('email',)])
def test_modify_non_customer(user, user_alternative_email, update_fields):
    user.email = user_alternative_email
    user.save(update_fields=update_fields)
    assert user.email == user_alternative_email
    assert not user.stripe_customer_id


@pytest.mark.django_db
def test_modify_customer_setting_disabled(user_with_customer_id, user_alternative_email, user_email,
                                          disable_keep_customer_email_updated):
    user_with_customer_id.email = user_alternative_email
    user_with_customer_id.save()
    assert_customer_email(user_with_customer_id, user_email)


@pytest.mark.django_db
def test_subscription_checkout(user_with_and_without_customer_id, stripe_unsubscribed_price_id):
    session = payments.create_subscription_checkout(user_with_and_without_customer_id, stripe_unsubscribed_price_id)
    assert session["id"]
    assert session['setup_intent'] is None
    assert_signal_called(signals.checkout_created)
    assert_customer_id_exists(user_with_and_without_customer_id)


@pytest.mark.django_db
def test_setup_checkout(user_with_and_without_customer_id):
    session = payments.create_setup_checkout(user_with_and_without_customer_id)
    assert session["id"]
    assert session['setup_intent'] is not None
    assert_signal_called(signals.checkout_created)
    assert_customer_id_exists(user_with_and_without_customer_id)


@pytest.mark.django_db
def test_billing_portal(user_with_and_without_customer_id):
    session = payments.create_billing_portal(user_with_and_without_customer_id)
    assert "stripe.com" in session["url"]
    assert_signal_called(signals.billing_portal_created)
    assert_customer_id_exists(user_with_and_without_customer_id)


@pytest.mark.django_db
def test_product_list_subscribed(user_with_customer_id, stripe_subscription_product_id, stripe_unsubscribed_product_id,
                                 subscription, expected_subscription_products_and_prices):
    result = payments.get_products(user_with_customer_id, ids=[stripe_subscription_product_id,
                                                               stripe_unsubscribed_product_id])
    assert result == expected_subscription_products_and_prices


@pytest.mark.django_db
def test_product_retrieve(user_with_customer_id, stripe_subscription_product_id, stripe_unsubscribed_product_id,
                          subscription, expected_subscription_products_and_prices):
    result = payments.retrieve_product(user_with_customer_id, stripe_subscription_product_id)
    assert result == expected_subscription_products_and_prices[1]
    result = payments.retrieve_product(user_with_customer_id, stripe_unsubscribed_product_id)
    assert result == expected_subscription_products_and_prices[0]


@pytest.mark.django_db
def test_product_restricted_product(user_with_customer_id, stripe_subscription_product_id,
                                    stripe_unsubscribed_product_id, subscription, restrict_products,
                                    expected_subscription_products_and_prices,
                                    expected_restricted_product):
    result = payments.get_products(user_with_customer_id)
    assert result == expected_restricted_product
    result = payments.retrieve_product(user_with_customer_id, stripe_subscription_product_id)
    assert result == expected_restricted_product[0]
    with pytest.raises(exceptions.PermissionDenied):
        payments.retrieve_product(user_with_customer_id, stripe_unsubscribed_product_id)


@pytest.mark.django_db
def test_product_list_unsubscribed(no_user_and_user_with_and_without_customer_id,
                                   stripe_subscription_product_id,
                                   stripe_unsubscribed_product_id,
                                   expected_subscription_products_and_prices_unsubscribed):
    result = payments.get_products(no_user_and_user_with_and_without_customer_id,
                                   ids=[stripe_subscription_product_id,
                                        stripe_unsubscribed_product_id])
    assert result == expected_subscription_products_and_prices_unsubscribed


@pytest.mark.django_db
def test_price_list_subscribed(user_with_customer_id, stripe_subscription_product_id, stripe_unsubscribed_product_id,
                               expected_subscription_prices, subscription):
    result = payments.get_prices(user_with_customer_id, product=stripe_subscription_product_id)
    assert result == expected_subscription_prices
    result = payments.get_prices(user_with_customer_id, product=stripe_unsubscribed_product_id)
    assert len(result) == 1


@pytest.mark.django_db
def test_price_list_unsubscribed(no_user_and_user_with_and_without_customer_id, stripe_subscription_product_id,
                                 expected_subscription_prices_unsubscribed):
    result = payments.get_prices(no_user_and_user_with_and_without_customer_id,
                                 product=stripe_subscription_product_id)
    assert result == expected_subscription_prices_unsubscribed


@pytest.mark.django_db
def test_price_retrieve(user_with_customer_id, stripe_price_id,
                        expected_subscription_prices, subscription):
    result = payments.retrieve_price(user_with_customer_id, stripe_price_id)
    assert result == expected_subscription_prices[0]


@pytest.mark.django_db
def test_price_list_restrict_products(user_with_customer_id, stripe_subscription_product_id, restrict_products,
                                      stripe_unsubscribed_product_id, expected_subscription_prices, subscription,
                                      stripe_price_id, stripe_unsubscribed_price_id):
    result = payments.get_prices(user_with_customer_id, product=stripe_subscription_product_id)
    assert result == expected_subscription_prices
    with pytest.raises(exceptions.PermissionDenied):
        payments.get_prices(user_with_customer_id, product=stripe_unsubscribed_product_id)
    result = payments.retrieve_price(user_with_customer_id, stripe_price_id)
    assert result == expected_subscription_prices[0]
    with pytest.raises(exceptions.PermissionDenied):
        payments.retrieve_price(user_with_customer_id, stripe_unsubscribed_price_id)


@pytest.mark.django_db
def test_new_setup_intent(user_with_and_without_customer_id):
    setup_intent = payments.create_setup_intent(user_with_and_without_customer_id)
    assert setup_intent['id'] is not None
    assert setup_intent['client_secret'] is not None
    assert setup_intent['payment_method_types'] == ['card']


@pytest.mark.django_db
def test_modify_default_payment_method(user_with_customer_id, payment_method_id):
    customer = stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)
    assert customer['invoice_settings']['default_payment_method'] is None
    payments.modify_payment_method(user_with_customer_id, payment_method_id, set_as_default=True)
    customer = stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)
    assert customer['invoice_settings']['default_payment_method'] == payment_method_id


@pytest.mark.django_db
def test_list_payment_methods(user_with_customer_id, default_payment_method_saved, payment_method_saved):
    payment_methods = list(payments.list_payment_methods(user_with_customer_id))
    default_payment_method_saved['default'] = True
    payment_method_saved['default'] = False
    assert payment_methods == [payment_method_saved, default_payment_method_saved]


@pytest.mark.django_db
def test_detach_payment_method(user_with_customer_id, default_payment_method_saved):
    payment_method = payments.detach_payment_method(user_with_customer_id, default_payment_method_saved['id'])
    assert not payment_method['customer']
    assert list(payments.list_payment_methods(user_with_customer_id)) == []


@pytest.mark.django_db
def test_detach_all_payment_methods(user_with_customer_id, default_payment_method_saved):
    payment_methods = payments.detach_all_payment_methods(user_with_customer_id, types=["card"])
    default_payment_method_saved["customer"] = None
    assert payment_methods == [default_payment_method_saved]
    payment_method = stripe.PaymentMethod.retrieve(default_payment_method_saved["id"])
    assert payment_method["customer"] is None


@pytest.mark.django_db
def test_create_subscription(user_with_customer_id, payment_method_id, default_payment_method_id,
                             stripe_price_id, stripe_subscription_product_id):
    payments.create_subscription(user_with_customer_id, stripe_price_id, default_payment_method=payment_method_id)
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_customer_id, stripe_subscription_product_id)
    assert response['subscribed'] is True
    assert response['cancel_at'] is None
    customer = stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)
    assert customer['invoice_settings']['default_payment_method'] == default_payment_method_id


@pytest.mark.django_db
def test_modify_subscription_payment_method(user_with_customer_id, subscription,
                                            payment_method_id, default_payment_method_id):
    assert subscription['default_payment_method'] is None
    payments.modify_subscription(user_with_customer_id, subscription['id'],
                                 default_payment_method=payment_method_id)
    sub = stripe.Subscription.retrieve(subscription['id'])
    assert sub['default_payment_method'] == payment_method_id
    customer = stripe.Customer.retrieve(user_with_customer_id.stripe_customer_id)
    assert customer['invoice_settings']['default_payment_method'] == default_payment_method_id


@pytest.mark.django_db
def test_cancel_subscription(user_with_customer_id, subscription, stripe_subscription_product_id):
    payments.delete(user_with_customer_id, stripe.Subscription, subscription['id'])
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_customer_id, stripe_subscription_product_id)
    assert response['subscribed'] is False
    assert response['cancel_at'] is None


@pytest.mark.django_db
def test_list_subscription(user_with_customer_id, subscription):
    subs = payments.list_customer_resource(user_with_customer_id, stripe.Subscription)
    assert subs == [subscription]


@pytest.mark.django_db
def test_invoice_list(user_with_customer_id, subscription):
    invoices = payments.list_customer_resource(user_with_customer_id, stripe.Invoice)
    invoice = invoices[0]
    assert invoice['billing_reason'] == 'subscription_create'
    assert invoice['customer'] == user_with_customer_id.stripe_customer_id
    assert invoice['hosted_invoice_url']
    assert invoice['invoice_pdf']


@pytest.mark.django_db
def test_invoice_list_none(user_with_and_without_customer_id):
    invoices = payments.list_customer_resource(user_with_and_without_customer_id, stripe.Invoice)
    assert invoices == []


@pytest.mark.django_db
def test_is_subscribed(user_with_customer_id, subscription, stripe_subscription_product_id, stripe_price_id):
    is_subscribed = payments.is_subscribed_and_cancelled_time(user_with_customer_id, stripe_subscription_product_id)
    assert is_subscribed['subscribed'] is True
    assert is_subscribed['cancel_at'] is None
    assert is_subscribed['evaluation'] is False
    assert is_subscribed['price_id'] == stripe_price_id
    assert subscriptions.is_subscribed(user_with_customer_id, stripe_subscription_product_id)


@pytest.mark.django_db
def test_is_subscribed_allowed_access_until(user_allowed_access_until, subscription, stripe_subscription_product_id):
    is_subscribed = payments.is_subscribed_and_cancelled_time(user_allowed_access_until)
    assert is_subscribed == {'subscribed': True, 'cancel_at': None, 'current_period_end': 1924905599,
                             'evaluation': True, 'product_id': stripe_subscription_product_id,
                             'price_id': None}
    assert subscriptions.is_subscribed(user_allowed_access_until, stripe_subscription_product_id)


@pytest.mark.django_db
def test_is_not_subscribed(no_user_and_user_with_and_without_customer_id, stripe_subscription_product_id, stripe_price_id):
    is_subscribed = payments.is_subscribed_and_cancelled_time(no_user_and_user_with_and_without_customer_id,
                                                              stripe_subscription_product_id)
    assert is_subscribed == {'subscribed': False, 'cancel_at': None, 'current_period_end': None,
                             'evaluation': False, 'product_id': None,
                             'price_id': None}
    assert subscriptions.is_subscribed(no_user_and_user_with_and_without_customer_id,
                                       stripe_subscription_product_id) is False


@pytest.mark.django_db
def test_is_subscribed_with_cache(user_with_customer_id, subscription, stripe_subscription_product_id, django_cache):
    cache_key = f'is_subscribed_{user_with_customer_id.id}_{stripe_subscription_product_id}'
    assert django_cache.get(cache_key) is None
    subscribed = payments.is_subscribed_with_cache(user_with_customer_id, stripe_subscription_product_id)
    assert subscribed is True
    assert django_cache.get(cache_key) is True
    subscribed = payments.is_subscribed_with_cache(user_with_customer_id, stripe_subscription_product_id)
    assert subscribed is True


@pytest.mark.django_db
def test_user_is_not_subscribed_with_cache(user_with_and_without_customer_id, django_cache, stripe_subscription_product_id):
    cache_key = f'is_subscribed_{user_with_and_without_customer_id.id}_{stripe_subscription_product_id}'
    subscribed = payments.is_subscribed_with_cache(user_with_and_without_customer_id,
                                                   product_id=stripe_subscription_product_id)
    assert subscribed is False
    assert django_cache.get(cache_key) is None
    subscribed = payments.is_subscribed_with_cache(user_with_and_without_customer_id,
                                                   product_id=stripe_subscription_product_id)
    assert subscribed is False
