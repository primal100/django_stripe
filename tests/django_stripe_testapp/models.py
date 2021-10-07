from django.db import models
from django_stripe.models import StripeCustomerUser


class User(StripeCustomerUser):
    allowed_access_until = models.DateTimeField(blank=True, null=True)
