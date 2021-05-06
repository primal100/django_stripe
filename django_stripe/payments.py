import stripe
import subscriptions
from functools import wraps
from .settings import django_stripe_settings as settings
from rest_framework.exceptions import NotAuthenticated
from . import signals
from .utils import get_actual_user
from typing import List, Dict, Any


def add_stripe_customer_if_not_existing(f):
    @wraps(f)
    def wrapper(user, *args, **kwargs):
        user = create_customer(user)
        return f(user, *args, **kwargs)
    return wrapper


@get_actual_user
def create_customer(user, **kwargs):
    kwargs = kwargs or {}
    if not user or not user.is_authenticated:
        raise NotAuthenticated('This stripe method requires a logged in user')
    if not user.stripe_customer_id:
        customer_kwargs = settings.STRIPE_NEW_CUSTOMER_GET_KWARGS(**kwargs)
        customer = subscriptions.create_customer(user, **customer_kwargs)
        user.save(update_fields=('stripe_customer_id',))
        signals.new_customer.send(sender=user, customer=customer)
    return user


@get_actual_user
@subscriptions.decorators.customer_id_required
def modify_customer(user, **kwargs):
    customer = stripe.Customer.modify(user.stripe_customer_id, **kwargs)
    signals.customer_modified.send(sender=user, customer=customer)
    return customer


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
    session = subscriptions.create_subscription_checkout(**checkout_kwargs)
    signals.checkout_created.send(sender=user, session=session)
    return session


@add_stripe_customer_if_not_existing
def create_billing_portal(user) -> stripe.billing_portal.Session:
    return_url = settings.STRIPE_BILLING_PORTAL_RETURN_URL
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url
    )
    signals.billing_portal_created.send(sender=user, session=session)
    return session


@get_actual_user
def get_subscription_products(user, ids: List[str], price_kwargs: Dict[str, Any] = None,
                              **kwargs) -> List[Dict[str, Any]]:
    return subscriptions.get_subscription_products_and_prices(user, ids=ids, price_kwargs=price_kwargs, **kwargs)


@get_actual_user
def get_subscription_prices(user, product: str = None, currency: str = None, **kwargs) -> List[Dict[str, Any]]:
    return subscriptions.get_subscription_prices(user, product=product, currency=currency, **kwargs)


@get_actual_user
@subscriptions.decorators.customer_id_required
def create_subscription(user, price_id: str, **kwargs) -> stripe.Subscription:
    subscription = subscriptions.create_subscription(user, price_id, **kwargs)
    signals.subscription_created.send(sender=user, subscription=subscription)
    return subscription
