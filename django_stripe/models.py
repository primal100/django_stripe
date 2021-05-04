from django.db import models
from django.contrib.auth.models import AbstractUser


class StripeCustomerUser(AbstractUser):
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

    class Meta:
        abstract = True
