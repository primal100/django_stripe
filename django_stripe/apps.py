from django.apps import AppConfig
from django.conf import settings
import stripe
import os
from . import __version__, app_name, url


class DjangoStripeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_stripe'

    def ready(self):
        stripe.api_key = getattr(settings, 'STRIPE_API_KEY', os.environ.get('STRIPE_API_KEY', stripe.api_key))
        stripe_app_data = getattr(settings, "STRIPE_APP_DATA", {
            'name': app_name,
            'url': url,
            'version': __version__
        })
        stripe.set_app_info(**stripe_app_data)
        from . import signal_receivers
