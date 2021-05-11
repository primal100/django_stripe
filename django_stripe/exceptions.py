import re
from rest_framework import exceptions


def get_request_id_string(error_msg: str) -> str:
    try:
        return re.search('^Request req_.+?: ', error_msg)[0]
    except TypeError:
        return ''


class StripeException(exceptions.APIException):
    def __init__(self, detail=None, code=None):
        super().__init__(detail=detail, code=code)
        self.request_id = get_request_id_string(self.detail)
        self.detail = self.detail.replace(self.request_id, "")
