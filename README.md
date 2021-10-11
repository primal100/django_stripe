# Django Stripe

This library is designed to make it as easy as possible for Django web developers to manage Stripe Subscriptions. 

There are three ways to use ```django-stripe```:

1) A full featured Rest Framework API allowing end users to view products and prices and manage their subsciptions, payment methods and invoices.

2) A self-hosted alternative to Stripe Checkout optimized for subscriptions.

3) Functions which can easily be utilized in Django views for building custom checkouts are for checking a user's subscription status

The library is built with a particular focus on Django users which are central to everything. For example, users are restricted from accessing private objects not belonging to them.

## Getting Started

To install:

```shell
pip install django-stripe
```

You must have a ```User``` model which implements the ```stripe_customer_id``` property:

```python
from django.db.contrib.auth import User
from django.db import models


class StripeUser(User):
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

```

```Django Stripe``` also provides a built-in AbstractModel with the ```stripe_customer_id``` included. Because it's abstract it will not be enabled by default but can be subclassed:

```python
from django_stripe.models import StripeCustomerUser

class User(StripeCustomerUser):
    pass
```


If you already have a database field for storing a customer id or prefer a different field name, you can add a property:

```python
from django.db.contrib.auth import User
from django.db import models


class StripeUser(User):
    customer_id = models.CharField(max_length=255)

    @property
    def stripe_customer_id(self):
        return self.customer_id
```

There is a feature in ```django_stripe``` which allows users to be given temporary free access. To enable this feature, add the ```allowed_access_until``` field:


```python
from django.db import models
from django_stripe.models import StripeCustomerUser


class User(StripeCustomerUser):
    allowed_access_until = models.DateTimeField(blank=True, null=True)
```

Now, configure some settings in your web project settings.py file:

1) Add ```rest_framework``` and ```django_stripe``` to INSTALLED_APPS.
2) Set AUTH_USER_MODEL to your custom user
3) In Stripe Dashboard create at least one subscription-based product and one price. In the price add the following metadata which will appear in the custom checkout: 

- additional_info
- price_header

Add your test api keys and product id to your app.

```python
INSTALLED_APPS = [
    ...,
    'rest_framework',
    'django_stripe'

AUTH_USER_MODEL = "django_stripe_testapp.User"

STRIPE_SECRET_KEY="sk_test..."
STRIPE_PUBLISHABLE_KEY="pk_test..."
STRIPE_DEFAULT_SUBSCRIPTION_PRODUCT_ID="prod_..."
```


The three Stripe settings can also be provided by environment variables (recommended for production).

There are many optional settings which will be covered later.

Finally, let's add some paths to urls.py. This example shows how to enable all the URLs but you can pick and choose which ones you need.

```python
from django.contrib import admin
from django.urls import path, include
from django.urls import re_path
from django_stripe.views import (
    GoToSetupCheckoutView, GoToCheckoutView, GoToBillingPortalView, SubscriptionPortalView, SubscriptionHistoryView)

urlpatterns = [
    path('admin/', admin.site.urls),                                                                                            # The Django Admin
    path('api/', include("django_stripe.urls")),                                                                                # The Rest APIs
    re_path(r'^api-auth/', include('rest_framework.urls')),                                                                     # Login and logout
    re_path('^checkout/(?P<price_id>.*)/', GoToCheckoutView.as_view(), name='go-to-checkout'),                                  # Redirect a Stripe Checkout to allow a user to subscribe
    re_path(r'^setup-checkout/(?:/(?P<subscription_id>.*)/)?', GoToSetupCheckoutView.as_view(), name='go-to-setup-checkout'),   # Redirect a Stripe Checkout to allow a user to subscribe
    re_path(r'^billing-portal/', GoToBillingPortalView.as_view(), name='go-to-billing-portal'),                                 # Redirect to Stripe Billing Portal, needs to be enabled on Stripe.com
    path(r'subscriptions/', SubscriptionHistoryView.as_view(), name='subscription-history'),                                    # Part of the django-stripe subscription portal showing subscription status and invoices
    path(r'', SubscriptionPortalView.as_view(), name='subscription-portal'),                                                    # The django-stripe subscription portal
]
```


The url paths can be changed but the view names should be consistent. 
The ```SubscriptionPortalView and``` ```SubscriptionHistoryView need``` must be used together and require at minimum the ```StripeSetupIntentView``` and ```StripeSubscriptionView``` API Views (included in ```django_stripe.urls```) to be enabled.

Then, prepare your app and start it:

```shell
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

You should now see the custom checkout when you browse to ```localhost:8000```. It will look best if you create 2 or 3 prics with metadata ```price_header``` and ```additional_info``` set in the Stripe dashboard.

## Rest API

Most of the offical Stripe APIs are intended to be run server-side (the Secret API Key is required). The ```Django Stripe``` rest APIs are built on top of those and are designed to be run from the client. They convert the client request including authentication details into a server-sde request to the Stripe API and return only data that is relevant to the user. They also prevent users viewing information belonging to other users by checking their customer id.

The Rest APIs are implemented using ```Django Rest Framework```. The easiest way to get familiar with the APIs is to use the ```rest-framework``` browsable API by opening a browser and going to the API URL.

Most resources have a combination of resource URLs (for creating and listing) and instance URLs (for viewing, modifying and deleting objects).

URLs listed in this tutorial assume the Getting Started procedure was followed but can easily by adjusted if the urls were changed.

### Products

Methods supported: GET

Products are read-only over the API. They can be created and changed on the Stripe Dashboard.

The view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripeProductsView

urlpatterns = [
    re_path(r'^products/(?:(?P<obj_id>.*)/)?', StripeProductsView.as_view(), name="products")
]
```

To list products:

http://localhost:8000/api/products/

The following filters can be applied by including with json data in the request:

```
- ids: List[str]
```

To retrieve a single product:

http://localhost:8000/api/prices/prod_Jo3KY017h0SZ1x/

Example list request:

```http request
GET /api/products
HTTP 200 OK
Allow: GET, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

[
    {
        "id": "prod_Jo3KY017h0SZ1x",
        "images": [],
        "metadata": {},
        "name": "Decoder Subscription",
        "prices": [
            {
                "id": "price_1JB9PtCz06et8VuzfLu1Z9bf",
                "recurring": {
                    "aggregate_usage": null,
                    "interval": "year",
                    "interval_count": 1,
                    "trial_period_days": null,
                    "usage_type": "licensed"
                },
                "type": "recurring",
                "currency": "eur",
                "unit_amount": 99999,
                "unit_amount_decimal": "99999",
                "nickname": "Gold",
                "metadata": {
                    "additional_info": "Includes Everything",
                    "price_header": "Gold"
                },
                "subscription_info": {
                    "subscribed": true,
                    "cancel_at": null,
                    "current_period_end": 1664832172
                }
            }
        ],
        "shippable": null,
        "subscription_info": {
            "subscribed": true,
            "cancel_at": null,
            "current_period_end": 1664832172
        },
        "type": "service",
        "unit_label": null,
        "url": null
    },
]
```

### Prices

Methods supported: GET

Prices are read-only over the API. They can be created and changed on the Stripe Dashboard.

The view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripePricesView

urlpatterns = [
    re_path(r'^prices/(?:(?P<obj_id>.*)/)?', StripePricesView.as_view(), name="prices"),
]
```


To list prices:

http://localhost:8000/api/prices/

The following filters can be applied by including with json data in the request:

```
- currency: str
- product: str
```

To retrieve a single price:

http://localhost:8000/api/prices/price_1JB9PtCz06et8VuzfLu1Z9bf/

Example list request:
```http request
GET /api/prices/

HTTP 200 OK
Allow: GET, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

[
    {
        "id": "price_1JB9PtCz06et8VuzfLu1Z9bf",
        "recurring": {
            "aggregate_usage": null,
            "interval": "month",
            "interval_count": 1,
            "trial_period_days": null,
            "usage_type": "licensed"
        },
        "type": "recurring",
        "currency": "usd",
        "unit_amount": 129,
        "unit_amount_decimal": "129",
        "nickname": null,
        "metadata": {
            "additional_info": "Includes Everything",
            "price_header": "Gold"
        },
        "product": "price_1JB9PtCz06et8VuzfLu1Z9bf",
        "subscription_info": {
            "subscribed": false,
            "current_period_end": null,
            "cancel_at": null
        }
    }
]
```


### Stripe Checkouts

Methods supported: POST

This view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripePriceCheckoutView

urlpatterns = [
    re_path(r'^checkout/(?P<price_id>.*)/', StripePriceCheckoutView.as_view(), name="checkout")
]
```

Create a Stripe checkout by making a POST request to the following URL including the ```price_id``` of the price the user wishes to subscribe to:

```http request
POST /api/checkout/price_1JB9PtCz06et8VuzfLu1Z9bf/

HTTP 201 Created
Allow: POST, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "cs_test_a1vlrEt9aMdfpo42C6zuqWIXEpZdkjw0ESKga4K7tmdwYhwxknD5mnOxDS"
}
```
The user can then be re-directed the new checkout using the ```stripe.js stripe.redirectToCheckout``` method. See the built-in checkout.html template for an example.

### Stripe Setup Checkouts

Methods supported: POST

This view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripeSetupCheckoutView

urlpatterns = [
    re_path(r'^setup-checkout/', StripeSetupCheckoutView.as_view(), name="setup-checkout")
]
```

Create a Stripe Setup Checkout for adding payments details for future usage by making a POST request to the following URL:

```http request
POST /api/setup-checkout/

HTTP 201 Created
Allow: POST, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "cs_test_c1U7FS4ro1GP9ic7iOUQInwcRLhoU6tIB00K0g4h0K2LROoL3dYe9Vr920"
}
```

The user can then be re-directed the new checkout session using the ```stripe.js stripe.redirectToCheckout``` method. See the built-in checkout.html template for an example.


### Stripe Billing Portal

Methods supported: POST

This view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripeBillingPortalView

urlpatterns = [
    re_path(r'^billing/', StripeBillingPortalView.as_view(), name="billing")
]
```

Create a Stripe Billing Portal subscriptions by making a post request to the following URL:

```http request
POST /api/billing/

HTTP 201 Created
Allow: POST, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "url": "https://billing.stripe.com/session/_KNoJpxaBUCxpjZYkNNu4INQzyeJfvf6"
}
```

Billing Portals must be enabled from the Stripe Dashboard.

The user can then be re-directed to the given URL.


### Stripe Setup Intent

Methods supported: POST

This view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripeSetupIntentView

urlpatterns = [
    re_path(r'^setup-intents', StripeSetupIntentView.as_view(), name="setup-intents")
]
```

Create a Stripe Setup Intent by making a post request to the following URL:

```http request
POST /api/setup-intents/

HTTP 201 Created
Allow: POST, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "seti_1Jj2iaCz06et8VuzkxkWgrkb",
    "client_secret": "seti_1Jj2iaCz06et8VuzkxkWgrkb_secret_KNoL0pH9o4nY9PvJf9grD0SKQKltjfH",
    "payment_method_types": [
        "card"
    ]
```

The ```client_secret``` can then be used to creating a new payment method with ```stripe.js stripe.confirmCardSetup``` method.

The payment method types support can be customized using in settings.py with ```STRIPE_PAYMENT_METHOD_TYPES```.


### Invoices

Methods supported: GET

Invoices are read-only over the API. They are generated automatically and managed by Stripe.

This view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripeInvoiceView

urlpatterns = [
    re_path(r'^invoices/(?:(?P<obj_id>.*)/)?', StripeInvoiceView.as_view(), name="invoices")
]
```

To list the authenticated user's invoices:

http://localhost:8000/api/invoices/

The following filters can be applied by including with json data in the request:

```
- status: str (one of draft, open, paid, uncollectible, void)
- subscription: str
```

To retrieve a single invoice:

http://localhost:8000/api/invoices/in_1Jj2tFCz06et8Vuzu3vzIdFJ/

Example list request:

```http request
GET /api/invoices/

HTTP 200 OK
Allow: GET, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

[
    {
        "id": "in_1Jj2tFCz06et8Vuzu3vzIdFJ",
        "amount_due": 29999,
        "amount_paid": 29999,
        "amount_remaining": 0,
        "billing_reason": "subscription_create",
        "created": 1633563554,
        "hosted_invoice_url": "https://invoice.stripe.com/i/acct_....",
        "invoice_pdf": "https://pay.stripe.com/invoice/acct_....",
        "next_payment_attempt": null,
        "status": "paid",
        "subscription": "sub_IMxfbzPJTsf22d"
    },
]
```


### Payment Methods

Methods Supported: GET, PUT, DELETE

This view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripePaymentMethodView

urlpatterns = [
    re_path(r'^payment-methods/(?:(?P<obj_id>.*)/)?', StripePaymentMethodView.as_view(), name="payment-methods")
]
```

Paymend methods can be read, modified or detached from a customer over the Rest API. To create a payment method, use the Stripe official Checkout or Billing Portal, ```django-stripe``` checkout or the Setup Intent API and ```stripe.js```.

To list the authenticated user's payment methods:

http://localhost:8000/api/payment-methods/

To retrieve a single payment method:

http://localhost:8000/api/payment-methods/pm_1Jj2tFCz06et8Vuzu3vzIdFJ/

Example list request:

```http request
GET /api/payment-methods/

HTTP 200 OK
Allow: GET, PUT, DELETE, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept


[
    {
        "id": "pm_1Jj2tFCz06et8Vuzu3vzIdFJ",
        "billing_details": {
            "address": {
                "city": "Dublin",
                "country": "IE",
                "line1": "O'Connell Street",
                "line2": null,
                "postal_code": "",
                "state": "Dublin"
            },
            "email": null,
            "name": "Jane Doe",
            "phone": null
        },
        "card": {
            "brand": "visa",
            "checks": {
                "address_line1_check": "pass",
                "address_postal_code_check": null,
                "cvc_check": "pass"
            },
            "country": "IE",
            "exp_month": 4,
            "exp_year": 2055,
            "fingerprint": "4fs8d0OveGSOiKRG",
            "funding": "credit",
            "generated_from": null,
            "last4": "4242",
            "networks": {
                "available": [
                    "visa"
                ],
                "preferred": null
            },
            "three_d_secure_usage": {
                "supported": true
            },
            "wallet": null
        },
        "created": 1633563553,
        "type": "card",
        "default": false
    },   
]
```

Detach a Payment Method from the authenticated user:
```http request
DELETE /api/payment-methods/pm_1Jj2tFCz06et8Vuzu3vzIdFJ/

HTTP 204 No Content
Allow: GET, PUT, DELETE, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept
```

Detach all Payment Methods for the authenticated user:
```http request
DELETE /api/payment-methods/*/

HTTP 204 No Content
Allow: GET, PUT, DELETE, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept
```


To update a Payment Method for the authenticated user, send the following request with one or all of the following data keys:

```
- set_as_default: bool
- billing_details: JSON
```


```http request
PUT /api/payment-methods/pm_1Jj2tFCz06et8Vuzu3vzIdFJ/

HTTP 200 OK
Allow: GET, PUT, DELETE, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "pm_1Jj2tFCz06et8Vuzu3vzIdFJ",
    "billing_details": {
          "address": {
                "city": "Dublin",
                "country": "IE",
                "line1": "O'Connell Street",
                "line2": null,
                "postal_code": "",
                "state": "Dublin"
            },
        "email": null,
        "name": "Jane Doe",
        "phone": null
    },
    "card": {
        "brand": "visa",
        "checks": {
            "address_line1_check": null,
            "address_postal_code_check": null,
            "cvc_check": "pass"
        },
        "country": "US",
        "exp_month": 5,
        "exp_year": 2025,
        "fingerprint": "4fs8d0OveGSOiKRG",
        "funding": "credit",
        "generated_from": null,
        "last4": "4242",
        "networks": {
            "available": [
                "visa"
            ],
            "preferred": null
        },
        "three_d_secure_usage": {
            "supported": true
        },
        "wallet": null
    },
    "created": 1633293765,
    "type": "card"
}
```


### Subscriptions

Methods Supported: POST, GET, PUT, DELETE

This view is included in ```django_stripe.urls``` or can be added individually:

```python
from django.urls import re_path
from django_stripe.views import StripeSubscriptionView

urlpatterns = [
    re_path(r'^subscriptions/(?:(?P<obj_id>.*)/)?', StripeSubscriptionView.as_view(), name="subscriptions")
]
```

To list the authenticated user's subscriptions:

http://localhost:8000/api/subscriptions/

To retrieve a single subscription:

http://localhost:8000/api/payment-methods/sub_1JhjheCz06et8VuzyEbux9T4/


```http request
GET /api/subscriptions/
HTTP 200 OK
Allow: GET, POST, PUT, DELETE, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

[
    {
        "id": "sub_1JhjheCz06et8VuzyEbux9T4",
        "created": 1633563554,
        "product": "prod_Jo3KY017h0SZ1x",
        "price": "price_1JB9PtCz06et8VuzfLu1Z9bf",
        "cancel_at": null,
        "current_period_end": 1665099554,
        "current_period_start": 1633563554,
        "days_until_due": null,
        "default_payment_method": null,
        "latest_invoice": "in_1Jj2tFCz06et8Vuzu3vzIdFJ",
        "start_date": 1633563554,
        "status": "active",
        "trial_end": null,
        "trial_start": null
    }
]

```

To create a subscription for the authenticated user, send a POST request to the following URL with the following paramaters:

```
price_id: str
default_payment_method: str
set_as_default_payment_method: bool
```

The ```price_id``` parameter is mandatory.

The ```default_payment_method``` parameter is mandatory if the customer does not already have a ```default_payment_method``` attached.

The ```set_as_default_payment_method``` parameter can be optionally set to true in which case the ```default_payment_method``` given for the subscription will become the ```set_as_default_payment_method``` for the customer also.


```http request
POST /api/subscriptions/

HTTP 201 Created
Allow: GET, POST, PUT, DELETE, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "sub_1Jj4ozCz06et8VuzZEEgJno2",
    "created": 1633883061,
    "product": "prod_Jo3EMrpYBKmHiM",
    "price": "price_1JAR86Cz06et8VuzO1sER9MR",
    "cancel_at": null,
    "current_period_end": 1665419061,
    "current_period_start": 1633883061,
    "days_until_due": null,
    "default_payment_method": "pm_1JgbWDCz06et8VuzKdb4KdZy",
    "latest_invoice": "in_1Jj4ozCz06et8VuzUTSsTBT7",
    "start_date": 1633883061,
    "status": "active",
    "trial_end": null,
    "trial_start": null
}
```

To update a Subscription for the authenticated user, send a PUT request to the instance url with one or all of the following data keys:

```
- default_payment_method: bool
- billing_details: set_as_default_payment_method
```

To cancel a Subscription for the authenticated user, send a DELETE request:

```http request
DELETE /api/subscriptions/sub_1Jj4ozCz06et8VuzZEEgJno2/

HTTP 200 OK
Allow: GET, POST, PUT, DELETE, HEAD, OPTIONS
Content-Type: application/json
Vary: Accept

{
    "id": "sub_1Jj4ozCz06et8VuzZEEgJno2",
    "created": 1633883061,
    "product": "prod_Jo3EMrpYBKmHiM",
    "price": "price_1JAR86Cz06et8VuzO1sER9MR",
    "cancel_at": null,
    "current_period_end": 1665419061,
    "current_period_start": 1633883061,
    "days_until_due": null,
    "default_payment_method": "pm_1JgbWDCz06et8VuzKdb4KdZy",
    "latest_invoice": "in_1Jj4ozCz06et8VuzUTSsTBT7",
    "start_date": 1633883061,
    "status": "canceled",
    "trial_end": null,
    "trial_start": null
}


```

## Function Reference