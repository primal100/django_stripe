import stripe
import subscriptions
from subscriptions.types import PaymentMethodType
from functools import wraps
from .conf import settings
from rest_framework.exceptions import NotAuthenticated
from . import signals
from .utils import get_actual_user, user_description
from typing import List, Dict, Any, Callable, Generator


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
        customer = subscriptions.create_customer(user, description=user_description(user), **customer_kwargs)
        user.save(update_fields=('stripe_customer_id',))
        signals.new_customer.send(sender=user, customer=customer)
    return user


@get_actual_user
@subscriptions.decorators.customer_id_required
def modify_customer(user, **kwargs) -> stripe.Customer:
    customer = stripe.Customer.modify(user.stripe_customer_id, **kwargs)
    signals.customer_modified.send(sender=user, customer=customer)
    return customer


@get_actual_user
@subscriptions.decorators.customer_id_required
def modify_default_payment_method(user, payment_method_id: str) -> stripe.Customer:
    return modify_customer(user, invoice_settings={
        'default_payment_method': payment_method_id})


@add_stripe_customer_if_not_existing
def create_checkout(user: subscriptions.types.UserProtocol, method: Callable, **kwargs) -> stripe.checkout.Session:
    checkout_kwargs = {
        'user': user,
        'client_reference_id': user.id,
        'success_url': settings.STRIPE_CHECKOUT_SUCCESS_URL,
        'cancel_url': settings.STRIPE_CHECKOUT_CANCEL_URL,
        'payment_method_types': settings.STRIPE_PAYMENT_METHOD_TYPES
    }
    checkout_kwargs.update(**kwargs)
    session = method(**checkout_kwargs)
    signals.checkout_created.send(sender=user, session=session)
    return session


def create_subscription_checkout(user: subscriptions.types.UserProtocol, price_id: str, **kwargs) -> stripe.checkout.Session:
    return create_checkout(user, subscriptions.create_subscription_checkout, price_id=price_id, **kwargs)


def create_setup_checkout(user: subscriptions.types.UserProtocol, **kwargs) -> stripe.checkout.Session:
    return create_checkout(user, method=subscriptions.create_setup_checkout, **kwargs)


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
def get_subscription_products(user, ids: List[str] = None, price_kwargs: Dict[str, Any] = None,
                              **kwargs) -> List[Dict[str, Any]]:
    return subscriptions.get_subscription_products_and_prices(user, ids=ids, price_kwargs=price_kwargs, **kwargs)


@get_actual_user
def get_subscription_prices(user, product: str = None, currency: str = None, **kwargs) -> List[Dict[str, Any]]:
    return subscriptions.get_subscription_prices(user, product=product, currency=currency, **kwargs)


@get_actual_user
@add_stripe_customer_if_not_existing
def create_setup_intent(user, **kwargs) -> stripe.SetupIntent:
    setup_intent_kwargs = {
        'customer': user.stripe_customer_id,
        'payment_method_types': settings.STRIPE_PAYMENT_METHOD_TYPES,
        'confirm': False,
        'usage': "off_session"}
    setup_intent_kwargs.update(kwargs)
    setup_intent = stripe.SetupIntent.create(**setup_intent_kwargs)
    signals.setup_intent_created.send(sender=user, setup_intent=setup_intent)
    return setup_intent


@get_actual_user
def list_payment_methods(user, types: List[PaymentMethodType] = None, **kwargs) -> Generator[stripe.PaymentMethod, None, None]:
    types = types or settings.STRIPE_PAYMENT_METHOD_TYPES
    return subscriptions.list_payment_methods(user, types, **kwargs)


@get_actual_user
def detach_payment_method(user, payment_method_id: str) -> stripe.PaymentMethod:
    payment_method = subscriptions.detach_payment_method(user, payment_method_id)
    signals.payment_method_detached.send(sender=user, payment_methods=[payment_method])
    return payment_method


@get_actual_user
def detach_all_payment_methods(user, types: List[PaymentMethodType] = None, **kwargs) -> List[stripe.PaymentMethod]:
    types = types or settings.STRIPE_PAYMENT_METHOD_TYPES
    payment_methods = subscriptions.detach_all_payment_methods(user, types, **kwargs)
    if payment_methods:
        signals.payment_method_detached.send(sender=user, payment_methods=payment_methods)
    return payment_methods


@get_actual_user
@subscriptions.decorators.customer_id_required
def create_subscription(user, price_id: str,
                        set_as_default_payment_method: bool = False, **kwargs) -> stripe.Subscription:
    subscription = subscriptions.create_subscription(user, price_id,
                                                     set_as_default_payment_method=set_as_default_payment_method, **kwargs)
    signals.subscription_created.send(sender=user, subscription=subscription)
    return subscription


@get_actual_user
def list_subscriptions(user, **kwargs) -> List[stripe.Subscription]:
    return subscriptions.list_subscriptions(user, **kwargs)


@get_actual_user
@subscriptions.decorators.customer_id_required
def cancel_subscription(user, sub_id: str) -> stripe.Subscription:
    return subscriptions.cancel_subscription(user, sub_id)


@get_actual_user
@subscriptions.decorators.customer_id_required
def modify_subscription(user, subscription_id: str, **kwargs) -> stripe.Subscription:
    return subscriptions.modify_subscription(user, subscription_id, **kwargs)
