from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from functools import wraps
import subscriptions
from typing import Any


User = get_user_model()


def get_user_if_token_user(user: Any):
    """
    Support for django-rest-framework-simplejwt TokenUser.
    Makes sure to always use the actual user model with save capability.
    """
    if user.is_authenticated and not isinstance(user, models.Model):
        return User.objects.get(id=user.id)
    return user


def add_stripe_customer_if_not_existing(f):
    @wraps(f)
    def wrapper(user, *args, **kwargs):
        user = get_user_if_token_user(user)
        if not user.stripe_customer_id:
            customer_kwargs = getattr(settings, 'STRIPE_CUSTOMER_GET_KWARGS', lambda x: {})(user)
            subscriptions.create_customer(user, **customer_kwargs)
            user.save(update_fields=('stripe_customer_id',))
        return f(user, *args, **kwargs)
    return wrapper


