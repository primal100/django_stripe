from rest_framework import serializers

from .settings import django_stripe_settings as settings
from typing import Type


class CheckoutSessionSerializer(serializers.Serializer):
    swappable = "CHECKOUT"
    price_id = serializers.CharField(max_length=255, required=True)


class PriceSerializer(serializers.Serializer):
    swappable = "PRICE"
    product_ids = serializers.ListField(child=serializers.CharField(max_length=255), required=False)
    currency = serializers.CharField(min_length=3, max_length=3, required=False)


class ProductSerializer(serializers.Serializer):
    swappable = "PRODUCT"
    product_id = serializers.CharField(max_length=255, required=False)


def get_serializer_class(serializer: Type[serializers.Serializer]) -> Type[serializers.Serializer]:
    name = getattr(serializer, 'swappable', '')
    if name:
        return settings.STRIPE_SERIALIZERS.get(name, serializer)
    return serializer
