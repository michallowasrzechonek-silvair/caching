import logging
from typing import List, Dict, Any

from fastapi import FastAPI, status, Depends
from pydantic import BaseModel

from reconf.cache import CachingMiddleware, MemoryCache


class Node(BaseModel):
    name: str
    configuration: Dict


class Zone(BaseModel):
    name: str
    scenario: str


class Misconfiguration(BaseModel):
    name: str
    current: Any
    expected: Any


def reconf_svc() -> FastAPI:
    cache = MemoryCache()

    app = FastAPI()
    app.add_middleware(CachingMiddleware, cache=cache)

    @app.post("/misconfiguration", response_model=List[Misconfiguration])
    async def post_misconfigurations(node: Node, zone: Zone, cache_vary=Depends(cache.vary)):
        # https://httpwg.org/http-extensions/draft-ietf-httpbis-digest-headers.html#name-using-repr-digest-in-state-
        cache_vary("Repr-Digest")

        logging.warning("RUNNING AUDIT")
        return []

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
