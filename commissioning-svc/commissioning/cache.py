from contextlib import contextmanager, suppress
from dataclasses import dataclass
from functools import partial
from hashlib import sha1
from typing import List, Optional, Tuple

from fastapi import Request, Response
from starlette.datastructures import URL, Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send


@dataclass
class CacheEntry:
    etag: str
    headers: list


@contextmanager
def Subscriber(handler, *args, **kwargs):
    """
    When a view constructs the cache key, it should then subscribe to signals
    emitted by database models to invalidate its key.

    The invalidation should only happen when modified model instances match the
    filter used by the view to generate a resource.

    Note: we can't use SQL clauses here, because signal provides the instance
    as a dictionary, so we would need to run queries on the application side.
    This means that if you need relationships, subscribe to the signal in
    related models, directly.

    See CrudMixin.notify
    """
    handler = partial(handler, *args, **kwargs)

    callbacks = set()

    def _match(received, expected):
        def match(lhs, rhs):
            if rhs is ...:
                return True

            if isinstance(rhs, list):
                return len(rhs) == len(lhs) and all(match(*i) for i in zip(lhs, rhs))

            if isinstance(rhs, dict):
                _lhs = {k: v for k, v in lhs.items()}
                return all(match(v, rhs.get(k, ...)) for k, v in _lhs.items())

            return lhs == rhs

        return match(received, expected)

    def subscribe(model, /, **filters):
        async def callback(**mapping):
            # call the handler only if emitted signal passes the filter
            if not _match(mapping, filters):
                return

            # all callbacks connected by this subscriber point to the same handler, so we can disconnect all
            # of them when handler gets called
            for c in callbacks:
                model.unsubscribe(c)

            return handler()

        model.subscribe(callback)

    yield subscribe


class MemoryCache:
    def __init__(self):
        self.entries = {}
        self.vary_headers = {}

    def _dump_vary(self, vary: List[str]):
        return ";".join(i.strip().lower() for i in vary)

    def _parse_vary(self, vary: str):
        return tuple(i.strip().lower() for i in vary.split(";") if i)

    def _create_key(self, url: str, request_headers: Headers, vary_headers: Tuple[str]):
        return frozenset({url, *((name, request_headers.get(name)) for name in vary_headers)})

    def vary(self, request: Request, response: Response):
        # TODO: cache key should vary on
        #  - url (only path!)
        #  - selected headers
        #  - selected query parameters
        #  - request body (for POST requests - how?)
        def _vary(*vary_headers):
            response.headers.setdefault("Vary", self._dump_vary(vary_headers))
            cache_key = self._create_key(str(request.url), request.headers, vary_headers)
            return Subscriber(self.invalidate, cache_key)

        return _vary

    def _get_key(self, url: str, request_headers: Headers):
        vary_headers = self.vary_headers.get(url, ())
        return self._create_key(url, request_headers, vary_headers)

    def store(
        self, url: str, request_headers: Headers, response_headers: List[Tuple[bytes, bytes]], etag: str
    ):
        with suppress(StopIteration):
            vary = next(value.decode() for name, value in response_headers if name.decode().lower() == "vary")
            self.vary_headers[url] = self._parse_vary(vary)

        key = self._get_key(url, request_headers)
        self.entries[key] = CacheEntry(etag, response_headers)

    def get(self, url: str, request_headers: Headers):
        key = self._get_key(url, request_headers)
        return self.entries.get(key)

    def invalidate(self, key):
        self.entries.pop(key, None)


class CachingSend:
    def __init__(self, send: Send, cache: MemoryCache, url, request_headers):
        self._send = send
        self.cache = cache
        self.url = url
        self.request_headers = request_headers

        self.response_start: Optional[Message] = None
        self.response_body: List[Message] = []

    async def __call__(self, message: Message):
        # these are the headers
        if message["type"] == "http.response.start":
            self.response_start = message
            return

        if message["type"] != "http.response.body":
            raise RuntimeError(f"Wrong message, expecting `http.response.body`, but got `{message['type']}`")

        # body may be streamed in multiple messages, let's accumulate them
        self.response_body.append(message)

        if message.get("more_body", False):
            return

        if not self.response_start:
            raise RuntimeError("Missing `http.response.start` before `http.response.body`")

        if self.response_start["status"] == 200:
            content = b"".join(body["body"] for body in self.response_body)

            etag = sha1(content).hexdigest()
            self.response_start["headers"].append((b"ETag", etag.encode()))

            headers = list(self.response_start["headers"])
            self.cache.store(
                str(self.url), request_headers=self.request_headers, response_headers=headers, etag=etag
            )

        await self._send(self.response_start)
        for body in self.response_body:
            await self._send(body)


class CachingMiddleware:
    """
    This is a [pure-ASGI middleware](https://www.starlette.io/middleware/#pure-asgi-middleware) that allows us
    to intercept body of streaming responses.

    When the app generates a response, we accumulate all parts of the body in memory (see CachingSend above)
    and compute an ETag by hashing it. This ETag is then stored in our cache along with generated headers,
    then sent to the client in the response.

    When we receive a request, we check if the client included the If-None-Match header, and the ETag value
    provided by the client matches the one we have previously cached. If so, we _don't_ invoke the app, just
    return a 304 Not Modified with an empty body.

    Note: we *don't* cache the body on our side! It's the client who is supposed to do this, and use cached
    version when we send back a 304.
    """

    def __init__(self, app: ASGIApp, cache: MemoryCache):
        self.app = app
        self.cache = cache

    async def not_modified(self, entry: CacheEntry, send: Send):
        await send(
            dict(
                type="http.response.start",
                status=304,
                headers=entry.headers,
            )
        )
        await send(dict(type="http.response.body", more_body=False))

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope["method"] != "GET":
            await self.app(scope, receive, send)
            return

        url = URL(scope=scope)
        headers = Headers(scope=scope)

        if entry := self.cache.get(str(url), request_headers=headers):
            if entry.etag == headers.get("If-None-Match"):
                await self.not_modified(entry, send)
                return

        caching_send = CachingSend(send, self.cache, url, headers)
        await self.app(scope, receive, caching_send)
