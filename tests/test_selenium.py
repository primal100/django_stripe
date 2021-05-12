import time

import stripe


def test_checkout(checkout_session_data, selenium_go_to_checkout):
    time.sleep(60)


def test_setup_checkout(checkout_session_data, selenium_go_to_setup_checkout):
    session = checkout_session_data['session']
    setup_intent = stripe.SetupIntent.retrieve(session['setup_intent'])
    assert 'subscription_id' not in setup_intent['metadata'] == {}


def test_setup_checkout_subscription(checkout_session_data, subscription,
                                     selenium_go_to_setup_checkout_subscription):
    session = checkout_session_data['session']
    setup_intent = stripe.SetupIntent.retrieve(session['setup_intent'])
    assert setup_intent['metadata']['subscription_id'] == subscription['id']
    time.sleep(60)


def test_billing_portal(billing_portal_data, selenium_go_to_billing_portal):
    time.sleep(60)
