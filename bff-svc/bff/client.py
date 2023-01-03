from contextvars import ContextVar
from dataclasses import dataclass
from logging import getLogger
from typing import Any

import aiohttp
import yarl
from fastapi import responses
from starlette.middleware.base import BaseHTTPMiddleware

logger = getLogger("client")
_session: ContextVar[aiohttp.ClientSession] = ContextVar("_session")


@dataclass
class CacheEntry:
    etag: str
    response: Any


class CachingSession(aiohttp.ClientSession):
    def __init__(self, cache, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = cache

    async def _request(self, method, url, *args, **kwargs):
        key = (url,)

        if method == "GET":
            if entry := self.cache.get(key):
                kwargs.setdefault("headers", {})["If-None-Match"] = entry.etag

        response = await super()._request(method, url, *args, **kwargs)

        if method == "GET":
            if response.status == 304 and entry:
                return entry.response

            if response.status == 200:
                if etag := response.headers.get("ETag"):
                    self.cache[key] = CacheEntry(etag=etag, response=response)

        return response


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


def post(url: yarl.URL, *, data: Any = None, **kwargs: Any) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.post(_session.get(), url, data=data, **kwargs)


def put(url: yarl.URL, *, data: Any = None, **kwargs: Any) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.put(_session.get(), url, data=data, **kwargs)


def patch(url: yarl.URL, *, data: Any = None, **kwargs: Any) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.patch(_session.get(), url, data=data, **kwargs)


def delete(url: yarl.URL, **kwargs: Any) -> aiohttp.client._RequestContextManager:
    return aiohttp.ClientSession.delete(_session.get(), url, **kwargs)
