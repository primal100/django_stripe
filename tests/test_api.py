import pytest
from django_stripe.tests import assert_customer_id_exists, make_request
from django_stripe import signals


@pytest.mark.django_db
def test_checkout(authenticated_client, user, stripe_unsubscribed_price_id):
    response = make_request(authenticated_client.post,
                            'checkout',
                            200,
                            signal=signals.checkout_created,
                            price_id=stripe_unsubscribed_price_id)
    assert list(response.data.keys()) == ['sessionId']
    assert response.data['sessionId']
    assert_customer_id_exists(user)


@pytest.mark.django_db
def test_billing_portal(authenticated_client, user):
    response = make_request(authenticated_client.post,
                            'billing',
                            200,
                            signal=signals.billing_portal_created)
    assert list(response.data.keys()) == ['sessionId']
    assert "stripe.com" in response.data["url"]
    assert_customer_id_exists(user)


@pytest.mark.django_db
@pytest.mark.parametrize('method,view', [('post', 'checkout'), ('post', 'billing')])
def test_unauthenticated_post(client, method, view):
    method = getattr(client, method)
    response = make_request(method,
                            view,
                            403)
    assert response.data == {'detail': 'Authentication credentials were not provided.'}


@pytest.mark.django_db
def test_price_list(client):
    response = make_request(client.get, 'prices', 200)
    assert response.data == []


@pytest.mark.django_db
def test_product_list():
    pass


@pytest.mark.django_db
def test_new_subscription():
    pass


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
