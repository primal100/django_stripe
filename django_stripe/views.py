from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import subscriptions
from . import serializers
from . import payments
from .utils import get_user_if_token_user
from typing import Dict, Any, Type


class SwappableSerializerMixin:
    serializer_class = None

    def get_serializer_class(self) -> Type:
        return serializers.get_serializer_class(self.serializer_class)

    def get_serializer_context(self) -> Dict[str, Any]:
        return {
            'request': self.request,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args,  **kwargs)


class StripeCheckoutView(APIView, SwappableSerializerMixin):
    serializer_class = serializers.CheckoutSessionSerializer
    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            session = payments.create_checkout(request.user, data['price_id'])
            return Response({'sessionId': session['id']})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StripeBillingPortalView(APIView):
    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        session = payments.create_billing_portal(request.user)
        return Response({'url': session['url']})


class StripePricesView(APIView, SwappableSerializerMixin):
    serializer_class = serializers.PriceSerializer
    throttle_scope = 'payments'

    def get(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            user = get_user_if_token_user(request.user)
            result = subscriptions.get_subscription_prices(user, **data)
            return Response(result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StripeProductsView(APIView, SwappableSerializerMixin):
    serializer_class = serializers.ProductSerializer
    throttle_scope = 'payments'

    def get(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            user = get_user_if_token_user(request.user)
            result = subscriptions.get_subscription_products_and_prices(user, **data)
            return Response(result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
