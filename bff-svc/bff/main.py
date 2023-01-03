from typing import Dict, List, Tuple
from uuid import UUID

from fastapi import FastAPI, status
from pydantic import BaseModel
from yarl import URL

from bff import client

PROJECTS_URL = URL("http://projects-svc")
COMMISSIONING_URL = URL("http://commissioning-svc")


class CreateProject(BaseModel):
    name: str


class Project(CreateProject):
    project_id: str


class CreateArea(BaseModel):
    name: str


class Area(CreateArea):
    area_id: str
    project_id: str


class CreateZone(BaseModel):
    name: str


class Zone(CreateZone):
    zone_id: str
    area_id: str
    project_id: str


def bff_svc() -> FastAPI:
    cache: Dict[Tuple, client.CacheEntry] = {}

    app = FastAPI()
    app.add_middleware(client.SessionMiddleware, cache=cache)

    @app.get("/projects", response_model=List[Project])
    async def get_projects():
        async with client.get(PROJECTS_URL / "projects") as response:
            return await response.json()

    @app.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
    async def post_projects(create_project: CreateProject):
        async with client.post(PROJECTS_URL / "projects", json=create_project.dict()) as response:
            return await response.json()

    @app.get("/projects/{project_id}", response_model=Project)
    async def get_project(project_id: str):
        async with client.get(PROJECTS_URL / "projects" / project_id) as response:
            return await response.json()

    @app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_project(project_id: str):
        async with client.delete(PROJECTS_URL / "projects" / project_id):
            return None

    @app.get("/projects/{project_id}/areas", response_model=List[Area])
    async def get_areas(project_id: str):
        async with client.get(PROJECTS_URL / "projects" / project_id / "areas") as response:
            return await response.json()

    @app.post(
        "/projects/{project_id}/areas",
        response_model=Area,
        status_code=status.HTTP_201_CREATED,
    )
    async def post_areas(project_id: str, create_area: CreateArea):
        async with client.post(
            PROJECTS_URL / "projects" / project_id / "areas", json=create_area.dict()
        ) as response:
            return await response.json()

    @app.get("/projects/{project_id}/areas/{area_id}", response_model=Area)
    async def get_area(project_id: str, area_id: str):
        async with client.get(PROJECTS_URL / "projects" / project_id / "areas" / area_id) as response:
            return await response.json()

    @app.delete("/projects/{project_id}/areas/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_area(project_id: str, area_id: str):
        async with client.delete(PROJECTS_URL / "projects" / project_id / "areas" / area_id):
            return None

    @app.get("/projects/{project_id}/areas/{area_id}/zones", response_model=List[Zone])
    async def get_zones(project_id: str, area_id: str):
        async with client.get(
            PROJECTS_URL / "projects" / project_id / "areas" / area_id / "zones"
        ) as response:
            return [dict(project_id=project_id, **zone) for zone in await response.json()]

    @app.post(
        "/projects/{project_id}/areas/{area_id}/zones",
        response_model=Zone,
        status_code=status.HTTP_201_CREATED,
    )
    async def post_zones(project_id: str, area_id: str, create_zone: CreateZone):
        async with client.post(
            PROJECTS_URL / "projects" / project_id / "areas" / area_id / "zones",
            json=create_zone.dict(),
        ) as response:
            return await response.json()

    @app.get("/projects/{project_id}/areas/{area_id}/zones/{zone_id}", response_model=Zone)
    async def get_zone(project_id: str, area_id: str, zone_id: str):
        async with client.get(
            PROJECTS_URL / "projects" / project_id / "areas" / area_id / "zones" / zone_id
        ) as response:
            return dict(project_id=project_id, **await response.json())

    @app.delete(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_zone(project_id: str, area_id: str, zone_id: str):
        async with client.delete(
            PROJECTS_URL / "projects" / project_id / "areas" / area_id / "zones" / zone_id
        ):
            return None

    @app.get("/projects/{project_id}/areas/{area_id}/zones/{zone_id}/nodes/{node_uuid}")
    async def get_node(project_id: str, area_id: str, zone_id: str, node_uuid: UUID):
        async with client.get(COMMISSIONING_URL / "nodes" / node_uuid.hex) as node_response:
            return await node_response.json()

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
