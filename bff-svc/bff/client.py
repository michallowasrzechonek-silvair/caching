from contextvars import ContextVar
from dataclasses import dataclass
from functools import partial
from logging import getLogger
from typing import Any

import aiohttp
import yarl
from fastapi import responses
from starlette.middleware.base import BaseHTTPMiddleware

from bff import context

logger = getLogger("client")
_session: ContextVar[aiohttp.ClientSession] = ContextVar("_session")


@dataclass
class CacheEntry:
    etag: str
    response: Any


class CachingResponse(aiohttp.ClientResponse):
    def __init__(self, *args, cache, **kwargs):
        self.cache = cache
        super().__init__(*args, **kwargs)

    async def start(self, conn):
        await super().start(conn)

        if self.method == "GET":
            key = (self.url,)

            if self.status == 200:
                if etag := self.headers.get("ETag"):
                    self.cache[key] = CacheEntry(etag=etag, response=self)

            entry = self.cache.get(key)

            if self.status == 304 and entry:
                self.status = entry.response.status
                self.reason = entry.response.reason
                self._body = entry.response._body

        return self


class CachingRequest(aiohttp.ClientRequest):
    def __init__(self, *args, cache, **kwargs):
        self.cache = cache
        super().__init__(*args, **kwargs)

    async def send(self, conn):
        self.headers.update(context.current_headers())

        if self.method == "GET":
            if entry := self.cache.get(self.url, self.headers):
                self.headers["If-None-Match"] = entry.etag

        return await super().send(conn)


class CachingSession(aiohttp.ClientSession):
    """
    When we POST, and the service responds with 303, we follow the redirection but want to immediately
    cache the resource we've been redirected to

    We need to override the response class, as `aiohttp.ClientSession_request()` uses an internal loop to
    follow redirections
    """

    def __init__(self, cache, *args, **kwargs):
        super().__init__(
            *args,
            request_class=partial(CachingRequest, cache=cache),
            response_class=partial(CachingResponse, cache=cache),
            **kwargs,
        )
        self.cache = cache


class SessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cache):
        super().__init__(app)
        self.cache = cache

    async def dispatch(self, request, call_next):
        s = CachingSession(self.cache, raise_for_status=True)

        try:
            _session.set(s)
            return await call_next(request)
        except aiohttp.ClientResponseError as ex:
            return responses.JSONResponse(content=dict(message=ex.message), status_code=ex.status)
        finally:
            if not s.closed:
                await s.close()


def get(
    url: yarl.URL, *, allow_redirects: bool = True, **kwargs: Any
) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.get(_session.get(), url, allow_redirects=allow_redirects, **kwargs)


def options(
    url: yarl.URL, *, allow_redirects: bool = True, **kwargs: Any
) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.options(_session.get(), url, allow_redirects=allow_redirects, **kwargs)


def head(
    url: yarl.URL, *, allow_redirects: bool = True, **kwargs: Any
) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.head(_session.get(), url, allow_redirects=allow_redirects, **kwargs)


def post(
    url: yarl.URL, *, allow_redirects: bool = True, data: Any = None, **kwargs: Any
) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.post(_session.get(), url, data=data, **kwargs)


def put(
    url: yarl.URL, *, allow_redirects: bool = True, data: Any = None, **kwargs: Any
) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.put(
        _session.get(), url, allow_redirects=allow_redirects, data=data, **kwargs
    )


def patch(
    url: yarl.URL, *, allow_redirects: bool = True, data: Any = None, **kwargs: Any
) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.patch(
        _session.get(), url, allow_redirects=allow_redirects, data=data, **kwargs
    )


def delete(
    url: yarl.URL, allow_redirects: bool = True, **kwargs: Any
) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.delete(_session.get(), url, allow_redirects=allow_redirects, **kwargs)
