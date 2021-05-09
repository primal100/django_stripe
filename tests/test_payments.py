import pytest
import stripe
import subscriptions
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
def test_modify_customer_on_save_first_name_update(user_with_customer_id, user_alternative_email, update_fields):
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
def test_price_list_subscribed(subscribed_user, stripe_subscription_product_id, expected_subscription_prices):
    result = payments.get_subscription_prices(subscribed_user, product=stripe_subscription_product_id)
    assert result == expected_subscription_prices


@pytest.mark.django_db
def test_price_list_unsubscribed(no_user_and_user_with_and_without_customer_id, stripe_subscription_product_id,
                                 expected_subscription_prices_unsubscribed):
    result = payments.get_subscription_prices(no_user_and_user_with_and_without_customer_id,
                                              product=stripe_subscription_product_id)
    assert result == expected_subscription_prices_unsubscribed


@pytest.mark.django_db
def test_product_list_subscribed(subscribed_user, stripe_subscription_product_id, stripe_unsubscribed_product_id,
                                 expected_subscription_products_and_prices):
    result = payments.get_subscription_products(subscribed_user, ids=[stripe_subscription_product_id,
                                                                      stripe_unsubscribed_product_id])
    assert result == expected_subscription_products_and_prices


@pytest.mark.django_db
def test_product_list_unsubscribed(no_user_and_user_with_and_without_customer_id,
                                   stripe_subscription_product_id,
                                   stripe_unsubscribed_product_id,
                                   expected_subscription_products_and_prices_unsubscribed):
    result = payments.get_subscription_products(no_user_and_user_with_and_without_customer_id,
                                                ids=[stripe_subscription_product_id,
                                                     stripe_unsubscribed_product_id])
    assert result == expected_subscription_products_and_prices_unsubscribed


@pytest.mark.django_db
def test_list_payment_intents(user_with_customer_id, stripe_price_id):
    payment_intents = payments.list_payment_intents(user_with_customer_id)
    assert payment_intents['data'] == []
    #session = payments.create_checkout(user_with_customer_id, stripe_price_id)


@pytest.mark.django_db
def test_new_subscription(user_with_payment_method, stripe_price_id, stripe_subscription_product_id):
    payments.create_subscription(user_with_payment_method, stripe_price_id)
    response = subscriptions.is_subscribed_and_cancelled_time(user_with_payment_method, stripe_subscription_product_id)
    assert response['subscribed'] is True
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
