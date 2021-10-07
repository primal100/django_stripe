from rest_framework import serializers


class PriceSerializer(serializers.Serializer):
    product = serializers.CharField(max_length=255, required=False)
    currency = serializers.CharField(min_length=3, max_length=3, required=False)


class ProductSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.CharField(max_length=255), required=False)


class PaymentMethodModifySerializer(serializers.Serializer):
    set_as_default = serializers.BooleanField(default=False, required=False)
    billing_details = serializers.JSONField(required=False)


class SubscriptionModifySerializer(serializers.Serializer):
    default_payment_method = serializers.CharField(max_length=255, required=False)
    set_as_default_payment_method = serializers.BooleanField(default=False, required=False)

    def validate(self, data):
        if data['set_as_default_payment_method'] and not data.get('default_payment_method'):
            raise serializers.ValidationError(
                "The default_payment_method field must be set if set_as_default_payment_method is True.")
        return data


class SubscriptionCreateSerializer(SubscriptionModifySerializer):
    price_id: str = serializers.CharField(max_length=255, required=True)


class SubscriptionListSerializer(serializers.Serializer):
    price_id: str = serializers.CharField(max_length=255, required=False)
    status = serializers.ChoiceField(required=False, choices=(
        ('incomplete', 'incomplete'),
        ('incomplete_expired', 'incomplete_expired'),
         ('trialing', 'trialing'),
         ('active', 'active'),
         ('past_due', 'past_due'),
         ('canceled', 'canceled'),
         ('unpaid', 'unpaid')
    ))


class InvoiceSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'paid'),
        ('uncollectible', 'uncollectible'),
        ('void', 'void'),
    ), required=False)
    subscription = serializers.CharField(max_length=255, required=False)
