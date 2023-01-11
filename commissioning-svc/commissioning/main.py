import json
from typing import Dict

from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config as alembic_config
from fastapi import Depends, FastAPI, Query, responses, status
from fastapi_sqlalchemy import AsyncDBSessionMiddleware
from pkg_resources import resource_filename
from pydantic import BaseModel, Field
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import create_async_engine

from commissioning.cache import CachingMiddleware, MemoryCache
from commissioning.database import DB_URL, Node


class CreateNode(BaseModel):
    name: str
    configuration: Dict = Field(default_factory=dict)


class UpdateNode(BaseModel):
    name: str = None
    configuration: Dict = None


def commissioning_svc() -> FastAPI:
    cache = MemoryCache()

    app = FastAPI()
    app.add_middleware(
        AsyncDBSessionMiddleware,
        db_url=str(DB_URL),
        commit_on_exit=True,
    )
    app.add_middleware(CachingMiddleware, cache=cache)

    @app.on_event("startup")
    async def run_migrations():
        def upgrade(connection, cfg):
            cfg.attributes["connection"] = connection
            alembic_upgrade(cfg, "head")

        config = alembic_config(resource_filename("commissioning", "alembic.ini"))

        async_engine = create_async_engine(str(DB_URL))
        async with async_engine.connect() as connection:
            await connection.run_sync(upgrade, config)

    @app.get("/nodes")
    async def list_nodes(
        project_id: str = Query(...), zone_id: str = Query(...), cache_vary=Depends(cache.vary)
    ):
        nodes = await Node.select(Node.tags.comparator.contains(dict(project_id=project_id, zone_id=zone_id)))

        with cache_vary() as invalidate:
            invalidate(Node, tags=dict(project_id=project_id, zone_id=zone_id))

        return nodes

    @app.get("/nodes/{node_uuid}")
    async def get_node(
        node_uuid: str,
        project_id: str = Query(...),
        zone_id: str = Query(...),
        cache_vary=Depends(cache.vary),
    ):
        node = await Node.get(
            Node.node_uuid == node_uuid,
            Node.tags.comparator.contains(dict(project_id=project_id, zone_id=zone_id)),
        )

        with cache_vary() as invalidate:
            invalidate(Node, node_uuid=node_uuid)

        return node

    @app.put(
        "/nodes/{node_uuid}", response_class=responses.RedirectResponse, status_code=status.HTTP_303_SEE_OTHER
    )
    async def put_node(
        node_uuid: str, create_node: CreateNode, project_id: str = Query(...), zone_id: str = Query(...)
    ):
        await Node.merge(
            dict(node_uuid=node_uuid),
            name=create_node.name,
            tags=dict(project_id=project_id, zone_id=zone_id),
            configuration=create_node.configuration,
        )

        return f"/nodes/{node_uuid}?project_id={project_id}&zone_id={zone_id}"

    @app.patch(
        "/nodes/{node_uuid}", response_class=responses.RedirectResponse, status_code=status.HTTP_303_SEE_OTHER
    )
    async def patch_node(
        node_uuid: str, update_node: UpdateNode, project_id: str = Query(...), zone_id: str = Query(...)
    ):
        await Node.update(
            Node.node_uuid == node_uuid,
            tags=dict(project_id=project_id, zone_id=zone_id),
            **update_node.dict(exclude_none=True),
        )

        return f"/nodes/{node_uuid}?project_id={project_id}&zone_id={zone_id}"

    @app.delete("/nodes/{node_uuid}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_node(node_uuid: str, project_id: str = Query(...), zone_id: str = Query(...)):
        # FIXME: sqlalchemy.exc.InvalidRequestError: Could not evaluate current criteria in Python
        # when using delete() with contains()
        await Node.get(
            Node.node_uuid == node_uuid,
            Node.tags.comparator.contains(dict(project_id=project_id, zone_id=zone_id)),
        )
        await Node.delete(
            Node.node_uuid == node_uuid,
        )

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
