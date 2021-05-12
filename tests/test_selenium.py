import time


def test_checkout(checkout_session_data, selenium_go_to_checkout):
    time.sleep(60)


def test_setup_checkout(checkout_session_data, selenium_go_to_setup_checkout):
    time.sleep(60)


def test_setup_checkout_subscription(checkout_session_data, selenium_go_to_setup_checkout_subscription):
    print(checkout_session_data['session'])


def test_billing_portal(billing_portal_data, selenium_go_to_billing_portal):
    time.sleep(60)
