from subscriptions.types import Protocol, UserProtocol


class DjangoUserProtocol(UserProtocol, Protocol):
    is_authenticated: bool

    def save(self, update_fields=None, **kwargs):
        pass
