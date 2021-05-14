from rest_framework import serializers


class PriceSerializer(serializers.Serializer):
    product = serializers.CharField(max_length=255, required=False)
    currency = serializers.CharField(min_length=3, max_length=3, required=False)


class ProductSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.CharField(max_length=255), required=False)


class PaymentMethodModifySerializer(serializers.Serializer):
    set_as_default = serializers.BooleanField(default=False, required=False)


class SubscriptionModifySerializer(serializers.Serializer):
    default_payment_method = serializers.CharField(max_length=255, required=False)
    set_as_default_payment_method = serializers.BooleanField(default=False, required=False)


class SubscriptionCreateSerializer(SubscriptionModifySerializer):
    price_id: str = serializers.CharField(max_length=255, required=True)


class SubscriptionListSerializer(serializers.Serializer):
    price_id: str = serializers.CharField(max_length=255, required=False)
    active = serializers.BooleanField(required=False)


class InvoiceSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'paid'),
        ('uncollectible', 'uncollectible'),
        ('void', 'void'),
    ), required=False)
    subscription = serializers.CharField(max_length=255, required=False)
