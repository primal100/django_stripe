import stripe
import logging

from operator import itemgetter

import subscriptions.exceptions
from stripe.error import StripeError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django_stripe import payments, exceptions
from subscriptions.types import Protocol
from typing import Dict, Any, Callable, List, Type, Union, Iterable, Optional


DataType = Union[Dict[str, Any], List[Any]]


logger = logging.getLogger("django_stripe")


class StripeViewMixin(Protocol):
    stripe_resource = None
    throttle_scope: str = 'payments'
    status_code: int = status.HTTP_200_OK
    response_keys: tuple = ("id", "created")
    response_keys_exclude: tuple = None

    def make_request(self, request: Request, **data) -> DataType: ...

    @property
    def name_in_errors(self) -> str:
        return self.stripe_resource.__name__

    def make_response(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if self.response_keys_exclude:
            return {k: item[k] for k in item.keys() if k not in self.response_keys_exclude}
        if self.response_keys:
            return {k: item[k] for k in self.response_keys}
        return item

    def run_stripe(self, request: Request, method: Callable = None, **data) -> DataType:
        method = method or self.make_request
        try:
            return method(request, **data)
        except stripe.error.StripeError as e:
            logger.exception(e, exc_info=e)
            raise exceptions.StripeException(detail=e)

    def run_stripe_response(self, request: Request, method: Callable = None,
                            status_code: int = None, **data) -> Response:
        return Response(
            self.run_stripe(request, method, **data),
            status=status_code or self.status_code
        )


class StripeViewWithSerializerMixin(StripeViewMixin, Protocol):
    serializer_class: Type = None
    serializer_classes: Dict[str, Type] = None

    def get_serializer_class(self, request: Request) -> Optional[Type]:
        if self.serializer_classes:
            serializer_class = self.serializer_classes.get(request.method)
            if serializer_class:
                return serializer_class
        return self.serializer_class

    def get_serializer_context(self, request) -> Dict[str, Any]:
        return {
            'request': request,
            'view': self
        }

    def get_serializer(self, request, *args, **kwargs):
        serializer_class = self.get_serializer_class(request)
        if serializer_class:
            kwargs.setdefault('context', self.get_serializer_context(request))
            return serializer_class(*args,  **kwargs)
        return None

    def run_serialized_stripe_response(self, request: Request, method: Callable = None,
                                       status_code: int = None, **kwargs) -> Response:
        serializer = self.get_serializer(request, data=request.data or request.query_params)
        if not serializer:
            result = self.run_stripe(request, method=method, **kwargs)
        elif serializer.is_valid():
            data = serializer.data
            result = self.run_stripe(request, method=method, **data, **kwargs)
        else:
            result = serializer.errors
            status_code = status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code or self.status_code)


class StripeListMixin(StripeViewWithSerializerMixin, Protocol):
    order_by: tuple = ("created", "id")
    order_reverse: bool = True

    def list(self, request: Request, **kwargs) -> Iterable[Dict[str, Any]]:
        return payments.list_customer_resource(request.user, self.stripe_resource, **kwargs)

    def retrieve(self, request: Request, id: str) -> Dict[str, Any]:
        return payments.retrieve(request.user, self.stripe_resource, id)

    def prepare_list(self, items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            [self.make_response(item) for item in items],
            key=itemgetter(*self.order_by), reverse=self.order_reverse
        )

    def get_list(self, request: Request, **data) -> List[Dict[str, Any]]:
        return self.prepare_list(self.list(request, **data))

    def get_one(self, request: Request, id: str) -> Dict[str, Any]:
        try:
            return self.make_response(self.retrieve(request, id))
        except subscriptions.exceptions.StripeWrongCustomer:
            raise exceptions.StripeException(f"No such {self.name_in_errors}: '{id}'")

    def get(self, request: Request, **kwargs) -> Response:
        if kwargs:
            return self.run_stripe_response(request, method=self.get_one, **kwargs)
        return self.run_serialized_stripe_response(request, method=self.get_list)


class StripeCreateMixin(StripeViewMixin, Protocol):
    permission_classes = (IsAuthenticated,)

    def create(self, request: Request, **data) -> Dict[str, Any]:
        raise NotImplementedError

    def run_create(self, request: Request, **data) -> Dict[str, Any]:
        return self.make_response(self.create(request, **data))

    def post(self, request: Request, **kwargs) -> Response:
        return self.run_stripe_response(request, method=self.run_create, status_code=status.HTTP_201_CREATED, **kwargs)


class StripeCreateWithSerializerMixin(StripeViewWithSerializerMixin, Protocol):
    permission_classes = (IsAuthenticated,)

    def create(self, request: Request, **data) -> Dict[str, Any]:
        raise NotImplementedError

    def run_create(self, request: Request, **data) -> Dict[str, Any]:
        return self.make_response(self.create(request, **data))

    def post(self, request: Request, **kwargs) -> Response:
        return self.run_serialized_stripe_response(request, method=self.run_create,
                                                   status_code=status.HTTP_201_CREATED, **kwargs)


class StripeModifyMixin(StripeViewWithSerializerMixin, Protocol):
    permission_classes = (IsAuthenticated,)

    def modify(self, request: Request, id: str, **data) -> Dict[str, Any]:
        return payments.modify(request.user, self.stripe_resource, id, **data)

    def run_modify(self, request: Request, id: str, **data) -> Dict[str, Any]:
        try:
            return self.make_response(self.modify(request, id=id, **data))
        except subscriptions.exceptions.StripeWrongCustomer:
            raise exceptions.StripeException(f"No such {self.name_in_errors}: '{id}'")

    def put(self, request: Request, id: str, **kwargs) -> Response:
        return self.run_serialized_stripe_response(request, method=self.run_modify,
                                                   status_code=status.HTTP_200_OK, id=id, **kwargs)


class StripeDeleteMixin(StripeViewMixin, Protocol):
    permission_classes = (IsAuthenticated,)

    def destroy(self, request: Request, id: str) -> None:
        payments.delete(request.user, self.stripe_resource, id)

    def run_delete(self, request: Request, id: str) -> None:
        try:
            self.destroy(request, id=id)
        except subscriptions.exceptions.StripeWrongCustomer:
            raise exceptions.StripeException(f"No such {self.name_in_errors}: '{id}'")

    def delete(self, request: Request, id: str, **kwargs) -> Response:
        return self.run_stripe_response(request, method=self.run_delete,
                                        status_code=status.HTTP_204_NO_CONTENT,
                                        id=id, **kwargs)
