from typing import List, Dict, Any

from fastapi import FastAPI, status
from pydantic import BaseModel


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
    app = FastAPI()

    @app.post("/misconfiguration", response_model=List[Misconfiguration])
    async def post_misconfigurations(node: Node, zone: Zone):
        return []

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
