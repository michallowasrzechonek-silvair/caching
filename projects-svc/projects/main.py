from typing import Dict, Tuple
from uuid import UUID, uuid4

from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config as alembic_config
from fastapi import FastAPI, responses, status
from fastapi_sqlalchemy import AsyncDBSessionMiddleware
from pkg_resources import resource_filename
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine

from projects.cache import CacheEntry, CachingMiddleware
from projects.database import DB_URL, Area, Project, Zone


class CreateProject(BaseModel):
    name: str


class CreateArea(BaseModel):
    name: str


class CreateZone(BaseModel):
    name: str


def projects_svc() -> FastAPI:
    cache: Dict[Tuple, CacheEntry] = {}

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

        config = alembic_config(resource_filename("projects", "alembic.ini"))

        async_engine = create_async_engine(str(DB_URL))
        async with async_engine.connect() as connection:
            await connection.run_sync(upgrade, config)

    @app.get("/projects")
    async def get_projects():
        return await Project.select()

    @app.post(
        "/projects",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def post_projects(create_project: CreateProject):
        project_id = uuid4()
        await Project.create(project_id=project_id.hex, name=create_project.name)
        return f"projects/{project_id}"

    @app.get("/projects/{project_id}")
    async def get_project(project_id: UUID):
        return await Project.get(project_id=project_id.hex)

    @app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_project(project_id: UUID):
        return await Project.delete(project_id=project_id.hex)

    @app.get("/projects/{project_id}/areas")
    async def get_areas(project_id: UUID):
        return await Area.select(project_id=project_id.hex)

    @app.post(
        "/projects/{project_id}/areas",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def post_areas(project_id: UUID, create_area: CreateArea):
        area_id = uuid4()
        await Area.create(project_id=project_id.hex, area_id=area_id.hex, name=create_area.name)
        return f"projects/{project_id}/areas/{area_id}"

    @app.get("/projects/{project_id}/areas/{area_id}")
    async def get_area(project_id: UUID, area_id: UUID):
        return await Area.get(project_id=project_id.hex, area_id=area_id.hex)

    @app.delete("/projects/{project_id}/areas/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_area(project_id: UUID, area_id: UUID):
        return await Area.delete(project_id=project_id.hex, area_id=area_id.hex)

    @app.get("/projects/{project_id}/areas/{area_id}/zones")
    async def get_zones(project_id: UUID, area_id: UUID):
        area = await Area.get(project_id=project_id.hex, area_id=area_id.hex)
        return await Zone.select(area_id=area.area_id)

    @app.post(
        "/projects/{project_id}/areas/{area_id}/zones",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def post_zones(project_id: UUID, area_id: UUID, create_zone: CreateZone):
        zone_id = uuid4()
        area = await Area.get(project_id=project_id.hex, area_id=area_id.hex)
        await Zone.create(area_id=area.area_id, zone_id=zone_id.hex, name=create_zone.name)
        return f"projects/{project_id}/areas/{area_id}/zones/{zone_id}"

    @app.get("/projects/{project_id}/areas/{area_id}/zones/{zone_id}")
    async def get_zone(project_id: UUID, area_id: UUID, zone_id: UUID):
        area = await Area.get(project_id=project_id.hex, area_id=area_id.hex)
        return await Zone.get(area_id=area.area_id, zone_id=zone_id.hex)

    @app.delete(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_zone(project_id: UUID, area_id: UUID, zone_id: UUID):
        area = await Area.get(project_id=project_id.hex, area_id=area_id.hex)
        return await Zone.delete(area_id=area.area_id, zone_id=zone_id.hex)

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
