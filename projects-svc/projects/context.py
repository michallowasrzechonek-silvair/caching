from contextvars import ContextVar
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware

_headers: ContextVar[Dict[str, str]] = ContextVar("_user")


class RequestHeadersMiddleware(BaseHTTPMiddleware):
    HEADERS = {
        "x-user",
        "x-role",
    }

    async def dispatch(self, request, call_next):
        _headers.set({name: value for name, value in request.headers.items() if name in self.HEADERS})

        return await call_next(request)


def current_headers():
    return _headers.get({})


def update_headers(**kwargs):
    _headers.set({**current_headers(), **kwargs})
