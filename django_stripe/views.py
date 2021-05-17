import stripe
from django.contrib import messages
from django.views.generic import FormView, RedirectView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from stripe.error import StripeError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.views import APIView
from . import exceptions
import logging
from .conf import settings
from .forms import SubscriptionForm
from . import serializers
from . import payments
from .view_mixins import StripeListMixin, StripeCreateMixin, StripeCreateWithSerializerMixin, StripeModifyMixin, StripeDeleteMixin
from typing import Dict, Any, List, Iterable


logger = logging.getLogger("django_stripe")


class StripePriceCheckoutView(APIView, StripeCreateMixin):
    permission_classes = (IsAuthenticated,)
    response_keys: tuple = ("id",)

    def create(self, request: Request, **data) -> stripe.checkout.Session:
        return payments.create_subscription_checkout(request.user, **data)


class StripeSetupCheckoutView(StripePriceCheckoutView):

    def create(self, request: Request, **data) -> stripe.checkout.Session:
        return payments.create_setup_checkout(request.user, **data)


class StripeBillingPortalView(APIView, StripeCreateMixin):
    permission_classes = (IsAuthenticated,)
    response_keys: tuple = ("url",)

    def create(self, request: Request, **kwargs) -> stripe.billing_portal.session:
        return payments.create_billing_portal(request.user, **kwargs)


class StripeSetupIntentView(APIView, StripeCreateMixin):
    permission_classes = (IsAuthenticated,)
    response_keys = ('id', 'client_secret', 'payment_method_types')

    def create(self, request: Request, **data) -> stripe.SetupIntent:
        return payments.create_setup_intent(request.user, **data)


class StripePricesView(APIView, StripeListMixin):
    serializer_class = serializers.PriceSerializer
    response_keys = ("id", "recurring", "type", "currency", "unit_amount", "unit_amount_decimal",
                     "nickname", "metadata", "product", "subscription_info")
    order_by = ("unit_amount", "id")
    order_reverse = False

    def list(self, request: Request, **kwargs) -> List[Dict[str, Any]]:
        return payments.get_prices(request.user, **kwargs)

    def retrieve(self, request: Request, id: str) -> Dict[str, Any]:
        return payments.retrieve_price(request.user, id)


class StripeProductsView(APIView, StripeListMixin):
    serializer_class = serializers.ProductSerializer
    response_keys = ("id", "images", "metadata", "name", "prices", "shippable", "subscription_info",
                     "type", "unit_label", "url")
    order_by = ("id",)
    order_reverse = False

    def list(self, request: Request, **kwargs) -> List[Dict[str, Any]]:
        return payments.get_products(request.user, **kwargs)

    def retrieve(self, request: Request, id: str) -> Dict[str, Any]:
        return payments.retrieve_product(request.user, id)


class StripeInvoiceView(APIView, StripeListMixin):
    stripe_resource = stripe.Invoice
    status_code = status.HTTP_200_OK
    serializer_class = serializers.InvoiceSerializer
    permission_classes = (IsAuthenticated,)
    response_keys = ('id', "amount_due", "amount_paid", "amount_remaining", "billing_reason",
                     "created","hosted_invoice_url", "invoice_pdf", "next_payment_attempt", "status", "subscription")

    @property
    def name_in_errors(self) -> str:
        return self.stripe_resource.__name__.lower()


class StripePaymentMethodView(APIView, StripeListMixin, StripeModifyMixin, StripeDeleteMixin):
    stripe_resource = stripe.PaymentMethod
    serializer_classes = {
        'PUT': serializers.PaymentMethodModifySerializer,
    }
    modify_serializer_class = serializers.PaymentMethodModifySerializer
    status_code = status.HTTP_200_OK
    permission_classes = (IsAuthenticatedOrReadOnly,)
    response_keys_exclude = ('customer', 'livemode', 'metadata', 'object')
    order_by = ('default', 'created', 'id')

    def list(self, request: Request, **data) -> Iterable[stripe.PaymentMethod]:
        return payments.list_payment_methods(request.user, **data)

    def modify(self, request, id: str, **data) -> Dict[str, Any]:
        return payments.modify_payment_method(request.user, id=id, **data)

    def destroy(self, request: Request, id: str) -> None:
        if id == "*":
            payments.detach_all_payment_methods(request.user)
        else:
            payments.detach_payment_method(request.user, id)


class StripeSubscriptionView(APIView, StripeListMixin, StripeCreateWithSerializerMixin,
                             StripeModifyMixin, StripeDeleteMixin):
    stripe_resource = stripe.Subscription
    status_code = status.HTTP_201_CREATED
    serializer_classes = {
        'GET': serializers.SubscriptionListSerializer,
        'PUT': serializers.SubscriptionModifySerializer,
        'POST': serializers.SubscriptionCreateSerializer
    }
    permission_classes = (IsAuthenticatedOrReadOnly,)
    response_keys = ('id', 'cancel_at', 'current_period_end', 'current_period_start', 'days_until_due',
                     'default_payment_method', 'latest_invoice', 'start_date', 'status', 'trial_end', 'trial_start')

    @property
    def name_in_errors(self) -> str:
        return self.stripe_resource.__name__.lower()

    def create(self, request, **data) -> Dict[str, Any]:
        return payments.create_subscription(request.user, **data)

    def modify(self, request, id: str, **data) -> Dict[str, Any]:
        return payments.modify_subscription(request.user, id, **data)


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
