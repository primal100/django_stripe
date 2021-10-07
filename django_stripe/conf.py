import os
import stripe

from . import __version__, app_name, url
from django.conf import settings as django_settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from .exceptions import ConfigurationException
from typing import Optional, List, Dict, Any


def return_empty_kwargs(**kwargs) -> Dict:
    return {}


class Settings:

    @property
    def STRIPE_SECRET_KEY(self) -> str:
        return getattr(django_settings, 'STRIPE_SECRET_KEY', os.environ.get('STRIPE_SECRET_KEY', stripe.api_key))

    @property
    def STRIPE_PUBLISHABLE_KEY(self) -> str:
        return getattr(django_settings, 'STRIPE_PUBLISHABLE_KEY', os.environ.get('STRIPE_PUBLISHABLE_KEY'))

    @property
    def STRIPE_APP_DATA(self) -> Dict[str, Any]:
        return getattr(django_settings, 'STRIPE_APP_DATA', {
            'name': app_name,
            'url': url,
            'version': __version__
        })

    @property
    def STRIPE_CHECKOUT_SUCCESS_URL(self) -> str:
        return django_settings.STRIPE_CHECKOUT_SUCCESS_URL

    @property
    def STRIPE_CHECKOUT_CANCEL_URL(self) -> str:
        return django_settings.STRIPE_CHECKOUT_CANCEL_URL

    @property
    def STRIPE_PAYMENT_METHOD_TYPES(self) -> List[str]:
        return getattr(django_settings, "STRIPE_PAYMENT_METHOD_TYPES", ["card"])

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
        return getattr(django_settings, 'STRIPE_BILLING_PORTAL_RETURN_URL', None)

    @property
    def STRIPE_FREE_ACCESS_PRICE_ID(self) -> Optional[str]:
        return getattr(django_settings, 'STRIPE_FREE_ACCESS_PRICE_ID', None)

    @property
    def STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID(self) -> str:
        value = getattr(django_settings, 'STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID', None) or os.environ.get('STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID')
        if not value:
            raise ConfigurationException('STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID')
        return value

    @property
    def STRIPE_ALLOW_DEFAULT_PRODUCT_ONLY(self) -> Optional[str]:
        return getattr(django_settings, 'STRIPE_ALLOW_DEFAULT_PRODUCT_ONLY', False)

    @property
    def STRIPE_CREDIT_CARD_HIDE_POSTAL_CODE(self) -> bool:
        return getattr(django_settings, 'STRIPE_CREDIT_CARD_HIDE_POSTAL_CODE', False)

    @property
    def STRIPE_CHECKOUT_TITLE(self) -> bool:
        return getattr(django_settings, 'STRIPE_CHECKOUT_TITLE', os.environ.get('STRIPE_CHECKOUT_TITLE', 'Django Stripe Checkout Demo'))

    @property
    def STRIPE_CHECKOUT_DEV_MODE(self) -> bool:
        # Note that this will be overridden if test does not appear in the Stripe Publishable key
        return getattr(django_settings, 'STRIPE_CHECKOUT_DEV_MODE', os.environ.get('STRIPE_CHECKOUT_DEV_MODE', True))

    @property
    def STRIPE_CHECKOUT_DEFAULT_COUNTRY(self) -> bool:
        return getattr(django_settings, 'STRIPE_CHECKOUT_COLLECT_BILLING_DATA', "US")

    @property
    def COUNTRY_HEADER(self) -> bool:
        return getattr(django_settings, 'STRIPE_GET_COUNTRY_HEADER ', None)

    @property
    def STRIPE_SUBSCRIPTION_CACHE_NAME(self) -> Optional[str]:
        return getattr(django_settings, 'STRIPE_SUBSCRIPTION_CACHE_NAME', 'default')

    @property
    def STRIPE_SUBSCRIPTION_CHECK_CACHE_TIMEOUT_SECONDS(self) -> Optional[str]:
        return getattr(django_settings, 'STRIPE_SUBSCRIPTION_CHECK_CACHE_TIMEOUT_SECONDS', DEFAULT_TIMEOUT)


settings = Settings()
