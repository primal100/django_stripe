from django.conf import settings
from rest_framework.serializers import Serializer, ListSerializer
from django.utils.module_loading import import_string
from typing import Optional, List, Dict, Union


def return_empty_kwargs(**kwargs) -> Dict:
    return {}


class Settings:

    def __init__(self):
        self._loaded_strings = {}

    @property
    def STRIPE_CHECKOUT_SUCCESS_URL(self) -> str:
        return settings.STRIPE_CHECKOUT_SUCCESS_URL

    @property
    def STRIPE_CHECKOUT_CANCEL_URL(self) -> str:
        return settings.STRIPE_CHECKOUT_CANCEL_URL

    @property
    def STRIPE_PAYMENT_METHOD_TYPES(self) -> List[str]:
        return settings.STRIPE_KEEP_CUSTOMER_EMAIL_UPDATED

    @property
    def STRIPE_KEEP_CUSTOMER_EMAIL_UPDATED(self) -> bool:
        return getattr(settings, 'STRIPE_KEEP_CUSTOMER_EMAIL_UPDATED', True)

    @property
    def STRIPE_CHECKOUT_GET_KWARGS(self) -> bool:
        return getattr(settings, 'STRIPE_CHECKOUT_GET_KWARGS', return_empty_kwargs)

    @property
    def STRIPE_BILLING_PORTAL_RETURN_URL(self) -> Optional[str]:
        return getattr(settings, '', None)

    @property
    def STRIPE_SERIALIZERS(self) -> Dict[str, Union[Serializer, ListSerializer]]:
        serializers = getattr(settings, '', {})
        for name, serializer in serializers.items():
            if isinstance(serializer, str):
                if serializer not in self._loaded_strings:
                    self._loaded_strings[serializer] = import_string(serializer)
                serializers[name] = self._loaded_strings[name]
        return serializers


django_stripe_settings = Settings()
