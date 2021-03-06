import datetime

import stripe
from django.views.generic import RedirectView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView
from .conf import settings
from . import serializers
from . import payments
from .utils import get_user_if_token_user
from .logging import logger
from .view_mixins import StripeListMixin, StripeCreateMixin, StripeCreateWithSerializerMixin, StripeModifyMixin, StripeDeleteMixin
from typing import Dict, Any, List, Iterable, Optional


class StripePriceCheckoutView(APIView, StripeCreateMixin):
    """
    An API View for creating a Stripe Subscription Checkout. The price_id must be provided in the url.
    Methods Supported: POST
    """
    permission_classes = (IsAuthenticated,)
    response_keys: tuple = ("id",)

    def create(self, request: Request, **data) -> stripe.checkout.Session:
        return payments.create_subscription_checkout(request.user, rest=True, **data)


class StripeSetupCheckoutView(StripePriceCheckoutView):
    """
    An API View for creating a Stripe Setup Checkout.
    Methods Supported: POST
    """
    def create(self, request: Request, **data) -> stripe.checkout.Session:
        return payments.create_setup_checkout(request.user, rest=True, **data)


class StripeBillingPortalView(APIView, StripeCreateMixin):
    """
    An API View for creating a Stripe Billing Portal.
    Methods Supported: POST
    """
    permission_classes = (IsAuthenticated,)
    response_keys: tuple = ("url",)

    def create(self, request: Request, **kwargs) -> stripe.billing_portal.session:
        return payments.create_billing_portal(request.user, **kwargs)


class StripeSetupIntentView(APIView, StripeCreateMixin):
    """
    An API View for creating a Stripe Setup Intent.
    Methods Supported: POST
    """
    permission_classes = (IsAuthenticated,)
    response_keys = ('id', 'client_secret', 'payment_method_types')

    def create(self, request: Request, **data) -> stripe.SetupIntent:
        return payments.create_setup_intent(request.user, **data)


class StripePricesView(APIView, StripeListMixin):
    """
    An API View for listing and retrieving prices including subscription information if the user is authenticated.
    Methods Supported: GET
    """
    serializer_class = serializers.PriceSerializer
    response_keys = ("id", "recurring", "type", "currency", "unit_amount", "unit_amount_decimal",
                     "nickname", "metadata", "product", "subscription_info")
    order_by = ("unit_amount", "id")
    order_reverse = False

    def list(self, request: Request, **kwargs) -> List[Dict[str, Any]]:
        return payments.get_prices(request.user, rest=True, **kwargs)

    def retrieve(self, request: Request, price_id: str) -> Dict[str, Any]:
        return payments.retrieve_price(request.user, price_id, rest=True)


class StripeProductsView(APIView, StripeListMixin):
    """
    An API View for listing and retrieving products including subscription information if the user is authenticated.
    Methods Supported: GET
    """
    serializer_class = serializers.ProductSerializer
    response_keys = ("id", "images", "metadata", "name", "prices", "shippable", "subscription_info",
                     "type", "unit_label", "url")
    order_by = ("id",)
    order_reverse = False

    def list(self, request: Request, **kwargs) -> List[Dict[str, Any]]:
        return payments.get_products(request.user, rest=True, **kwargs)

    def retrieve(self, request: Request, product_id: str) -> Dict[str, Any]:
        return payments.retrieve_product(request.user, product_id, rest=True)


class StripeInvoiceView(APIView, StripeListMixin):
    """
    An API View for listing and retrieving a user's invoices.
    Methods Supported: GET
    """
    stripe_resource = stripe.Invoice
    status_code = status.HTTP_200_OK
    serializer_class = serializers.InvoiceSerializer
    permission_classes = (IsAuthenticated,)
    response_keys = ('id', "amount_due", "amount_paid", "amount_remaining", "billing_reason",
                     "created", "hosted_invoice_url", "invoice_pdf", "next_payment_attempt", "status", "subscription")

    @property
    def name_in_errors(self) -> str:
        return self.stripe_resource.__name__.lower()


class StripePaymentMethodView(APIView, StripeListMixin, StripeModifyMixin, StripeDeleteMixin):
    """
    An API View for listing, modifying, retrieving and detaching a user's payment methods. Payment Methods are created seperately using stripe.js.
    Methods Supported: GET, PUT, DELETE
    """
    stripe_resource = stripe.PaymentMethod
    serializer_classes = {
        'PUT': serializers.PaymentMethodModifySerializer,
    }
    modify_serializer_class = serializers.PaymentMethodModifySerializer
    status_code = status.HTTP_200_OK
    permission_classes = (IsAuthenticated,)
    response_keys_exclude = ('customer', 'livemode', 'metadata', 'object')
    order_by = ('default', 'created', 'id')

    def list(self, request: Request, **data) -> Iterable[stripe.PaymentMethod]:
        return payments.list_payment_methods(request.user, **data)

    def modify(self, request, obj_id: str, **data) -> Dict[str, Any]:
        return payments.modify_payment_method(request.user, obj_id=obj_id, **data)

    def destroy(self, request: Request, obj_id: str) -> None:
        """
        Detaches a payment method if a user owns it.
        If "*" is givan as the payment method, all payment methods for that user are detached.
        """
        if obj_id == "*":
            payments.detach_all_payment_methods(request.user)
        else:
            payments.detach_payment_method(request.user, obj_id)


class StripeSubscriptionView(APIView, StripeListMixin, StripeCreateWithSerializerMixin,
                             StripeModifyMixin, StripeDeleteMixin):
    """
    An API View for creating, listing, modifying, cancelling and retrieving a user's subscription.
    Methods Supported: POST, GET, PUT, DELETE
    """
    stripe_resource = stripe.Subscription
    status_code = status.HTTP_201_CREATED
    delete_status_code = status.HTTP_200_OK
    serializer_classes = {
        'GET': serializers.SubscriptionListSerializer,
        'PUT': serializers.SubscriptionModifySerializer,
        'POST': serializers.SubscriptionCreateSerializer
    }
    permission_classes = (IsAuthenticated,)
    key_rename = {'plan__id': 'price'}
    response_keys = ('id', 'created', 'plan__product', 'plan__id', 'cancel_at', 'current_period_end',
                     'current_period_start', 'days_until_due', 'default_payment_method', 'latest_invoice',
                     'start_date', 'status', 'trial_end', 'trial_start')

    @property
    def name_in_errors(self) -> str:
        return self.stripe_resource.__name__.lower()

    def create(self, request, **data) -> Dict[str, Any]:
        return payments.create_subscription(request.user, **data)

    def modify(self, request, sub_id: str, **data) -> Dict[str, Any]:
        return payments.modify_subscription(request.user, sub_id, **data)


class GoToSetupCheckoutView(LoginRequiredMixin, TemplateView):
    """
    A regular Django view for redirecting a user to a newly created Stripe Setup Checkout session.
    Methods Supported: GET
    """
    template_name = 'django_stripe/checkout.html'

    def make_checkout(self):
        subscription_id = self.kwargs.get('subscription_id')
        return payments.create_setup_checkout(self.request.user, subscription_id=subscription_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.make_checkout()
        context.update({'sessionId': session['id'], 'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY})
        return context


class GoToCheckoutView(GoToSetupCheckoutView):
    """
    A regular Django view for redirecting a user to a newly created Subscription Checkout session.
    Methods Supported: GET
    """
    def make_checkout(self, price_id: str = None):
        price_id = self.kwargs['price_id']
        return payments.create_subscription_checkout(self.request.user, price_id=price_id)


class GoToBillingPortalView(LoginRequiredMixin, RedirectView):
    """
    A regular Django view for redirecting a user to a newly created Billing Portal session.
    Methods Supported: GET
    """
    def get_redirect_url(self, *args, **kwargs) -> str:
        session = payments.create_billing_portal(self.request.user, **kwargs)
        return session['url']


class BaseCheckoutView(LoginRequiredMixin, TemplateView):
    """
    Base Class for django_stipe custom checkouts views.
    Methods Supported: GET
    """
    product_id: str = None
    date_format: str = "%A %d %B %Y"

    def get_product_id(self) -> str:
        return self.product_id or settings.STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID

    def get(self, request, *args, **kwargs):
        if request.user and request.user.is_authenticated:
            payments.create_customer(request.user)
        return super().get(request, *args, **kwargs)

    def get_default_country(self):
        country = None
        if settings.COUNTRY_HEADER:
            country = self.request.META.get(settings.COUNTRY_HEADER, '')
        if not country:
            country = settings.STRIPE_CHECKOUT_DEFAULT_COUNTRY
        return country or "US"

    def timestamp_format(self, timestamp: Optional[int]):
        if timestamp:
            return datetime.datetime.fromtimestamp(timestamp).strftime(self.date_format)
        return None


class SubscriptionPortalView(BaseCheckoutView):
    """
    The django_stripe custom checkout views. Allows a user to select a price and then subscribe on the same page.
    Methods Supported: GET
    """
    template_name = 'django_stripe/subscription_portal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_user_if_token_user(self.request.user)
        product_id = self.get_product_id()
        logger.debug("Opening payments portal for user %d, product %s", user.id, product_id)
        context['product'] = payments.retrieve_product(user, product_id)
        context['product']['subscription_info']['current_period_end'] = self.timestamp_format(context['product']['subscription_info']['current_period_end'])
        context['product']['subscription_info']['cancel_at'] = self.timestamp_format(context['product']['subscription_info']['cancel_at'])
        context['dev_mode'] = settings.STRIPE_CHECKOUT_DEV_MODE and 'test' in settings.STRIPE_PUBLISHABLE_KEY
        context['title'] = settings.STRIPE_CHECKOUT_TITLE
        context['header_link'] = reverse("subscription-history")
        context['header_link_text'] = "Subscription History"
        context['js_config'] = {
            'subscriptionInfo': context['product']['subscription_info'],
            'user_email': user.email,
            'country': self.get_default_country(),
            'hide_postal_code': settings.STRIPE_CREDIT_CARD_HIDE_POSTAL_CODE,
            'stripePublishableKey': settings.STRIPE_PUBLISHABLE_KEY,
            'paymentMethods': settings.STRIPE_PAYMENT_METHOD_TYPES,
            'subscription_api_url': reverse("subscriptions"),
            'setup_intents_url': reverse("setup-intents")
        }
        return context


class SubscriptionHistoryView(BaseCheckoutView):
    """
    The django_stripe view display a user's subscription status and invoice history.
    Methods Supported: GET
    """
    template_name = 'django_stripe/subscription_history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_user_if_token_user(self.request.user)
        product_id = self.get_product_id()
        logger.debug("Opening subscription history portal for user %d, product %s", user.id, product_id)
        subscriptions = payments.list_customer_resource(user, stripe.Subscription)
        context['subscription'] = None
        for status in payments.subscription_alive_statuses:
            relevant_subscriptions = sorted(filter(lambda s: s['status'] == status, subscriptions), key= lambda s: s['created'], reverse=True)
            if relevant_subscriptions:
                context['subscription'] = relevant_subscriptions[0]
                break
        payment_method_id = context['subscription'].get('default_payment_method', None) if context['subscription'] else None
        if payment_method_id:
            context['payment_method'] = payments.retrieve(user, stripe.PaymentMethod, payment_method_id)
        else:
            context['payment_method'] = None
        context['invoices'] = payments.list_customer_resource(user, stripe.Invoice)
        context['header_link'] = reverse("subscription-portal")
        context['header_link_text'] = "Subscription Portal"
        context['subscription']['current_period_end'] = self.timestamp_format(context['subscription']['current_period_end'])
        context['subscription']['cancel_at'] = self.timestamp_format(context['subscription']['cancel_at'])
        context['dev_mode'] = settings.STRIPE_CHECKOUT_DEV_MODE and 'test' in settings.STRIPE_PUBLISHABLE_KEY
        context['title'] = settings.STRIPE_CHECKOUT_TITLE
        return context
