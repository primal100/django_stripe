from django.apps import AppConfig
from django.conf import settings
import stripe


class DjangoStripeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_stripe'

    def ready(self):
        stripe.api_key = getattr(settings, 'STRIPE_API_KEY', None)
        app_name = getattr(settings, "APPNAME", "django-stripe")
        app_url = getattr(settings, "APPURL", "https://github.com/primal100/django_stripe")
        app_version = getattr(settings, 'VERSION', '0.1')
        stripe.set_app_info(app_name, version=app_version, url=app_url)
