from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from .settings import django_stripe_settings as settings
import stripe
from .payments import modify_customer


from typing import Optional, Tuple


User = get_user_model()


@receiver(post_save, sender=User)
def modify_email_if_changed_receiver(instance, created: bool,
                                     update_fields: Optional[Tuple] = None, **kwargs):
    if settings.STRIPE_KEEP_CUSTOMER_EMAIL_UPDATED and not created and instance.stripe_customer_id and (
            not update_fields or 'email' in update_fields):
        customer = stripe.Customer.retrieve(instance.stripe_customer_id)
        if customer['email'] != instance.email:
            modify_customer(instance, email=instance.email)
