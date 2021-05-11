from django.conf.urls import url
from .views import (
    StripeSetupCheckoutView, StripePriceCheckoutView, StripeBillingPortalView, StripePricesView, StripeProductsView,
    StripeSetupIntentView, StripePaymentMethodView, StripeSubscriptionView,
)


urlpatterns = [
    url(r'^checkout/(?P<price_id>.*)', StripePriceCheckoutView.as_view(), name="checkout"),
    url(r'^setup-checkout/', StripeSetupCheckoutView.as_view(), name="setup-checkout"),
    url(r'^billing', StripeBillingPortalView.as_view(), name="billing"),
    url(r'^prices', StripePricesView.as_view(), name="prices"),
    url(r'^products', StripeProductsView.as_view(), name="products"),
    url(r'^setup-intents', StripeSetupIntentView.as_view(), name="setup-intents"),
    url(r'^payment-methods/(?:/(?P<payment_method_id>.*)/)?', StripePaymentMethodView.as_view(), name="payment-methods"),
    url(r'^subscriptions/(?P<price_id>.*)', StripeSubscriptionView.as_view(), name="subscriptions")
]