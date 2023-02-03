from typing import List
from uuid import uuid4

from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config as alembic_config
from fastapi import Depends, FastAPI, exceptions, responses, status
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
    scenario: str


class UpdateZone(BaseModel):
    name: str = None
    scenario: str = None


class CreateCollaborator(BaseModel):
    email: str
    role: str

    class Config:
        orm_mode = True


def project_role():
    async def _project_role():
        if not context.current_headers().get("x-role", None):
            raise exceptions.HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Project doesn't exist or you don't have access",
            )

    return Depends(_project_role)


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
        status_code=status.HTTP_201_CREATED,
    )
    async def post_projects(create_project: CreateProject):
        project_id = uuid4().hex
        await Project.create(project_id=project_id, name=create_project.name)
        await Collaborator.create(
            project_id=project_id, email=context.current_headers().get("x-user"), role="owner"
        )
        return f"/projects/{project_id}"

    @app.get(
        "/projects/{project_id}",
        dependencies=[project_role()],
    )
    async def get_project(project_id: str, cache_vary=Depends(cache.vary)):
        project = await Project.get(Project.project_id == project_id)

        with cache_vary("x-role") as invalidate:
            invalidate(Project, project_id=project_id)
            invalidate(Area, project_id=project_id)
            invalidate(Collaborator, project_id=project_id)

        return project

    @app.patch(
        "/projects/{project_id}",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
        dependencies=[project_role()],
    )
    async def patch_project(project_id: str, update_project: CreateProject):
        await Project.update(Project.project_id == project_id, update_project.dict(exclude_none=True))
        return f"/projects/{project_id}"

    @app.get(
        "/projects/{project_id}/collaborators",
        response_model=List[CreateCollaborator],
        dependencies=[project_role()],
    )
    async def get_collaborators(project_id: str, cache_vary=Depends(cache.vary)):
        collaborators = await Collaborator.select(Collaborator.project_id == project_id)

        with cache_vary("x-role") as invalidate:
            invalidate(Project, project_id=project_id, _action="delete")
            invalidate(Collaborator, project_id=project_id)

        return collaborators

    @app.get(
        "/projects/{project_id}/collaborators/{email}",
        response_model=CreateCollaborator,
        dependencies=[project_role()],
    )
    async def get_collaborator(project_id: str, email: str, cache_vary=Depends(cache.vary)):
        collaborator = await Collaborator.get(
            Collaborator.project_id == project_id, Collaborator.email == email
        )

        with cache_vary() as invalidate:
            invalidate(Project, project_id=project_id, _action="delete")
            invalidate(Collaborator, project_id=project_id, email=email)

        return collaborator

    @app.patch(
        "/projects/{project_id}/collaborators",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
        dependencies=[project_role()],
    )
    async def patch_collaborators(project_id: str, create_collaborators: List[CreateCollaborator]):
        for collaborator in create_collaborators:
            await Collaborator.merge(
                dict(project_id=project_id, email=collaborator.email),
                role=collaborator.role,
            )

        return f"/projects/{project_id}/collaborators"

    @app.delete(
        "/projects/{project_id}/collaborators",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
        dependencies=[project_role()],
    )
    async def delete_collaborators(project_id: str, delete_collaborators: List[str]):
        for email in delete_collaborators:
            await Collaborator.delete(Collaborator.project_id == project_id, Collaborator.email == email)

        return f"/projects/{project_id}/collaborators"

    @app.delete(
        "/projects/{project_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[project_role()],
    )
    async def delete_project(project_id: str):
        return await Project.delete(Project.project_id == project_id)

    @app.get(
        "/projects/{project_id}/areas",
        dependencies=[project_role()],
    )
    async def get_areas(project_id: str, cache_vary=Depends(cache.vary)):
        await Project.get(Project.project_id == project_id)
        areas = await Area.select(Area.project_id == project_id)

        with cache_vary("x-role") as invalidate:
            invalidate(Project, project_id=project_id, _action="delete")
            invalidate(Area, project_id=project_id)

        return areas

    @app.post(
        "/projects/{project_id}/areas",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
        dependencies=[project_role()],
    )
    async def post_areas(project_id: str, create_area: CreateArea):
        area_id = uuid4().hex
        await Project.get(Project.project_id == project_id)
        await Area.create(project_id=project_id, area_id=area_id, name=create_area.name)
        return f"/projects/{project_id}/areas/{area_id}"

    @app.get(
        "/projects/{project_id}/areas/{area_id}",
        dependencies=[project_role()],
    )
    async def get_area(project_id: str, area_id: str, cache_vary=Depends(cache.vary)):
        area = await Area.get(Area.project_id == project_id, Area.area_id == area_id)

        with cache_vary("x-role") as invalidate:
            invalidate(Area, project_id=project_id, area_id=area_id)
            invalidate(Zone, area_id=area_id)

        return area

    @app.patch(
        "/projects/{project_id}/areas/{area_id}",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
        dependencies=[project_role()],
    )
    async def patch_area(project_id: str, area_id: str, update_area: CreateArea):
        await Area.update(
            Area.project_id == project_id, Area.area_id == area_id, **update_area.dict(exclude_none=True)
        )

        return f"/projects/{project_id}/areas/{area_id}"

    @app.delete(
        "/projects/{project_id}/areas/{area_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[project_role()],
    )
    async def delete_area(project_id: str, area_id: str):
        return await Area.delete(Area.project_id == project_id, Area.area_id == area_id)

    @app.get(
        "/projects/{project_id}/areas/{area_id}/zones",
        dependencies=[project_role()],
    )
    async def get_zones(project_id: str, area_id: str, cache_vary=Depends(cache.vary)):
        await Area.get(Area.project_id == project_id, Area.area_id == area_id)
        zones = await Zone.select(Area.project_id == project_id, Zone.area_id == area_id)

        with cache_vary("x-role") as invalidate:
            invalidate(Project, project_id=project_id, _action="delete")
            invalidate(Area, area_id=area_id, _action="delete")
            invalidate(Zone, area_id=area_id)

        return zones

    @app.post(
        "/projects/{project_id}/areas/{area_id}/zones",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
        dependencies=[project_role()],
    )
    async def post_zones(project_id: str, area_id: str, create_zone: CreateZone):
        zone_id = uuid4().hex
        await Area.get(Project.project_id == project_id, Area.area_id == area_id)
        await Zone.create(
            area_id=area_id, zone_id=zone_id, name=create_zone.name, scenario=create_zone.scenario
        )
        return f"/projects/{project_id}/areas/{area_id}/zones/{zone_id}"

    @app.get(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}",
        dependencies=[project_role()],
    )
    async def get_zone(project_id: str, area_id: str, zone_id: str, cache_vary=Depends(cache.vary)):
        zone = await Zone.get(
            Project.project_id == project_id, Area.area_id == area_id, Zone.zone_id == zone_id
        )

        with cache_vary("x-role") as invalidate:
            invalidate(Project, project_id=project_id, _action="delete")
            invalidate(Area, area_id=area_id, _action="delete")
            invalidate(Zone, zone_id=zone_id)

        return zone

    @app.patch(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}",
        response_class=responses.RedirectResponse,
        status_code=status.HTTP_303_SEE_OTHER,
        dependencies=[project_role()],
    )
    async def patch_zone(
        project_id: str, area_id: str, zone_id: str, update_zone: UpdateZone, cache_vary=Depends(cache.vary)
    ):
        await Area.get(Project.project_id == project_id, Area.area_id == area_id)
        await Zone.update(
            Zone.area_id == area_id, Zone.zone_id == zone_id, **update_zone.dict(exclude_none=True)
        )

        return f"/projects/{project_id}/areas/{area_id}/zones/{zone_id}"

    @app.delete(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[project_role()],
    )
    async def delete_zone(project_id: str, area_id: str, zone_id: str):
        await Area.get(Project.project_id == project_id, Area.area_id == area_id)
        return await Zone.delete(Zone.area_id == area_id, Zone.zone_id == zone_id)

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
