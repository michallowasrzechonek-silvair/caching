from typing import List

from fastapi import FastAPI, status
from pydantic import BaseModel

from bff import client, context, role, urls


class CreateNode(BaseModel):
    name: str


class ZoneNode(BaseModel):
    node_uuid: str
    name: str


class Node(BaseModel):
    name: str


class CreateZone(BaseModel):
    name: str


class AreaZone(BaseModel):
    zone_id: str
    name: str


class Zone(AreaZone):
    nodes: List[ZoneNode]


class CreateArea(BaseModel):
    name: str


class ProjectArea(BaseModel):
    area_id: str
    name: str


class Area(ProjectArea):
    zones: List[AreaZone]


class CreateCollaborator(BaseModel):
    email: str
    role: str


class ProjectCollaborator(BaseModel):
    email: str
    role: str


class CreateProject(BaseModel):
    name: str


class Project(CreateProject):
    project_id: str
    collaborators: List[ProjectCollaborator]
    areas: List[ProjectArea]


class ListProject(BaseModel):
    project_id: str
    name: str


def bff_svc() -> FastAPI:
    cache = client.MemoryCache()

    app = FastAPI()
    app.add_middleware(role.RoleMiddleware)
    app.add_middleware(client.SessionMiddleware, cache=cache)
    app.add_middleware(context.RequestHeadersMiddleware)

    @app.get("/projects", response_model=List[ListProject])
    async def get_projects():
        async with client.get(urls.PROJECTS_SVC / "projects") as response:
            return await response.json()

    @app.post("/projects", response_model=ListProject, status_code=status.HTTP_201_CREATED)
    async def post_projects(create_project: CreateProject):
        # FIXME: This is a workaround
        #
        # We can't follow the redirection automatically, because RoleMiddleware
        # doesn't ask for project role if URL doesn't contain the project id.
        # On the other hand, we've just created the project, so we know are the
        # owner...
        async with client.post(
            urls.PROJECTS_SVC / "projects", json=create_project.dict(), allow_redirects=False
        ) as create_response:
            if create_response.status == status.HTTP_201_CREATED:
                location = urls.PROJECTS_SVC.with_path(create_response.headers["Location"])
                async with client.get(location, headers={"x-role": "owner"}) as response:
                    return await response.json()

    @app.get("/projects/{project_id}", response_model=Project)
    async def get_project(project_id: str):
        async with client.get(urls.PROJECTS_SVC / "projects" / project_id) as response:
            return await response.json()

    @app.patch("/projects/{project_id}", response_model=Project)
    async def patch_project(project_id: str, patch_project: CreateProject):
        async with client.patch(
            urls.PROJECTS_SVC / "projects" / project_id, json=patch_project.dict()
        ) as response:
            return await response.json()

    @app.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_project(project_id: str):
        async with client.delete(urls.PROJECTS_SVC / "projects" / project_id):
            return None

    @app.get("/projects/{project_id}/collaborators", response_model=List[ProjectCollaborator])
    async def get_collaborators(project_id: str):
        async with client.get(urls.PROJECTS_SVC / "projects" / project_id / "collaborators") as response:
            return await response.json()

    @app.patch("/projects/{project_id}/collaborators", response_model=List[ProjectCollaborator])
    async def patch_collaborators(project_id: str, create_collaborators: List[CreateCollaborator]):
        async with client.patch(
            urls.PROJECTS_SVC / "projects" / project_id / "collaborators",
            json=[c.dict() for c in create_collaborators],
        ) as response:
            return await response.json()

    @app.delete("/projects/{project_id}/collaborators")
    async def delete_collaborators(project_id: str, delete_collaborators: List[str]):
        async with client.delete(
            urls.PROJECTS_SVC / "projects" / project_id / "collaborators", json=delete_collaborators
        ) as response:
            return await response.json()

    @app.get("/projects/{project_id}/areas", response_model=List[ProjectArea])
    async def get_areas(project_id: str):
        async with client.get(urls.PROJECTS_SVC / "projects" / project_id / "areas") as response:
            return await response.json()

    @app.post(
        "/projects/{project_id}/areas",
        response_model=ProjectArea,
        status_code=status.HTTP_201_CREATED,
    )
    async def post_areas(project_id: str, create_area: CreateArea):
        async with client.post(
            urls.PROJECTS_SVC / "projects" / project_id / "areas", json=create_area.dict()
        ) as response:
            return await response.json()

    @app.get("/projects/{project_id}/areas/{area_id}", response_model=Area)
    async def get_area(project_id: str, area_id: str):
        async with client.get(urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id) as response:
            return await response.json()

    @app.patch("/projects/{project_id}/areas/{area_id}", response_model=Area)
    async def patch_area(project_id: str, area_id: str, patch_area: CreateArea):
        async with client.patch(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id, json=patch_area.dict()
        ) as response:
            return await response.json()

    @app.delete("/projects/{project_id}/areas/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_area(project_id: str, area_id: str):
        async with client.delete(urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id):
            return None

    @app.get("/projects/{project_id}/areas/{area_id}/zones", response_model=List[AreaZone])
    async def get_zones(project_id: str, area_id: str):
        async with client.get(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones"
        ) as response:
            return await response.json()

    @app.post(
        "/projects/{project_id}/areas/{area_id}/zones",
        response_model=AreaZone,
        status_code=status.HTTP_201_CREATED,
    )
    async def post_zones(project_id: str, area_id: str, create_zone: CreateZone):
        async with client.post(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones",
            json=create_zone.dict(),
        ) as response:
            return await response.json()

    @app.get("/projects/{project_id}/areas/{area_id}/zones/{zone_id}", response_model=Zone)
    async def get_zone(project_id: str, area_id: str, zone_id: str):
        async with client.get(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones" / zone_id
        ) as zone_response, client.get(
            urls.COMMISSIONING_SVC / "nodes", params=dict(project_id=project_id, zone_id=zone_id)
        ) as nodes_response:
            zone = await zone_response.json()
            nodes = await nodes_response.json()
            return {**zone, "nodes": nodes}

    @app.patch("/projects/{project_id}/areas/{area_id}/zones/{zone_id}", response_model=Zone)
    async def patch_zone(project_id: str, area_id: str, zone_id: str, patch_zone: CreateZone):
        async with client.patch(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones" / zone_id,
            json=patch_zone.dict(),
        ) as response:
            return await response.json()

    @app.delete(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_zone(project_id: str, area_id: str, zone_id: str):
        async with client.delete(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones" / zone_id
        ):
            return None

    @app.get("/projects/{project_id}/areas/{area_id}/zones/{zone_id}/nodes", response_model=List[ZoneNode])
    async def get_nodes(project_id: str, area_id: str, zone_id: str):
        async with client.get(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones" / zone_id
        ), client.get(
            urls.COMMISSIONING_SVC / "nodes", params=dict(project_id=project_id, zone_id=zone_id)
        ) as node_response:
            return await node_response.json()

    @app.get("/projects/{project_id}/areas/{area_id}/zones/{zone_id}/nodes/{node_uuid}", response_model=Node)
    async def get_node(project_id: str, area_id: str, zone_id: str, node_uuid: str):
        async with client.get(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones" / zone_id
        ), client.get(
            urls.COMMISSIONING_SVC / "nodes" / node_uuid, params=dict(project_id=project_id, zone_id=zone_id)
        ) as response:
            return await response.json()

    @app.put(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}/nodes/{node_uuid}",
        response_model=Node,
        status_code=status.HTTP_201_CREATED,
    )
    async def put_node(project_id: str, area_id: str, zone_id: str, node_uuid: str, create_node: CreateNode):
        async with client.get(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones" / zone_id
        ), client.put(
            urls.COMMISSIONING_SVC / "nodes" / node_uuid,
            json=create_node.dict(),
            params=dict(project_id=project_id, zone_id=zone_id),
        ) as response:
            return await response.json()

    @app.delete(
        "/projects/{project_id}/areas/{area_id}/zones/{zone_id}/nodes/{node_uuid}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_node(project_id: str, area_id: str, zone_id: str, node_uuid: str):
        async with client.get(
            urls.PROJECTS_SVC / "projects" / project_id / "areas" / area_id / "zones" / zone_id
        ), client.delete(
            urls.COMMISSIONING_SVC / "nodes" / node_uuid,
            params=dict(project_id=project_id, zone_id=zone_id),
        ) as response:
            return None

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
