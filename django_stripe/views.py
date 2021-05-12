import stripe
import logging
from .forms import SubscriptionForm
from django.contrib import messages
from django.views.generic import FormView, RedirectView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from operator import itemgetter
from stripe.error import StripeError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from . import exceptions
from .permissions import StripeCustomerIdRequiredOrReadOnly
from subscriptions.exceptions import StripeWrongCustomer
from subscriptions.types import Protocol
from .conf import settings
from . import serializers
from . import payments
from typing import Dict, Any, Callable, List, Type, Union


DataType = Union[Dict[str, Any], List[Any]]


logger = logging.getLogger("django_stripe")


class StripeViewMixin(Protocol):
    throttle_scope = 'payments'
    status_code = status.HTTP_200_OK

    def make_request(self, request: Request, **data) -> DataType:
        raise NotImplementedError

    def run_stripe(self, request: Request, method: Callable = None, **data) -> DataType:
        method = method or self.make_request
        try:
            return method(request, **data)
        except stripe.error.StripeError as e:
            logger.exception(e, exc_info=e)
            raise exceptions.StripeException(detail=e)

    def run_stripe_response(self, request: Request, method: Callable = None,
                            status_code: int = None, **data) -> Response:
        return Response(
            self.run_stripe(request, method, **data),
            status=status_code or self.status_code
        )


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

    def run_stripe_response(self, request: Request, method: Callable = None,
                            status_code: int = None, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data or request.query_params)
        if serializer.is_valid():
            data = serializer.data
            result = self.run_stripe(request, method=method, **data, **kwargs)
        else:
            result = serializer.errors
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code or self.status_code)


class StripePriceCheckoutView(APIView, StripeViewMixin):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def make_checkout(request: Request, **data) -> stripe.checkout.Session:
        return payments.create_subscription_checkout(request.user, **data)

    def make_request(self, request: Request, **data) -> Dict[str, Any]:
        session = self.make_checkout(request, **data)
        return {'sessionId': session['id']}

    def post(self, request: Request, price_id: str) -> Response:
        return self.run_stripe_response(request, price_id=price_id)


class StripeSetupCheckoutView(StripePriceCheckoutView):

    @staticmethod
    def make_checkout(request: Request, **data) -> stripe.checkout.Session:
        return payments.create_setup_checkout(request.user, **data)

    def post(self, request: Request, **kwargs):
        return self.run_stripe_response(request, **kwargs)


class StripeBillingPortalView(APIView, StripeViewMixin):
    permission_classes = (IsAuthenticated,)
    throttle_scope = "payments"

    def make_request(self, request: Request, **kwargs) -> Dict[str, str]:
        session = payments.create_billing_portal(request.user, **kwargs)
        return {'url': session['url']}

    def post(self, request: Request) -> Response:
        return self.run_stripe_response(request)


class StripePricesView(APIView, StripeViewWithSerializerMixin):
    serializer_class = serializers.PriceSerializer

    def make_request(self, request: Request, **data) -> List[Dict[str, Any]]:
        return payments.get_subscription_prices(request.user, **data)

    def get(self, request: Request) -> Response:
        return self.run_stripe_response(request)


class StripeProductsView(APIView, StripeViewWithSerializerMixin):
    serializer_class = serializers.ProductSerializer

    def make_request(self, request: Request, **data) -> List[Dict[str, Any]]:
        return payments.get_subscription_products(request.user, **data)

    def get(self, request: Request) -> Response:
        return self.run_stripe_response(request)


class StripeSetupIntentView(APIView, StripeViewMixin):
    status_code = status.HTTP_201_CREATED
    permission_classes = (IsAuthenticated,)
    response_keys = ['id', 'client_secret', 'payment_method_types']

    def make_response(self, setup_intent: stripe.SetupIntent) -> Dict[str, Any]:
        return {k: setup_intent[k] for k in self.response_keys}

    def make_request(self, request: Request, **data) -> Dict[str, Any]:
        setup_intent = payments.create_setup_intent(request.user, **data)
        return self.make_response(setup_intent)

    def post(self, request: Request) -> Response:
        return self.run_stripe_response(request)


class StripePaymentMethodView(APIView, StripeViewMixin):
    status_code = status.HTTP_200_OK
    permission_classes = (IsAuthenticated,)
    response_keys_delete = ['customer', 'livemode', 'metadata', 'object']

    def make_response(self, payment_method: stripe.PaymentMethod) -> Dict[str, Any]:
        return {k: payment_method[k] for k in payment_method.keys() if k not in self.response_keys_delete}

    def make_request(self, request: Request, **data) -> List[Dict[str, Any]]:
        payment_methods = payments.list_payment_methods(request.user, **data)
        return sorted(
            [self.make_response(payment_method) for payment_method in payment_methods],
            key=itemgetter('default', 'created'), reverse=True
        )

    def _modify_default_payment_method(self, request, **data) -> List[Dict[str, Any]]:
        payments.modify_default_payment_method(request.user, **data)
        return self.run_stripe(request)

    def _detach_payment_method(self, request, **data) -> List[Dict[str, Any]]:
        try:
            payments.detach_payment_method(request.user, **data)
        except StripeWrongCustomer as e:
            raise exceptions.StripeException(f"No such PaymentMethod: '{data['payment_method_id']}'")
        return self.run_stripe(request)

    def _detach_all_payment_methods(self, request: Request, **data) -> List[Dict[str, Any]]:
        payments.detach_all_payment_methods(request.user, **data)
        return self.run_stripe(request)

    def get(self, request: Request) -> Response:
        return self.run_stripe_response(request)

    def put(self, request: Request, payment_method_id: str) -> Response:
        return self.run_stripe_response(request,
                                        method=self._modify_default_payment_method,
                                        payment_method_id=payment_method_id)

    def delete(self, request: Request, payment_method_id: str) -> Response:
        if payment_method_id == "*":
            return self.run_stripe_response(request,
                                            method=self._detach_all_payment_methods,
                                            status_code=status.HTTP_204_NO_CONTENT)
        return self.run_stripe_response(request,
                                        method=self._detach_payment_method,
                                        status_code=status.HTTP_204_NO_CONTENT,
                                        payment_method_id=payment_method_id)


class StripeSubscriptionView(APIView, StripeViewWithSerializerMixin):
    status_code = status.HTTP_201_CREATED
    serializer_class = serializers.SubscriptionSerializer
    permission_classes = (StripeCustomerIdRequiredOrReadOnly,)
    response_keys = ['id', 'cancel_at', 'current_period_end', 'current_period_start', 'days_until_due',
                     'latest_invoice', 'start_date', 'status', 'trial_end', 'trial_start']

    def make_response(self, subscription: stripe.Subscription) -> Dict[str, Any]:
        return {k: subscription[k] for k in self.response_keys}

    def make_request(self, request, **data) -> Dict[str, Any]:
        set_as_customer_default_payment_method = data.pop('set_as_customer_default_payment_method', False)
        subscription = payments.create_subscription(request.user, **data)
        if set_as_customer_default_payment_method and subscription['default_payment_method']:
            payments.modify_default_payment_method(self.request.user, subscription['default_payment_method'])
        return self.make_response(subscription)

    def post(self, request, price_id: str) -> Response:
        return self.run_stripe_response(request, price_id=price_id)


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
        subscription_id = self.kwargs.get('subscription_id')
        return payments.create_setup_checkout(self.request.user, subscription_id=subscription_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.make_checkout()
        context.update({'sessionId': session['id'], 'stripe_public_key': settings.STRIPE_PUBLIC_KEY})
        return context


class GoToCheckoutView(GoToSetupCheckoutView):

    def make_checkout(self, price_id: str = None):
        price_id = self.kwargs['price_id']
        return payments.create_subscription_checkout(self.request.user, price_id=price_id)


class GoToBillingPortalView(LoginRequiredMixin, RedirectView):

    def get_redirect_url(self, *args, **kwargs) -> str:
        session = payments.create_billing_portal(self.request.user, **kwargs)
        return session['url']
