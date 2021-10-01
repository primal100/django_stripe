from subscriptions.types import Protocol, UserProtocol, ProductIsSubscribed


class DjangoUserProtocol(UserProtocol, Protocol):
    is_authenticated: bool

    def save(self, update_fields=None, **kwargs):
        pass


class SubscriptionInfoWithEvaluation(ProductIsSubscribed):
    evaluation: bool
