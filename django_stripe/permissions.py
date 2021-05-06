from rest_framework.permissions import BasePermission, SAFE_METHODS
from .utils import get_user_if_token_user


class StripeCustomerIdRequiredOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            (request.user and
             request.user.is_authenticated and
             get_user_if_token_user(request.user).stripe_customer_id
            )
        )
