from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from .conf import settings
import stripe
from .logging import logger
from .payments import modify_customer
from .utils import user_description


from typing import Optional, Tuple


User = get_user_model()


@receiver(post_save, sender=User)
def modify_email_if_changed_receiver(instance, created: bool,
                                     update_fields: Optional[Tuple] = None, **kwargs):
    if settings.STRIPE_KEEP_CUSTOMER_DETAILS_UPDATED and not created and instance.stripe_customer_id and (
            not update_fields or any(f in update_fields for f in ('email', 'first_name', 'last_name'))):
        logger.debug("Updating user %d email in Stripe", instance.id)
        customer = stripe.Customer.retrieve(instance.stripe_customer_id)
        modify_kwargs = {}
        if customer['email'] != instance.email:
            modify_kwargs['email'] = instance.email
        description = user_description(instance)
        if customer['description'] != description:
            modify_kwargs['description'] = description
        if modify_kwargs:
            modify_customer(instance, **modify_kwargs)

