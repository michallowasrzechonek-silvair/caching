from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config as alembic_config
from fastapi import FastAPI
from fastapi_sqlalchemy import AsyncDBSessionMiddleware
from pkg_resources import resource_filename
from sqlalchemy.ext.asyncio import create_async_engine

from commissioning.database import DB_URL


def commissioning_svc() -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        AsyncDBSessionMiddleware,
        db_url=str(DB_URL),
        commit_on_exit=True,
    )

    @app.on_event("startup")
    async def run_migrations():
        def upgrade(connection, cfg):
            cfg.attributes["connection"] = connection
            alembic_upgrade(cfg, "head")

        config = alembic_config(resource_filename("commissioning", "alembic.ini"))

        async_engine = create_async_engine(str(DB_URL))
        async with async_engine.connect() as connection:
            await connection.run_sync(upgrade, config)

    @app.get("/health")
    async def get_health():
        return "OK"

    return app
