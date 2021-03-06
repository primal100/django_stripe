from django.urls import re_path
from .views import (
    StripeSetupCheckoutView, StripePriceCheckoutView, StripeBillingPortalView, StripePricesView, StripeProductsView,
    StripeSetupIntentView, StripePaymentMethodView, StripeSubscriptionView, StripeInvoiceView
)


urlpatterns = [
    re_path(r'^checkout/(?P<price_id>.*)/', StripePriceCheckoutView.as_view(), name="checkout"),
    re_path(r'^setup-checkout/', StripeSetupCheckoutView.as_view(), name="setup-checkout"),
    re_path(r'^billing/', StripeBillingPortalView.as_view(), name="billing"),
    re_path(r'^prices/(?:(?P<obj_id>.*)/)?', StripePricesView.as_view(), name="prices"),
    re_path(r'^products/(?:(?P<obj_id>.*)/)?', StripeProductsView.as_view(), name="products"),
    re_path(r'^setup-intents', StripeSetupIntentView.as_view(), name="setup-intents"),
    re_path(r'^payment-methods/(?:(?P<obj_id>.*)/)?', StripePaymentMethodView.as_view(), name="payment-methods"),
    re_path(r'^subscriptions/(?:(?P<obj_id>.*)/)?', StripeSubscriptionView.as_view(), name="subscriptions"),
    re_path(r'^invoices/(?:(?P<obj_id>.*)/)?', StripeInvoiceView.as_view(), name="invoices")
]