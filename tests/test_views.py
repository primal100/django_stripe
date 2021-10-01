import pytest
from django_stripe import signals
from django_stripe.tests import make_request, get_expected_checkout_html


@pytest.mark.django_db
@pytest.mark.parametrize('viewname,url_params',
                         [('go-to-checkout', 'price_id'),
                          ('go-to-setup-checkout', None),
                          ('go-to-setup-checkout', 'subscription_id')
                          ], indirect=("url_params",))
def test_checkout(authenticated_client, stripe_unsubscribed_price_id, stripe_public_key,
                  checkout_session_data, viewname, url_params):
    response = make_request(authenticated_client.get,
                            viewname,
                            200,
                            signal=signals.checkout_created,
                            url_params=url_params)
    html = response.rendered_content
    assert stripe_public_key.startswith('pk')
    checkout_session = checkout_session_data['session']
    expected_html = get_expected_checkout_html(stripe_public_key, checkout_session["id"])
    assert html == expected_html


@pytest.mark.django_db
def test_billing_portal(authenticated_client, billing_portal_data):
    response = make_request(authenticated_client.get,
                            "go-to-billing-portal",
                            302,
                            signal=signals.billing_portal_created)
    billing_portal_session = billing_portal_data['session']
    assert response.url == billing_portal_session['url']
