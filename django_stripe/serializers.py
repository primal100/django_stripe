from rest_framework import serializers


class CheckoutSessionSerializer(serializers.Serializer):
    price_id = serializers.CharField(max_length=255, required=True)


class PriceSerializer(serializers.Serializer):
    product = serializers.CharField(max_length=255, required=False)
    currency = serializers.CharField(min_length=3, max_length=3, required=False)


class ProductSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.CharField(max_length=255), required=False)


class SubscriptionSerializer(serializers.Serializer):
    price_id = serializers.CharField(max_length=255, required=True)
