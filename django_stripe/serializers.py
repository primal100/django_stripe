from rest_framework import serializers


class PriceSerializer(serializers.Serializer):
    product = serializers.CharField(max_length=255, required=False)
    currency = serializers.CharField(min_length=3, max_length=3, required=False)


class ProductSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.CharField(max_length=255), required=False)


class SubscriptionSerializer(serializers.Serializer):
    default_payment_method = serializers.CharField(max_length=255, required=False)
    set_as_customer_default_payment_method = serializers.BooleanField(default=False, required=False)
