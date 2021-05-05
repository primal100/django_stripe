from rest_framework import serializers

from .settings import django_stripe_settings as settings
from typing import Type


class CheckoutSessionSerializer(serializers.Serializer):
    price_id = serializers.CharField(max_length=255, required=True)


class PriceSerializer(serializers.Serializer):
    product_ids = serializers.ListField(child=serializers.CharField(max_length=255), required=False)
    currency = serializers.CharField(min_length=3, max_length=3, required=False)


class ProductSerializer(serializers.Serializer):
    product_id = serializers.CharField(max_length=255, required=False)

