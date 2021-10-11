import os
import stripe

from . import __version__, app_name, url
from django.conf import settings as django_settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from .exceptions import ConfigurationException
from typing import Optional, List, Dict, Any


def return_empty_kwargs(user, **kwargs) -> Dict:
    return {}


class Settings:

    @property
    def STRIPE_SECRET_KEY(self) -> str:
        """
        The Stripe Secret Key as shown in the Stripe Dashboard. Environment variable recommended for production.
        """
        return getattr(django_settings, 'STRIPE_SECRET_KEY', os.environ.get('STRIPE_SECRET_KEY', stripe.api_key))

    @property
    def STRIPE_PUBLISHABLE_KEY(self) -> str:
        """
        The Stripe Publishable Key as shown in the Stripe Dashboard. Can also be set wih an environment variable.
        """
        return getattr(django_settings, 'STRIPE_PUBLISHABLE_KEY', os.environ.get('STRIPE_PUBLISHABLE_KEY'))

    @property
    def STRIPE_APP_DATA(self) -> Dict[str, Any]:
        """
          Optional data to send with Stripe API requests
        """
        return getattr(django_settings, 'STRIPE_APP_DATA', {
            'name': app_name,
            'url': url,
            'version': __version__
        })

    @property
    def STRIPE_CHECKOUT_SUCCESS_URL(self) -> str:
        """
        URL to redirect to after Stripe Checkout is completed
        """
        return django_settings.STRIPE_CHECKOUT_SUCCESS_URL

    @property
    def STRIPE_CHECKOUT_CANCEL_URL(self) -> str:
        """
        URL to redirect to if a Stripe Checkout is cancelled
        """
        return django_settings.STRIPE_CHECKOUT_CANCEL_URL

    @property
    def STRIPE_PAYMENT_METHOD_TYPES(self) -> List[str]:
        """
        List of payment methods supported by checkout sessions and Setup Intents.
        Available types are listed here:
        https://stripe.com/docs/api/payment_methods/object
        """
        return getattr(django_settings, "STRIPE_PAYMENT_METHOD_TYPES", ["card"])

    @property
    def STRIPE_KEEP_CUSTOMER_DETAILS_UPDATED(self) -> bool:
        """
        When a user's name or email is changed, whether the value is also updated for the customer over the Stripe API
        """
        return getattr(django_settings, 'STRIPE_KEEP_CUSTOMER_DETAILS_UPDATED', True)

    @property
    def STRIPE_NEW_CUSTOMER_GET_KWARGS(self) -> bool:
        """
        A function which provides additional parameters to the Stripe API when creating a customer.
        Function signature is

        def additional_customer_parameters(user: User, **kwargs) -> Dict[str, Any]:

        """
        return getattr(django_settings, 'STRIPE_NEW_CUSTOMER_GET_KWARGS', return_empty_kwargs)

    @property
    def STRIPE_BILLING_PORTAL_RETURN_URL(self) -> Optional[str]:
        """
        The URL to return users to after they complete a Stripe Billing Portal Session
        """
        return getattr(django_settings, 'STRIPE_BILLING_PORTAL_RETURN_URL', None)

    @property
    def STRIPE_FREE_ACCESS_PRICE_ID(self) -> Optional[str]:
        """
        If a user has been given free access, this is the price_id they are being given free access to which will be returned in the responses.
        """
        return getattr(django_settings, 'STRIPE_FREE_ACCESS_PRICE_ID', None)

    @property
    def STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID(self) -> str:
        """
        The default product_id for subscriptions. Used to select prices for the django-stripe checkout.
        Can also be set wih an environment variable.
        """
        value = getattr(django_settings, 'STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID', None) or os.environ.get('STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID')
        if not value:
            raise ConfigurationException('STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID')
        return value

    @property
    def STRIPE_ALLOW_DEFAULT_PRODUCT_ONLY(self) -> Optional[str]:
        """
        If set to True, users will be restricting from accessing any product_id other than the default one.
        """
        return getattr(django_settings, 'STRIPE_ALLOW_DEFAULT_PRODUCT_ONLY', False)

    @property
    def STRIPE_CREDIT_CARD_HIDE_POSTAL_CODE(self) -> bool:
        """
        Whether to show the Postal Code field in Stripe Elements in the django_stripe checkout.
        """
        return getattr(django_settings, 'STRIPE_CREDIT_CARD_HIDE_POSTAL_CODE', False)

    @property
    def STRIPE_CHECKOUT_TITLE(self) -> bool:
        """
        Title of the django_stripe checkout page.
        """
        return getattr(django_settings, 'STRIPE_CHECKOUT_TITLE', os.environ.get('STRIPE_CHECKOUT_TITLE', 'Django Stripe Checkout Demo'))

    @property
    def STRIPE_CHECKOUT_DEV_MODE(self) -> bool:
        """
        Show additional information such as test credit card numbers in the django_stripe checkout page.
        This will be overridden as False if test does not appear in the Stripe Publishable key so it is safe to always leave this as True.
        """
        return getattr(django_settings, 'STRIPE_CHECKOUT_DEV_MODE', os.environ.get('STRIPE_CHECKOUT_DEV_MODE', True))

    @property
    def STRIPE_CHECKOUT_DEFAULT_COUNTRY(self) -> bool:
        """
        The default country to set the Billing Details form to in the django_stripe checkout page
        """
        return getattr(django_settings, 'STRIPE_CHECKOUT_DEFAULT_COUNTRY', "US")

    @property
    def COUNTRY_HEADER(self) -> bool:
        """
        If a two-letter country code exists as a header in the request, set the header name here and the value of the header will be used as the default country in the django-stripe checkout page.
        For example, if requests pass through Cloudflare, set this value to HTTP_CF_IPCOUNTRY.
        If this header is available, it takes priority, otherwise STRIPE_CHECKOUT_DEFAULT_COUNTRY is used.
        """
        return getattr(django_settings, 'STRIPE_GET_COUNTRY_HEADER ', None)

    @property
    def STRIPE_SUBSCRIPTION_CACHE_NAME(self) -> Optional[str]:
        """
        Caching can be used when checking if a user is subscribed. This is the cache name to use for storing subscriptions.
        """
        return getattr(django_settings, 'STRIPE_SUBSCRIPTION_CACHE_NAME', 'default')

    @property
    def STRIPE_SUBSCRIPTION_CHECK_CACHE_TIMEOUT_SECONDS(self) -> Optional[str]:
        """
        How long to store keys in the Stripe Subscription Cache.
        """
        return getattr(django_settings, 'STRIPE_SUBSCRIPTION_CHECK_CACHE_TIMEOUT_SECONDS', DEFAULT_TIMEOUT)


settings = Settings()
