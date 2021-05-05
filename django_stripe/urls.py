from django.conf.urls import url
from .views import StripeCheckoutView, StripeBillingPortalView, StripePricesView, StripeProductsView


urlpatterns = [
    url(r'^checkout', StripeCheckoutView.as_view(), name="checkout"),
    url(r'^billing', StripeBillingPortalView.as_view(), name="billing"),
    url(r'^prices', StripePricesView.as_view(), name="prices"),
    url(r'^products', StripeProductsView.as_view(), name="products")
]