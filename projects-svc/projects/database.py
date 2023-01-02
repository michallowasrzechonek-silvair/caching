import os

from sqlalchemy import Column, ForeignKey, Text
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base  # type: ignore
from yarl import URL

from projects.crud import CrudMixin

DB_URL = URL.build(
    scheme="postgresql+asyncpg",
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
    path="/",
) / os.getenv("DB_NAME", "project")

Model: DeclarativeMeta = declarative_base()


class Project(CrudMixin, Model):
    __tablename__ = "projects"

    project_id = Column(Text, primary_key=True)
    name = Column(Text)


class Area(CrudMixin, Model):
    __tablename__ = "areas"

    area_id = Column(Text, primary_key=True, unique=True)
    name = Column(Text, nullable=False)
    project_id = Column(Text, ForeignKey("projects.project_id", ondelete="CASCADE"), primary_key=True)


class Zone(CrudMixin, Model):
    __tablename__ = "zones"

    zone_id = Column(Text, primary_key=True, unique=True)
    name = Column(Text, nullable=False)
    area_id = Column(Text, ForeignKey("areas.area_id", ondelete="CASCADE"), primary_key=True)
