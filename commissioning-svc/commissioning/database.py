import os

from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base  # type: ignore
from yarl import URL

DB_URL = URL.build(
    scheme="postgresql+asyncpg",
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
    path="/",
) / os.getenv("DB_NAME", "topology")

Model: DeclarativeMeta = declarative_base()
