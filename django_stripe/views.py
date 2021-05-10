import stripe
import logging
from .forms import SubscriptionForm
from django.contrib import messages
from django.views.generic import FormView, RedirectView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from stripe.error import StripeError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from . import exceptions
from .permissions import StripeCustomerIdRequiredOrReadOnly
from subscriptions.types import Protocol
from .conf import settings
from . import serializers
from . import payments
from typing import Dict, Any, Type


logger = logging.getLogger("django_stripe")


class StripeViewMixin(Protocol):
    throttle_scope = 'payments'
    status_code = status.HTTP_200_OK

    def make_request(self, request, **data):
        raise NotImplementedError

    def run_stripe(self, request, **data):
        try:
            result = self.make_request(request, **data)
        except stripe.error.StripeError as e:
            logger.exception(e, exc_info=e)
            raise exceptions.StripeException(detail=e)
        return Response(result, status=self.status_code)


class StripeViewWithSerializerMixin(StripeViewMixin, Protocol):
    serializer_class: Type = None

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

    def run_with_serializer(self, request, **kwargs):
        serializer = self.get_serializer(data=request.data or request.query_params)
        if serializer.is_valid():
            data = serializer.data
            return self.run_stripe(request, **data, **kwargs)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StripePriceCheckoutView(APIView, StripeViewMixin):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def make_checkout(request, **data):
        return payments.create_subscription_checkout(request.user, **data)

    def make_request(self, request, **data):
        session = self.make_checkout(request, **data)
        return {'sessionId': session['id']}

    def post(self, request, price_id: str):
        return self.run_stripe(request, price_id=price_id)


class StripeSetupCheckoutView(StripePriceCheckoutView):

    @staticmethod
    def make_checkout(request, **data):
        return payments.create_setup_checkout(request.user, **data)

    def post(self, request, **kwargs):
        return self.run_stripe(request, **kwargs)


class StripeBillingPortalView(APIView, StripeViewMixin):
    permission_classes = (IsAuthenticated,)
    throttle_scope = "payments"

    def make_request(self, request, **kwargs):
        session = payments.create_billing_portal(request.user, **kwargs)
        return {'url': session['url']}

    def post(self, request):
        return self.run_stripe(request)


class StripePricesView(APIView, StripeViewWithSerializerMixin):
    serializer_class = serializers.PriceSerializer

    def make_request(self, request, **data):
        return payments.get_subscription_prices(request.user, **data)

    def get(self, request):
        return self.run_with_serializer(request)


class StripeProductsView(APIView, StripeViewWithSerializerMixin):
    serializer_class = serializers.ProductSerializer

    def make_request(self, request, **data):
        return payments.get_subscription_products(request.user, **data)

    def get(self, request):
        return self.run_with_serializer(request)


class StripeSubscriptionView(APIView, StripeViewMixin):
    status_code = status.HTTP_201_CREATED
    permission_classes = (StripeCustomerIdRequiredOrReadOnly,)
    response_keys = ['id', 'cancel_at', 'current_period_end', 'current_period_start', 'days_until_due',
                     'latest_invoice', 'start_date', 'status', 'trial_end', 'trial_start']

    def make_response(self, subscription: stripe.Subscription) -> Dict[str, Any]:
        return {k: subscription[k] for k in self.response_keys}

    def make_request(self, request, **data):
        subscription = payments.create_subscription(request.user, **data)
        return self.make_response(subscription)

    def post(self, request, price_id: str):
        return self.run_stripe(request, price_id=price_id)


class SubscriptionFormView(LoginRequiredMixin, FormView):
    template_name = 'django_stripe/subscription_form.html'
    form_class = SubscriptionForm

    def get(self, request, *args, **kwargs):
        if request.user and request.user.is_authenticated:
            payments.create_customer(request.user)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        setup_intent = payments.create_setup_intent(self.request.user)
        print(setup_intent)
        print(stripe.PaymentMethod.list(customer=self.request.user.stripe_customer_id, type="card"))
        context['js_vars'] = {
            'stripe_client_secret': setup_intent['client_secret'],
            'payment_method_types': setup_intent['payment_method_types'],
            'hide_postal_code': settings.STRIPE_CREDIT_CARD_HIDE_POSTAL_CODE,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY
        }
        context['user'] = self.request.user
        return context

    def form_valid(self, form):
        price_id = form.cleaned_data['price_id']
        user = self.request.user
        print(stripe.PaymentMethod.list(customer=self.request.user.stripe_customer_id, type="card"))
        try:
            sub = payments.create_subscription(user, price_id)
            messages.success(self.request, f"Successfully subscribed to {sub['id']}")
        except stripe.error.StripeError as e:
            logger.exception(e, exc_info=e)
            error = str(e)
            request_id = exceptions.get_request_id_string(error)
            detail = error.replace(request_id, "")
            messages.error(self.request, detail)
        return self.render_to_response(self.get_context_data(form=form))


class GoToSetupCheckoutView(LoginRequiredMixin, TemplateView):
    template_name = 'django_stripe/checkout.html'

    def make_checkout(self):
        return payments.create_setup_checkout(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.make_checkout()
        context.update({'sessionId': session['id'], 'stripe_public_key': settings.STRIPE_PUBLIC_KEY})
        return context


class GoToCheckoutView(GoToSetupCheckoutView):

    def make_checkout(self):
        price_id = self.request.GET['price_id']
        return payments.create_subscription_checkout(self.request.user, price_id=price_id)


class GoToBillingPortalView(LoginRequiredMixin, RedirectView):

    def get_redirect_url(self, *args, **kwargs) -> str:
        session = payments.create_billing_portal(self.request.user, **kwargs)
        return session['url']
