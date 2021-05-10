import os

from django.conf import settings as django_settings
from typing import Optional, List, Dict


def return_empty_kwargs(**kwargs) -> Dict:
    return {}


class Settings:

    @property
    def STRIPE_CHECKOUT_SUCCESS_URL(self) -> str:
        return django_settings.STRIPE_CHECKOUT_SUCCESS_URL

    @property
    def STRIPE_CHECKOUT_CANCEL_URL(self) -> str:
        return django_settings.STRIPE_CHECKOUT_CANCEL_URL

    @property
    def STRIPE_PAYMENT_METHOD_TYPES(self) -> List[str]:
        return django_settings.STRIPE_PAYMENT_METHOD_TYPES

    @property
    def STRIPE_KEEP_CUSTOMER_DETAILS_UPDATED(self) -> bool:
        return getattr(django_settings, 'STRIPE_KEEP_CUSTOMER_DETAILS_UPDATED', True)

    @property
    def STRIPE_PUBLIC_KEY(self) -> str:
        return getattr(django_settings, 'STRIPE_PUBLIC_KEY', os.environ.get('STRIPE_PUBLIC_KEY'))

    @property
    def STRIPE_NEW_CUSTOMER_GET_KWARGS(self) -> bool:
        return getattr(django_settings, 'STRIPE_NEW_CUSTOMER_GET_KWARGS', return_empty_kwargs)

    @property
    def STRIPE_BILLING_PORTAL_RETURN_URL(self) -> Optional[str]:
        return getattr(django_settings, '', None)


settings = Settings()