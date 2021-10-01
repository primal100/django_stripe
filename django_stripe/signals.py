import django.dispatch
import stripe
from typing import Any


new_customer = django.dispatch.Signal()
customer_modified = django.dispatch.Signal()
checkout_created = django.dispatch.Signal()
billing_portal_created = django.dispatch.Signal()
setup_intent_created = django.dispatch.Signal()
subscription_created = django.dispatch.Signal()
subscription_modified = django.dispatch.Signal()
subscription_cancelled = django.dispatch.Signal()
payment_method_detached = django.dispatch.Signal()


all_signals = [new_customer,
               customer_modified,
               checkout_created,
               billing_portal_created,
               setup_intent_created,
               subscription_created,
               subscription_modified,
               subscription_cancelled,
               payment_method_detached]


modify_signals = {
    stripe.Subscription: {
        'signal': subscription_modified,
        'obj_name': "subscription"
    }
}

delete_signals = {
    stripe.Subscription: {
        'signal': subscription_cancelled,
        'obj_name': "subscription"
    }
}


def _send_signal_on_change(user, obj_cls: Any, obj: Any, signals) -> bool:
    signal_data = signals.get(obj_cls)
    if signal_data:
        signal = signal_data['signal']
        kwargs = {'sender': user, signal_data['obj_name']: obj}
        signal.send(**kwargs)
        return True
    return False


def send_signal_on_modify(user, obj_cls: Any, obj: Any) -> bool:
    return _send_signal_on_change(user, obj_cls, obj, modify_signals)


def send_signal_on_delete(user, obj_cls: Any, obj: Any) -> bool:
    return _send_signal_on_change(user, obj_cls, obj, delete_signals)
