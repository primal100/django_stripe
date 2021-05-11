import django.dispatch


new_customer = django.dispatch.Signal()
customer_modified = django.dispatch.Signal()
checkout_created = django.dispatch.Signal()
billing_portal_created = django.dispatch.Signal()
setup_intent_created = django.dispatch.Signal()
subscription_created = django.dispatch.Signal()
payment_method_detached = django.dispatch.Signal()


all_signals = [new_customer,
               customer_modified,
               checkout_created,
               billing_portal_created,
               setup_intent_created,
               subscription_created,
               payment_method_detached]
