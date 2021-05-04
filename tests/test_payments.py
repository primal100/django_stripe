import pytest
from django_stripe import payments


@pytest.mark.django_db
def test_checkout(user, stripe_unsubscribed_price_id):
    session = payments.create_checkout(user, stripe_unsubscribed_price_id)
    assert session["id"]


@pytest.mark.django_db
def test_billing_portal(user):
    session = payments.create_billing_portal(user)
    assert "stripe.com" in session["url"]


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
def test_price_list():
    pass


@pytest.mark.django_db
def test_product_list():
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
