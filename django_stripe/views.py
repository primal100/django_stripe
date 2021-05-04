from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import subscriptions
from . import serializers
from . import payments


class StripeCheckoutView(APIView):
    serializer_class = serializers.CheckoutSessionSerializer
    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = serializer.data
            session = payments.create_checkout(request.user, data['price_id'])
            return Response({'sessionId': session['id']})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StripeBillingPortalView(APIView):
    throttle_scope = 'payments'
    permission_classes = (IsAuthenticated,)

    @subscriptions.decorators.StripeCustomerIdRequired
    def post(self, request):
        session = payments.create_billing_portal(request.user)
        return Response({'url': session['url']})
