from typing import Dict, List, Tuple
from uuid import UUID, uuid4

from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config as alembic_config
from fastapi import FastAPI, responses, status
from fastapi_sqlalchemy import AsyncDBSessionMiddleware
from pkg_resources import resource_filename
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine

from projects import context
from projects.cache import CacheEntry, CachingMiddleware
from projects.database import DB_URL, Area, Collaborator, Project, Zone


class CreateProject(BaseModel):
    name: str


class CreateArea(BaseModel):
    name: str


class CreateZone(BaseModel):
    name: str


class CreateCollaborator(BaseModel):
    email: str
    role: str

    class Config:
        orm_mode = True


def projects_svc() -> FastAPI:
    cache: Dict[Tuple, CacheEntry] = {}

    app = FastAPI()
    app.add_middleware(
        AsyncDBSessionMiddleware,
        db_url=str(DB_URL),
        commit_on_exit=True,
    )
    app.add_middleware(CachingMiddleware, cache=cache)
    app.add_middleware(context.RequestHeadersMiddleware)

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
        await Collaborator.create(
            project_id=project_id.hex, email=context.current_headers().get("x-user"), role="owner"
        )
        return f"/projects/{project_id.hex}"

    @app.get("/projects/{project_id}")
    async def get_project(project_id: UUID):
        return await Project.get(project_id=project_id.hex)

    @app.get("/projects/{project_id}/collaborators", response_model=List[CreateCollaborator])
    async def get_collaborators(project_id: UUID):
        return await Collaborator.select(project_id=project_id.hex)

    @app.patch(
        "/projects/{project_id}/collaborators",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def patch_collaborators(project_id: UUID, create_collaborators: List[CreateCollaborator]):
        for collaborator in create_collaborators:
            await Collaborator.merge(
                dict(project_id=project_id.hex, email=collaborator.email),
                role=collaborator.role,
            )

        return f"/projects/{project_id.hex}/collaborators"

    @app.delete(
        "/projects/{project_id}/collaborators",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def delete_collaborators(project_id: UUID, delete_collaborators: List[str]):
        for email in delete_collaborators:
            await Collaborator.delete(project_id=project_id.hex, email=email)

        return f"/projects/{project_id.hex}/collaborators"

    @app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_project(project_id: UUID):
        return await Project.delete(project_id=project_id.hex)

    @app.get("/projects/{project_id}/role")
    async def get_project_role(project_id: UUID):
        email = context.current_headers().get("x-user")
        collaborator = await Collaborator.get(project_id=project_id.hex, email=email)
        return collaborator.role

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
        return f"/projects/{project_id.hex}/areas/{area_id.hex}"

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
        return f"/projects/{project_id.hex}/areas/{area_id.hex}/zones/{zone_id.hex}"

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
