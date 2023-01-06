from typing import List
from uuid import UUID, uuid4

from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config as alembic_config
from fastapi import Depends, FastAPI, responses, status
from fastapi_sqlalchemy import AsyncDBSessionMiddleware
from pkg_resources import resource_filename
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine

from projects import context
from projects.cache import CachingMiddleware, MemoryCache
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
    cache = MemoryCache()

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
    async def get_projects(response: responses.Response, cache_vary=Depends(cache.vary)):
        user = context.current_headers().get("x-user")
        projects = await Project.select(Project.collaborators.any(Collaborator.email == user))

        with cache_vary("x-user") as invalidate:
            for project in projects:
                invalidate(Project, project_id=project.project_id)

            invalidate(Collaborator, email=user)

        return projects

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
    async def get_project(project_id: UUID, cache_vary=Depends(cache.vary)):
        project = await Project.get(Project.project_id == project_id.hex)

        with cache_vary() as invalidate:
            invalidate(Project, project_id=project_id.hex)
            invalidate(Area, project_id=project_id.hex)
            invalidate(Collaborator, project_id=project_id.hex)

        return project

    @app.patch(
        "/projects/{project_id}",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def patch_project(project_id: UUID, patch_project: CreateProject):
        await Project.merge(dict(project_id=project_id.hex), name=patch_project.name)
        return f"/projects/{project_id.hex}"

    @app.get("/projects/{project_id}/collaborators", response_model=List[CreateCollaborator])
    async def get_collaborators(project_id: UUID, cache_vary=Depends(cache.vary)):
        collaborators = await Collaborator.select(Collaborator.project_id == project_id.hex)

        with cache_vary() as invalidate:
            invalidate(Collaborator, project_id=project_id.hex)

        return collaborators

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
            await Collaborator.delete(Collaborator.project_id == project_id.hex, Collaborator.email == email)

        return f"/projects/{project_id.hex}/collaborators"

    @app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_project(project_id: UUID):
        return await Project.delete(Project.project_id == project_id.hex)

    @app.get("/projects/{project_id}/role")
    async def get_project_role(project_id: UUID, cache_vary=Depends(cache.vary)):
        email = context.current_headers().get("x-user")
        collaborator = await Collaborator.get(
            Collaborator.project_id == project_id.hex, Collaborator.email == email
        )

        with cache_vary("x-user") as invalidate:
            invalidate(Collaborator, project_id=project_id.hex, email=email)

        return collaborator.role

    @app.get("/projects/{project_id}/areas")
    async def get_areas(project_id: UUID, cache_vary=Depends(cache.vary)):
        areas = await Area.select(Area.project_id == project_id.hex)

        with cache_vary() as invalidate:
            invalidate(Area, project_id=project_id.hex)

        return areas

    @app.post(
        "/projects/{project_id}/areas",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def post_areas(project_id: UUID, create_area: CreateArea):
        area_id = uuid4()
        await Project.get(Project.project_id == project_id.hex)
        await Area.create(project_id=project_id.hex, area_id=area_id.hex, name=create_area.name)
        return f"/projects/{project_id.hex}/areas/{area_id.hex}"

    @app.get("/projects/{project_id}/areas/{area_id}")
    async def get_area(project_id: UUID, area_id: UUID, cache_vary=Depends(cache.vary)):
        area = await Area.get(Area.project_id == project_id.hex, Area.area_id == area_id.hex)

        with cache_vary() as invalidate:
            invalidate(Area, project_id=project_id.hex, area_id=area_id.hex)
            invalidate(Zone, area_id=area_id.hex)

        return area

    @app.patch(
        "/projects/{project_id}/areas/{area_id}",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def patch_area(project_id: UUID, area_id: UUID, patch_area: CreateArea):
        await Area.merge(dict(project_id=project_id.hex, area_id=area_id.hex), name=patch_area.name)

        return f"/projects/{project_id.hex}/areas/{area_id.hex}"

    @app.delete("/projects/{project_id}/areas/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_area(project_id: UUID, area_id: UUID):
        return await Area.delete(Area.project_id == project_id.hex, Area.area_id == area_id.hex)

    @app.get("/projects/{project_id}/areas/{area_id}/zones")
    async def get_zones(project_id: UUID, area_id: UUID, cache_vary=Depends(cache.vary)):
        zones = await Zone.select(Area.project_id == project_id.hex, Zone.area_id == area_id.hex)

        with cache_vary() as invalidate:
            invalidate(Zone, area_id=area_id.hex)

        return zones

    @app.post(
        "/projects/{project_id}/areas/{area_id}/zones",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def post_zones(project_id: UUID, area_id: UUID, create_zone: CreateZone):
        zone_id = uuid4()
        await Area.get(Project.project_id == project_id.hex, Area.area_id == area_id.hex)
        await Zone.create(area_id=area_id.hex, zone_id=zone_id.hex, name=create_zone.name)
        return f"/projects/{project_id.hex}/areas/{area_id.hex}/zones/{zone_id.hex}"

    @app.get("/projects/{project_id}/areas/{area_id}/zones/{zone_id}")
    async def get_zone(project_id: UUID, area_id: UUID, zone_id: UUID, cache_vary=Depends(cache.vary)):
        zone = await Zone.get(
            Project.project_id == project_id.hex, Area.area_id == area_id.hex, Zone.zone_id == zone_id.hex
        )

        with cache_vary() as invalidate:
            invalidate(Zone, zone_id=zone_id.hex)

        return zone

    @app.patch(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
    )
    async def patch_zone(
        project_id: UUID, area_id: UUID, zone_id: UUID, patch_zone: CreateZone, cache_vary=Depends(cache.vary)
    ):
        await Area.get(Project.project_id == project_id.hex, Area.area_id == area_id.hex)
        await Zone.merge(dict(area_id=area_id.hex, zone_id=zone_id.hex), name=patch_zone.name)

        return f"/projects/{project_id.hex}/areas/{area_id.hex}/zones/{zone_id.hex}"

    @app.delete(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_zone(project_id: UUID, area_id: UUID, zone_id: UUID):
        await Area.get(Project.project_id == project_id.hex, Area.area_id == area_id.hex)
        return await Zone.delete(Zone.area_id == area_id.hex, Zone.zone_id == zone_id.hex)

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
