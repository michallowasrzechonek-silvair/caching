from logging import getLogger

from fastapi import HTTPException
from fastapi_sqlalchemy import async_db as db
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert  # type: ignore
from starlette.status import HTTP_404_NOT_FOUND

logger = getLogger("app")


class CrudMixin:
    @classmethod
    def _insert(cls, values=None, *args, **kwargs):
        if values is not None:
            if not values:
                return

            if kwargs:
                raise ValueError("Use either positional or keyword arguments")

        return insert(cls).values(values or kwargs)

    @classmethod
    async def create(cls, values=None, *args, **kwargs):
        stmt = cls._insert(values, *args, **kwargs)
        if stmt is not None:
            await db.session.execute(stmt)

        # TODO: return session-bound instance(s

    @classmethod
    async def merge(cls, values=None, *args, **kwargs):
        stmt = cls._insert(values, *args, **kwargs)
        if stmt is not None:
            await db.session.execute(stmt.on_conflict_do_nothing())

        # TODO: return session-bound instance(s

    @classmethod
    async def get(cls, **kwargs):
        logger.warning("SELECT %s WHERE %s", cls.__name__, kwargs)
        statement = select(cls).filter_by(**kwargs)
        obj = (await db.session.execute(statement)).unique().scalars().one_or_none()
        if not obj:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND,
                detail=f"{cls.__name__} matching {kwargs} doesn't exist",
            )

        return obj

    @classmethod
    async def select(cls, **kwargs):
        logger.warning("SELECT %s WHERE %s", cls.__name__, kwargs)
        statement = select(cls).filter_by(**kwargs)
        objs = (await db.session.execute(statement)).scalars().all()
        return objs

    @classmethod
    async def delete(cls, **kwargs):
        stmt = delete(cls).filter_by(**kwargs)
        await db.session.execute(stmt)
