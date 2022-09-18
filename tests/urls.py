"""tests URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.urls import re_path
from django_stripe.views import (
    GoToSetupCheckoutView, GoToCheckoutView, GoToBillingPortalView, SubscriptionPortalView, SubscriptionHistoryView)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include("django_stripe.urls")),
    path('api-auth/', include('rest_framework.urls')),
    re_path('^checkout/(?P<price_id>.*)/', GoToCheckoutView.as_view(), name='go-to-checkout'),
    re_path(r'^setup-checkout/(?:/(?P<subscription_id>.*)/)?', GoToSetupCheckoutView.as_view(), name='go-to-setup-checkout'),
    path('^billing-portal/', GoToBillingPortalView.as_view(), name='go-to-billing-portal'),
    path(r'subscriptions/', SubscriptionHistoryView.as_view(), name='subscription-history'),
    path(r'', SubscriptionPortalView.as_view(), name='subscription-portal'),

]
