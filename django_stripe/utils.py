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
