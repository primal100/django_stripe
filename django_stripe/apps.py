from django.apps import AppConfig
import stripe

from .conf import settings


class DjangoStripeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_stripe'

    def ready(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe_app_data = settings.STRIPE_APP_DATA
        stripe.set_app_info(**stripe_app_data)
        from . import signal_receivers
