from django.conf.urls import url
from .views import (
    StripeCheckoutView, StripeBillingPortalView, StripePricesView, StripeProductsView,
    StripeSubscriptionView
)


urlpatterns = [
    url(r'^checkout/(?P<price_id>.*)', StripeCheckoutView.as_view(), name="checkout"),
    url(r'^billing', StripeBillingPortalView.as_view(), name="billing"),
    url(r'^prices', StripePricesView.as_view(), name="prices"),
    url(r'^products', StripeProductsView.as_view(), name="products"),
    url(r'^subscriptions/(?P<price_id>.*)', StripeSubscriptionView.as_view(), name="subscriptions")
]