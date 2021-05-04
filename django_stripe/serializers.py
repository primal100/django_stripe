from rest_framework import serializers


class CheckoutSessionSerializer(serializers.Serializer):
    price_id = serializers.CharField(max_length=255)