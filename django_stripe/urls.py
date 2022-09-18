from django.urls import path, re_path
from .views import (
    StripeSetupCheckoutView, StripePriceCheckoutView, StripeBillingPortalView, StripePricesView, StripeProductsView,
    StripeSetupIntentView, StripePaymentMethodView, StripeSubscriptionView, StripeInvoiceView
)


urlpatterns = [
    re_path(r'^checkout/(?P<price_id>.*)/', StripePriceCheckoutView.as_view(), name="checkout"),
    path('setup-checkout/', StripeSetupCheckoutView.as_view(), name="setup-checkout"),
    path(r'^billing/', StripeBillingPortalView.as_view(), name="billing"),
    re_path(r'^prices/(?:(?P<obj_id>.*)/)?', StripePricesView.as_view(), name="prices"),
    re_path(r'^products/(?:(?P<obj_id>.*)/)?', StripeProductsView.as_view(), name="products"),
    path('setup-intents', StripeSetupIntentView.as_view(), name="setup-intents"),
    re_path(r'^payment-methods/(?:(?P<obj_id>.*)/)?', StripePaymentMethodView.as_view(), name="payment-methods"),
    re_path(r'^subscriptions/(?:(?P<obj_id>.*)/)?', StripeSubscriptionView.as_view(), name="subscriptions"),
    re_path(r'^invoices/(?:(?P<obj_id>.*)/)?', StripeInvoiceView.as_view(), name="invoices")
]
