import pytest
from django_stripe.tests import assert_customer_id_exists, make_request
from django_stripe import signals
import subscriptions


@pytest.mark.django_db
def test_checkout(authenticated_client_with_without_customer_id, user, stripe_unsubscribed_price_id):
    response = make_request(authenticated_client_with_without_customer_id.post,
                            'checkout',
                            200,
                            signal=signals.checkout_created,
                            price_id=stripe_unsubscribed_price_id)
    assert list(response.data.keys()) == ['sessionId']
    assert response.data['sessionId']
    assert_customer_id_exists(user)


@pytest.mark.django_db
def test_checkout_non_existing_price(authenticated_client_with_without_customer_id, user,
                                     non_existing_price_id):
    response = make_request(authenticated_client_with_without_customer_id.post,
                            'checkout',
                            400,
                            price_id=non_existing_price_id)
    assert response.data == ''
    assert_customer_id_exists(user)


@pytest.mark.django_db
def test_billing_portal(authenticated_client_with_without_customer_id, user):
    response = make_request(authenticated_client_with_without_customer_id.post,
                            'billing',
                            200,
                            signal=signals.billing_portal_created)
    assert list(response.data.keys()) == ['url']
    assert "stripe.com" in response.data["url"]
    assert_customer_id_exists(user)


@pytest.mark.django_db
@pytest.mark.parametrize('method,view', [('post', 'checkout'), ('post', 'billing')])
def test_unauthenticated_post(api_client, method, view):
    method = getattr(api_client, method)
    response = make_request(method,
                            view,
                            403)
    assert response.data == {'detail': 'Authentication credentials were not provided.'}


@pytest.mark.django_db
def test_price_list(client_no_user_and_user_with_and_without_stripe_id, expected_subscription_prices_unsubscribed, stripe_subscription_product_id,
                    stripe_price_currency):
    response = make_request(client_no_user_and_user_with_and_without_stripe_id.get, 'prices', 200,
                            product=stripe_subscription_product_id,
                            currency=stripe_price_currency)
    assert response.data == expected_subscription_prices_unsubscribed


@pytest.mark.django_db
def test_price_list_subscribed(authenticated_client_with_subscribed_user, expected_subscription_prices,
                               stripe_subscription_product_id, stripe_price_currency):
    response = make_request(authenticated_client_with_subscribed_user.get, 'prices', 200,
                            product=stripe_subscription_product_id)
    assert response.data == expected_subscription_prices


@pytest.mark.django_db
def test_product_list(client_no_user_and_user_with_and_without_stripe_id, expected_subscription_products_and_prices_unsubscribed,
                      stripe_subscription_product_id, stripe_unsubscribed_product_id):
    response = make_request(client_no_user_and_user_with_and_without_stripe_id.get, 'products', 200,
                            ids=[stripe_subscription_product_id,
                                 stripe_unsubscribed_product_id])
    assert response.data == expected_subscription_products_and_prices_unsubscribed


@pytest.mark.django_db
def test_product_list_subscribed(authenticated_client_with_subscribed_user, expected_subscription_products_and_prices,
                                 stripe_subscription_product_id, stripe_unsubscribed_product_id):
    response = make_request(authenticated_client_with_subscribed_user.get, 'products', 200,
                            ids=[stripe_subscription_product_id,
                                 stripe_unsubscribed_product_id])
    assert response.data == expected_subscription_products_and_prices


@pytest.mark.django_db
def test_new_subscription(authenticated_client_with_payment_method, stripe_price_id, stripe_subscription_product_id,
                          user_with_payment_method, subscription_response):
    response = make_request(authenticated_client_with_payment_method.post, "subscriptions", 201,
                            signal=signals.subscription_created, price_id=stripe_price_id)
    assert response.data.pop('current_period_end')
    assert response.data.pop('current_period_start')
    assert response.data.pop('id')
    assert response.data.pop('latest_invoice')
    assert response.data.pop('start_date')
    assert response.data == subscription_response
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_payment_method, stripe_subscription_product_id)
    assert response['subscribed'] is True
    assert response['cancel_at'] is None


@pytest.mark.django_db
def test_new_subscription_no_customer_id(client_no_user_and_without_stripe_id,
                                         no_user_or_user,
                                         stripe_price_id,
                                         stripe_subscription_product_id,
                                         subscription_response,
                                         permission_error):
    response = make_request(client_no_user_and_without_stripe_id.post, "subscriptions", 403,
                            price_id=stripe_price_id)
    assert response.data == {'detail': permission_error}
    response = subscriptions.is_subscribed_and_cancelled_time(no_user_or_user,
                                                              stripe_subscription_product_id)
    assert response['subscribed'] is False
    assert response['cancel_at'] is None


@pytest.mark.django_db
def test_update_subscription():
    pass


@pytest.mark.django_db
def test_cancel_subscription():
    pass


@pytest.mark.django_db
def test_list_subscription():
    pass


@pytest.mark.django_db
def test_check_subscription():
    pass


@pytest.mark.django_db
def test_invoice_list():
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
