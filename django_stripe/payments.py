import stripe
import subscriptions
from functools import wraps
from .settings import django_stripe_settings as settings
from . import signals
from .utils import get_user_if_token_user


def create_customer(user, **kwargs):
    kwargs = kwargs or {}
    user = get_user_if_token_user(user)
    if not user.stripe_customer_id:
        customer_kwargs = settings.STRIPE_CHECKOUT_GET_KWARGS(**kwargs)
        customer = subscriptions.create_customer(user, **customer_kwargs)
        user.save(update_fields=('stripe_customer_id',))
        signals.new_customer.send(sender=user, customer=customer)
    return user


def modify_customer(user, **kwargs):
    user = get_user_if_token_user(user)
    if not user.stripe_customer_id:
        raise subscriptions.exceptions.StripeCustomerIdRequired
    customer = stripe.Customer.modify(user.stripe_customer_id, **kwargs)
    signals.customer_modified.send(sender=user, customer=customer)
    return customer


def add_stripe_customer_if_not_existing(f):
    @wraps(f)
    def wrapper(user, *args, **kwargs):
        user = create_customer(user)
        return f(user, *args, **kwargs)
    return wrapper


@add_stripe_customer_if_not_existing
def create_checkout(user: subscriptions.types.UserProtocol, price_id: str, **kwargs) -> stripe.checkout.Session:
    checkout_kwargs = {
        'user': user,
        'price_id': price_id,
        'client_reference_id': user.id,
        'success_url': settings.STRIPE_CHECKOUT_SUCCESS_URL,
        'cancel_url': settings.STRIPE_CHECKOUT_CANCEL_URL,
        'payment_method_types': settings.STRIPE_PAYMENT_METHOD_TYPES
    }
    checkout_kwargs.update(**kwargs)
    checkout_kwargs = settings.STRIPE_CHECKOUT_GET_KWARGS(**checkout_kwargs)
    session = subscriptions.create_subscription_checkout(**checkout_kwargs)
    signals.checkout_created.send(sender=user, session=session)
    return session


@add_stripe_customer_if_not_existing
def create_billing_portal(user: subscriptions.types.UserProtocol) -> stripe.billing_portal.Session:
    return_url = settings.STRIPE_BILLING_PORTAL_RETURN_URL
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url
    )
    signals.billing_portal_created.send(sender=user, session=session)
    return session
