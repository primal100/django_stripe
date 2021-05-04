import stripe
import subscriptions
from django.conf import settings
import django.dispatch
from .utils import add_stripe_customer_if_not_existing


checkout_created = django.dispatch.Signal()
billing_portal_created = django.dispatch.Signal()


app_name = 'django-stripe'
app_url = "https://github.com/primal100/django_stripe"


stripe.set_app_info(app_name, version=version, url=app_url)
stripe.api_key = settings.STRIPE_API_KEY


@add_stripe_customer_if_not_existing
def create_checkout(user: subscriptions.types.UserProtocol, price_id: str) -> stripe.checkout.Session:
    kwargs = {
        'user': user,
        'price_id': price_id,
        'client_reference_id': user.id,
        'success_url': settings.STRIPE_CHECKOUT_SUCCESS_URL,
        'cancel_url': settings.STRIPE_CHECKOUT_CANCEL_URL,
    }
    kwargs = getattr(settings, 'STRIPE_CHECKOUT_GET_KWARGS', lambda **x: x)(**kwargs)
    session = subscriptions.create_subscription_checkout(**kwargs)
    checkout_created.send(sender=user, session=session)
    return session


@add_stripe_customer_if_not_existing
def create_billing_portal(user: subscriptions.types.UserProtocol) -> stripe.billing_portal.Session:
    return_url = getattr(settings, 'STRIPE_BILLING_PORTAL_RETURN_URL', None)
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url
    )
    billing_portal_created.send(sender=user, session=session)
    return session
