from django.db import models
from django.contrib.auth import get_user_model
from functools import wraps
from typing import Any


User = get_user_model()


def get_user_if_token_user(user: Any):
    """
    Support for django-rest-framework-simplejwt TokenUser.
    Makes sure to always use the actual user model with save capability.
    Returns None for anonymous users
    """
    if user:
        if not user.is_authenticated:
            return None
        elif not isinstance(user, models.Model):
            return User.objects.get(id=user.id)
    return user


def get_actual_user(f):
    """
    Decorator to support djangorestframework-simplejwt TokenUser. The stripe_customer_id is not available in that case so it is required to retrieve the User from the database.
    This decorator makes sure the database user model is provided to the child function.
    """
    @wraps(f)
    def wrapper(user, *args, **kwargs):
        user = get_user_if_token_user(user)
        return f(user, *args, **kwargs)
    return wrapper


def user_description(user) -> str:
    """
    The description sent to Stripe when a customer is created or modified
    """
    return f'{user.first_name} {user.last_name}'


def normalize_payment_method_kwargs(kwargs):
    """Translate the legacy spelling to the supported Stripe parameter."""
    kwargs = dict(kwargs)
    if 'payment_method_types' in kwargs:
        if 'allowed_payment_method_types' in kwargs:
            raise TypeError('Pass either payment_method_types or allowed_payment_method_types, not both.')
        kwargs['allowed_payment_method_types'] = kwargs.pop('payment_method_types')
    return kwargs


def resource_dict(value):
    """Normalize SDK objects before dictionary operations or JSON rendering."""
    import stripe
    if isinstance(value, stripe.StripeObject):
        return value.to_dict(for_json=True)
    if isinstance(value, dict):
        return {key: resource_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [resource_dict(item) for item in value]
    return value


def subscription_details(resource):
    """Keep legacy fields for single-item subscriptions without conflating item periods."""
    sub = resource_dict(resource).copy()
    items = (sub.get('items') or {}).get('data', [])
    if len(items) == 1:
        item = items[0]
        price = item.get('price') or item.get('plan') or {}
        sub['plan'] = dict(item.get('plan') or price)
        product = sub['plan'].get('product')
        if isinstance(product, dict):
            sub['plan']['product'] = product['id']
        for field in ('current_period_start', 'current_period_end'):
            sub[field] = item.get(field)
    elif len(items) > 1 or not sub.get('plan'):
        sub['plan'] = {'id': None, 'product': None}
        sub['current_period_start'] = sub['current_period_end'] = None
    return sub
