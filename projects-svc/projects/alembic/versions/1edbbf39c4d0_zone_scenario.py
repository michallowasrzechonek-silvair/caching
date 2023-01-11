"""
Zone scenario

Revision ID: 1edbbf39c4d0
Revises: d6f6c427aab4
Create Date: 2023-01-11 14:44:12.170057

"""
import sqlalchemy as sa
from alembic import op

revision = "1edbbf39c4d0"
down_revision = "d6f6c427aab4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("zones", sa.Column("scenario", sa.Text(), nullable=False, server_default="switch"))


def downgrade():
    pass
