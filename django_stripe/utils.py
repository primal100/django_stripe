from django.db import models
from django.contrib.auth import get_user_model
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
