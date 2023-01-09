import re
from contextlib import suppress

import aiohttp
from starlette.middleware.base import BaseHTTPMiddleware

from bff import client, context, urls


class RoleMiddleware(BaseHTTPMiddleware):
    def _get_project_id(self, request):
        if m := re.match(r"^/projects/(?P<project_id>[a-f0-9]+)", request.url.path):
            return m.group("project_id")

    async def dispatch(self, request, call_next):
        if project_id := self._get_project_id(request):
            async with client.get(urls.PROJECTS_SVC / "projects" / project_id / "role") as response:
                role = await response.json()
                context.update_headers(**{"x-role": role})

        return await call_next(request)
