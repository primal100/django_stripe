import stripe


def test_checkout(checkout_session_data, selenium_go_to_checkout):
    session = checkout_session_data['session']
    assert selenium_go_to_checkout.current_url.startswith(f"https://checkout.stripe.com/pay/{session['id']}")


def test_setup_checkout(checkout_session_data, selenium_go_to_setup_checkout):
    session = checkout_session_data['session']
    assert selenium_go_to_setup_checkout.current_url.startswith(f"https://checkout.stripe.com/pay/{session['id']}")
    setup_intent = stripe.SetupIntent.retrieve(session['setup_intent'])
    assert 'subscription_id' not in setup_intent['metadata'] == {}


def test_setup_checkout_subscription(checkout_session_data, subscription,
                                     selenium_go_to_setup_checkout_subscription):
    session = checkout_session_data['session']
    assert selenium_go_to_setup_checkout_subscription.current_url.startswith(
        f"https://checkout.stripe.com/pay/{session['id']}")
    setup_intent = stripe.SetupIntent.retrieve(session['setup_intent'])
    assert setup_intent['metadata']['subscription_id'] == subscription['id']


def test_billing_portal(billing_portal_data, selenium_go_to_billing_portal):
    session = billing_portal_data['session']
    assert selenium_go_to_billing_portal.current_url == session["url"]

