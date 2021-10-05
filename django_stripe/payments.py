import stripe
import stripe.error
import subscriptions

# Next line is so functions can be used by django_stripe user without needing to import from subscriptions
from subscriptions import cancel_subscription, cancel_subscription_for_product, delete_customer

from subscriptions.types import PaymentMethodType
from functools import wraps
from django.core.cache import caches, cache
from django.core import exceptions
from django import http
from django.utils import timezone
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, NotFound

from .conf import settings
from .logging import logger, p
from . import signals

from .utils import get_actual_user, user_description
from typing import List, Dict, Any, Callable, Generator, Optional, Type
from .types import DjangoUserProtocol, SubscriptionInfoWithEvaluation


FREE = "FREE"


def add_stripe_customer_if_not_existing(f):
    @wraps(f)
    def wrapper(user: DjangoUserProtocol, *args, **kwargs):
        user = create_customer(user)
        return f(user, *args, **kwargs)

    return wrapper


def raise_appropriate_permission_denied(rest: bool, msg: str):
    if rest:
        raise PermissionDenied(msg)
    else:
        raise exceptions.PermissionDenied(msg)


def raise_appropriate_not_found(rest: bool, msg: str):
    if rest:
        raise NotFound(msg)
    else:
        raise http.Http404(msg)


@get_actual_user
def create_customer(user: DjangoUserProtocol, **kwargs):
    kwargs = kwargs or {}
    if not user or not user.is_authenticated:
        raise NotAuthenticated('This stripe method requires a logged in user')
    if not user.stripe_customer_id:
        logger.debug('Creating user %s on stripe', user.id)
        customer_kwargs = settings.STRIPE_NEW_CUSTOMER_GET_KWARGS(**kwargs)
        customer = subscriptions.create_customer(user, description=user_description(user), **customer_kwargs)
        user.save(update_fields=('stripe_customer_id',))
        signals.new_customer.send(sender=user, customer=customer)
        logger.debug('Stripe: Created user %s on stripe. Customer id is %s', user.id, user.stripe_customer_id)
    return user


@get_actual_user
@subscriptions.decorators.customer_id_required
def modify_customer(user: DjangoUserProtocol, **kwargs) -> stripe.Customer:
    logger.debug('Modifying user %s on stripe with keys: %s', user.id, list(kwargs.keys()))
    customer = stripe.Customer.modify(user.stripe_customer_id, **kwargs)
    signals.customer_modified.send(sender=user, customer=customer)
    return customer


@get_actual_user
@subscriptions.decorators.customer_id_required
def modify_payment_method(user: DjangoUserProtocol, obj_id: str, set_as_default: bool = False,
                          **kwargs) -> stripe.PaymentMethod:
    if set_as_default:
        logger.debug('Setting default method for user %s to %s with keys: %s', user.id, obj_id, list(kwargs.keys()))
        modify_customer(user, invoice_settings={
            'default_payment_method': obj_id})
        if not kwargs:
            return retrieve(user, stripe.PaymentMethod, obj_id)
    logger.debug('Modifying payment method %s for user %s', user.id, obj_id)
    return modify(user, stripe.PaymentMethod, obj_id, **kwargs)


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
    logger.debug('Created new checkout session %s for user %s', session['id'], user.id)
    return session


def create_subscription_checkout(user: subscriptions.types.UserProtocol, price_id: str, rest: bool = False,
                                 **kwargs) -> stripe.checkout.Session:
    try:
        retrieve_price(user, price_id, rest=rest)            # To check that price is allowed depending on settings
    except stripe.error.InvalidRequestError:
        raise raise_appropriate_not_found(rest, f"No such price: '{price_id}'")
    logger.debug('Creating new subscription checkout session for user %s', user.id)
    return create_checkout(user, subscriptions.create_subscription_checkout, price_id=price_id, **kwargs)


def create_setup_checkout(user: subscriptions.types.UserProtocol, rest: bool = False, **kwargs) -> stripe.checkout.Session:
    """
    Rest argument needed for consistency with create_subscription_checkout
    """
    logger.debug('Creating new setup checkout session for user %s', user.id)
    return create_checkout(user, method=subscriptions.create_setup_checkout, **kwargs)


@add_stripe_customer_if_not_existing
def create_billing_portal(user) -> stripe.billing_portal.Session:
    logger.debug('Creating new billing portal session for user %s', user.id)
    return_url = settings.STRIPE_BILLING_PORTAL_RETURN_URL
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url
    )
    signals.billing_portal_created.send(sender=user, session=session)
    return session


@get_actual_user
def get_products(user, ids: List[str] = None, price_kwargs: Dict[str, Any] = None, rest: bool = False,
                 **kwargs) -> List[Dict[str, Any]]:
    if settings.STRIPE_ALLOW_DEFAULT_PRODUCT_ONLY:
        for product in ids or []:
            if not product == settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID:
                raise_appropriate_permission_denied(rest, f"Cannot access product {product}")
        ids = [settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID]
    return subscriptions.get_subscription_products_and_prices(user, ids=ids, price_kwargs=price_kwargs, **kwargs)


@get_actual_user
def get_prices(user, product: str = None, currency: str = None, rest: bool = False, **kwargs) -> List[Dict[str, Any]]:
    if settings.STRIPE_ALLOW_DEFAULT_PRODUCT_ONLY:
        if product and not product == settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID:
            raise_appropriate_permission_denied(rest, f"Cannot access product {product}")
        product = settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID
    result = subscriptions.get_subscription_prices(user, product=product, currency=currency, **kwargs)
    return result


@get_actual_user
def retrieve_product(user, obj_id: str, price_kwargs: Optional[Dict[str, Any]] = None,
                     rest: bool = False) -> Dict[str, Any]:
    if settings.STRIPE_ALLOW_DEFAULT_PRODUCT_ONLY and not obj_id == settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID:
        raise_appropriate_permission_denied(rest, f"Cannot access product {obj_id}")
    return subscriptions.retrieve_product(user, obj_id, price_kwargs=price_kwargs)


@get_actual_user
def retrieve_price(user, obj_id: str, rest: bool = False) -> Dict[str, Any]:
    price = subscriptions.retrieve_price(user, obj_id)
    if settings.STRIPE_ALLOW_DEFAULT_PRODUCT_ONLY and not price['product'] == settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID:
        raise_appropriate_permission_denied(rest, f"Cannot access price {obj_id}")
    return price


@get_actual_user
@add_stripe_customer_if_not_existing
def create_setup_intent(user, **kwargs) -> stripe.SetupIntent:
    logger.debug('Creating new setup intent for user %s', user.id)
    setup_intent_kwargs = {
        'customer': user.stripe_customer_id,
        'payment_method_types': settings.STRIPE_PAYMENT_METHOD_TYPES,
        'confirm': False,
        'usage': "off_session"}
    setup_intent_kwargs.update(kwargs)
    setup_intent = stripe.SetupIntent.create(**setup_intent_kwargs)
    signals.setup_intent_created.send(sender=user, setup_intent=setup_intent)
    logger.debug('Created new setup intent for user %s: %s', user.id, setup_intent['id'])
    return setup_intent


@get_actual_user
def list_payment_methods(user, types: List[PaymentMethodType] = None, **kwargs) -> Generator[
    stripe.PaymentMethod, None, None]:
    types = types or settings.STRIPE_PAYMENT_METHOD_TYPES
    return subscriptions.list_payment_methods(user, types, **kwargs)


@get_actual_user
@subscriptions.decorators.customer_id_required
def detach_payment_method(user, pm_id: str) -> stripe.PaymentMethod:
    logger.debug('Detaching payment method %s for user %s', pm_id, user.id)
    payment_method = subscriptions.detach_payment_method(user, pm_id)
    signals.payment_method_detached.send(sender=user, payment_methods=[payment_method])
    logger.debug('Detached payment method %s for user %s', pm_id, user.id)
    return payment_method


@get_actual_user
def detach_all_payment_methods(user, types: List[PaymentMethodType] = None, **kwargs) -> List[stripe.PaymentMethod]:
    types = types or settings.STRIPE_PAYMENT_METHOD_TYPES
    logger.debug('Detaching all payment method for user %s with types: %s', user.id, types)
    payment_methods = subscriptions.detach_all_payment_methods(user, types, **kwargs)
    if payment_methods:
        signals.payment_method_detached.send(sender=user, payment_methods=payment_methods)
        logger.debug('Detached %s for user %s', p.no('payment method', len(payment_methods)), user.id)
    else:
        logger.info('No payment methods for user %s found with types %s')
    return payment_methods


@get_actual_user
@subscriptions.decorators.customer_id_required
def create_subscription(user, price_id: str,
                        set_as_default_payment_method: bool = False, **kwargs) -> stripe.Subscription:
    logger.debug('Creating subscription for user %s price_id: %s', user.id, price_id)
    subscription = subscriptions.create_subscription(user, price_id,
                                                     set_as_default_payment_method=set_as_default_payment_method,
                                                     **kwargs)
    signals.subscription_created.send(sender=user, subscription=subscription)
    logger.debug('Created subscription %s for user %s', subscription['id'], user.id)
    return subscription


@get_actual_user
@subscriptions.decorators.customer_id_required
def modify_subscription(user, sub_id: str, set_as_default_payment_method: bool = False,
                        **kwargs) -> stripe.Subscription:
    logger.debug('Modifying subscription %s for user %s price_id: %s for keys: %s', sub_id, user.id,
                 list(kwargs.keys()))
    subscription = subscriptions.modify_subscription(user, sub_id,
                                                     set_as_default_payment_method=set_as_default_payment_method,
                                                     **kwargs)
    signals.subscription_modified.send(sender=user, subscription=subscription)
    logger.debug('Subscription %s modified by user %s', sub_id, user.id)
    return subscription


@get_actual_user
def list_customer_resource(user, obj_cls: Type, **kwargs) -> List[Dict[str, Any]]:
    if not user or not user.stripe_customer_id:
        return []
    return obj_cls.list(customer=user.stripe_customer_id, **kwargs)['data']


@get_actual_user
def retrieve(user: DjangoUserProtocol, obj_cls: Type, obj_id: str):
    return subscriptions.retrieve(user, obj_cls, obj_id)


@get_actual_user
@subscriptions.decorators.customer_id_required
def delete(user, obj_cls: Any, obj_id: str) -> Dict[str, Any]:
    logger.debug('Deleting %s for user %s', obj_id, user.id)
    obj = subscriptions.delete(user, obj_cls, obj_id)
    signals.send_signal_on_delete(user, obj_cls, obj)
    logger.debug('Deleted %s for user %s', obj_id, user.id)
    return obj


@get_actual_user
@subscriptions.decorators.customer_id_required
def modify(user: DjangoUserProtocol, obj_cls: Type, obj_id: str, **kwargs: Dict[str, Any]):
    logger.debug('Modifying %s for user %s with keys: %s', obj_id, user.id, list(kwargs.keys()))
    obj = subscriptions.modify(user, obj_cls, obj_id, **kwargs)
    signals.send_signal_on_modify(user, obj_cls, obj)
    return obj


@get_actual_user
def is_subscribed_and_cancelled_time(user, product_id: str = None) -> SubscriptionInfoWithEvaluation:
    product_id = product_id or settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID
    if hasattr(user, 'allowed_access_until') and (
            user.allowed_access_until and user.allowed_access_until >= timezone.now()):
        return {'sub_id': FREE, 'cancel_at': None, 'current_period_end': int(user.allowed_access_until.timestamp()),
                'evaluation': True, 'product_id': product_id, 'price_id': settings.STRIPE_FREE_ACCESS_PRICE_ID}
    sub_info: SubscriptionInfoWithEvaluation = subscriptions.is_subscribed_and_cancelled_time(user, product_id)
    sub_info['evaluation'] = False
    return sub_info


def is_subscribed(user, product_id: str = None) -> bool:
    product_id = product_id or settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID
    return bool(is_subscribed_and_cancelled_time(user, product_id)['sub_id'])


def get_subscription_cache() -> cache:
    return caches[settings.STRIPE_SUBSCRIPTION_CACHE_NAME]


def is_subscribed_with_cache(user, product_id: str = None) -> bool:
    product_id = product_id or settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID
    cache = get_subscription_cache()
    cache_key = f'is_subscribed_{user.id}_{product_id}'
    subscribed = cache.get(cache_key)
    if subscribed is None:
        logger.debug('Retrieving subscription data with cache key %s for user %s for product %s', cache_key, user.id,
                     product_id)
        subscribed = is_subscribed(user, product_id)
        if subscribed:
            logger.debug('Setting cache key %s for user %s subscription: %s', cache_key, user.id, subscribed, )
            cache.set(cache_key, subscribed, timeout=settings.STRIPE_SUBSCRIPTION_CHECK_CACHE_TIMEOUT_SECONDS)
    return subscribed
