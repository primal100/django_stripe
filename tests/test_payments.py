import pytest
import stripe
from django_stripe import payments
from django_stripe import signals
from django_stripe.tests import assert_customer_id_exists, assert_signal_called, assert_customer_email


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
def test_modify_customer_on_save_update(user_with_customer_id, user_alternative_email, update_fields):
    user_with_customer_id.email = user_alternative_email
    user_with_customer_id.save(update_fields=update_fields)
    assert_customer_email(user_with_customer_id, user_alternative_email)


@pytest.mark.django_db
def test_modify_customer_on_save_no_update(user_with_customer_id, user_alternative_email, user_email):
    user_with_customer_id.email = user_alternative_email
    user_with_customer_id.save(update_fields=('first_name',))
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
def test_checkout(user_with_and_without_customer_id, stripe_unsubscribed_price_id):
    session = payments.create_checkout(user_with_and_without_customer_id, stripe_unsubscribed_price_id)
    assert session["id"]
    assert_signal_called(signals.checkout_created)
    assert_customer_id_exists(user_with_and_without_customer_id)


@pytest.mark.django_db
def test_billing_portal(user_with_and_without_customer_id):
    session = payments.create_billing_portal(user_with_and_without_customer_id)
    assert "stripe.com" in session["url"]
    assert_signal_called(signals.billing_portal_created)
    assert_customer_id_exists(user_with_and_without_customer_id)


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
