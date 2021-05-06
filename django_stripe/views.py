import stripe
from stripe.error import StripeError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .permissions import StripeCustomerIdRequiredOrReadOnly
from subscriptions.types import Protocol
from . import serializers
from . import payments
from typing import Dict, Any, Type


class StripeViewMixin(Protocol):
    serializer_class: Type = None
    throttle_scope = 'payments'
    status_code = status.HTTP_200_OK

    def get_serializer_class(self) -> Type:
        return self.serializer_class

    def get_serializer_context(self) -> Dict[str, Any]:
        return {
            'request': self.request,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args,  **kwargs)

    def make_request(self, request, **data):
        raise NotImplementedError

    def run(self, request):
        serializer = self.get_serializer(data=request.data or request.query_params)
        if serializer.is_valid():
            data = serializer.data
            try:
                result = self.make_request(request, **data)
            except StripeError as e:
                raise
            return Response(result, status=self.status_code)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StripeCheckoutView(APIView, StripeViewMixin):
    serializer_class = serializers.CheckoutSessionSerializer
    permission_classes = (IsAuthenticated,)

    def make_request(self, request, **data):
        session = payments.create_checkout(request.user, data['price_id'])
        return {'sessionId': session['id']}

    def post(self, request):
        return self.run(request)


class StripeBillingPortalView(APIView):
    permission_classes = (IsAuthenticated,)
    throttle_scope = "payments"

    def make_request(self, request):
        session = payments.create_billing_portal(request.user)
        return {'url': session['url']}

    def post(self, request):
        result = self.make_request(request)
        return Response(result)


class StripePricesView(APIView, StripeViewMixin):
    serializer_class = serializers.PriceSerializer

    def make_request(self, request, **data):
        return payments.get_subscription_prices(request.user, **data)

    def get(self, request):
        return self.run(request)


class StripeProductsView(APIView, StripeViewMixin):
    serializer_class = serializers.ProductSerializer

    def make_request(self, request, **data):
        return payments.get_subscription_products(request.user, **data)

    def get(self, request):
        return self.run(request)


class StripeSubscriptionView(APIView, StripeViewMixin):
    status_code = status.HTTP_201_CREATED
    serializer_class = serializers.SubscriptionSerializer
    permission_classes = (StripeCustomerIdRequiredOrReadOnly,)
    response_keys = ['id', 'cancel_at', 'current_period_end', 'current_period_start', 'days_until_due',
                     'latest_invoice', 'start_date', 'status', 'trial_end', 'trial_start']

    def make_response(self, subscription: stripe.Subscription) -> Dict[str, Any]:
        return {k: subscription[k] for k in self.response_keys}

    def make_request(self, request, **data):
        subscription = payments.create_subscription(request.user, **data)
        return self.make_response(subscription)

    def post(self, request):
        return self.run(request)