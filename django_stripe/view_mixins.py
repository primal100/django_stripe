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
from .logging import logger
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
    key_rename: dict = {}

    def make_request(self, request: Request, **data) -> DataType: ...

    @property
    def name_in_errors(self) -> str:
        return self.stripe_resource.__name__

    def get_key(self, key: str) -> str:
        return self.key_rename.get(key, key.split('__')[-1])

    @staticmethod
    def get_value(item: Dict[str, Any], key: str) -> Any:
        value = item
        for k in key.split("__"):
            value = value[k]
        return value

    def make_response(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if self.response_keys_exclude:
            return {k: item[k] for k in item.keys() if k not in self.response_keys_exclude}
        if self.response_keys:
            return {self.get_key(k): self.get_value(item, k) for k in self.response_keys}
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

    def retrieve(self, request: Request, obj_id: str) -> Dict[str, Any]:
        return payments.retrieve(request.user, self.stripe_resource, obj_id)

    def prepare_list(self, items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            [self.make_response(item) for item in items],
            key=itemgetter(*self.order_by), reverse=self.order_reverse
        )

    def get_list(self, request: Request, **data) -> List[Dict[str, Any]]:
        return self.prepare_list(self.list(request, **data))

    def get_one(self, request: Request, obj_id: str) -> Dict[str, Any]:
        try:
            return self.make_response(self.retrieve(request, obj_id))
        except subscriptions.exceptions.StripeWrongCustomer as e:
            user = f'User {request.user.id}' if request.user and request.user.is_authenticated else "Unauthenticated User"
            logger.warning("%s attempted to access object they do not own: %s. %s", user, obj_id, e)
            raise exceptions.StripeException(f"No such {self.name_in_errors}: '{obj_id}'")

    def get(self, request: Request, **kwargs) -> Response:
        if kwargs:
            return self.run_stripe_response(request, method=self.get_one, status_code=status.HTTP_200_OK, **kwargs)
        return self.run_serialized_stripe_response(request, method=self.get_list, status_code=status.HTTP_200_OK)


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

    def modify(self, request: Request, obj_id: str, **data) -> Dict[str, Any]:
        return payments.modify(request.user, self.stripe_resource, obj_id, **data)

    def run_modify(self, request: Request, obj_id: str, **data) -> Dict[str, Any]:
        try:
            return self.make_response(self.modify(request, obj_id, **data))
        except subscriptions.exceptions.StripeWrongCustomer:
            raise exceptions.StripeException(f"No such {self.name_in_errors}: '{obj_id}'")

    def put(self, request: Request, obj_id: str, **kwargs) -> Response:
        return self.run_serialized_stripe_response(request, method=self.run_modify,
                                                   status_code=status.HTTP_200_OK, obj_id=obj_id, **kwargs)


class StripeDeleteMixin(StripeViewMixin, Protocol):
    permission_classes = (IsAuthenticated,)
    delete_status_code = status.HTTP_204_NO_CONTENT

    def destroy(self, request: Request, obj_id: str):
        return payments.delete(request.user, self.stripe_resource, obj_id)

    def run_delete(self, request: Request, obj_id: str):
        try:
            result = self.destroy(request, obj_id=obj_id)
            if result:
                return self.make_response(result)
        except subscriptions.exceptions.StripeWrongCustomer:
            raise exceptions.StripeException(f"No such {self.name_in_errors}: '{obj_id}'")

    def delete(self, request: Request, obj_id: str, **kwargs) -> Response:
        return self.run_stripe_response(request, method=self.run_delete,
                                        status_code=self.delete_status_code,
                                        obj_id=obj_id, **kwargs)
