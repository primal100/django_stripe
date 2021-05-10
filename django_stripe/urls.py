from django.conf.urls import url
from .views import (
    StripeSetupCheckoutView, StripePriceCheckoutView, StripeBillingPortalView,
    StripePricesView, StripeProductsView, StripeSubscriptionView, StripeSetupIntentView
)


urlpatterns = [
    url(r'^checkout/(?P<price_id>.*)', StripePriceCheckoutView.as_view(), name="checkout"),
    url(r'^setup-checkout/', StripeSetupCheckoutView.as_view(), name="setup-checkout"),
    url(r'^billing', StripeBillingPortalView.as_view(), name="billing"),
    url(r'^prices', StripePricesView.as_view(), name="prices"),
    url(r'^products', StripeProductsView.as_view(), name="products"),
    url(r'^setup-intents', StripeSetupIntentView.as_view(), name="setup-intents"),
    url(r'^subscriptions/(?P<price_id>.*)', StripeSubscriptionView.as_view(), name="subscriptions")
]