from dataclasses import dataclass
from hashlib import sha1
from typing import List, MutableMapping, Optional, Tuple

from starlette.datastructures import URL, Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send


@dataclass
class CacheEntry:
    etag: str
    headers: list


class CachingSend:
    def __init__(self, send: Send, cache: MutableMapping[Tuple, CacheEntry], key: Tuple):
        self._send = send
        self.cache = cache
        self.key = key

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
            self.cache[self.key] = CacheEntry(etag=etag, headers=headers)

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

    def __init__(self, app: ASGIApp, cache: MutableMapping[Tuple, CacheEntry]):
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

        key = (str(url),)

        if entry := self.cache.get(key):
            if entry.etag == headers.get("If-None-Match"):
                await self.not_modified(entry, send)
                return

        caching_send = CachingSend(send, self.cache, key)
        await self.app(scope, receive, caching_send)
