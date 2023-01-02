"""
Projects model

Revision ID: 69494c419c3a
Revises: -
Create Date: 2023-01-02 13:13:06.268387

"""
import sqlalchemy as sa
from alembic import op

revision = "69494c419c3a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("project_id"),
    )

    op.create_table(
        "areas",
        sa.Column("area_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("area_id"),
        sa.PrimaryKeyConstraint("area_id", "project_id"),
    )

    op.create_table(
        "zones",
        sa.Column("zone_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("area_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["areas.area_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("zone_id"),
        sa.PrimaryKeyConstraint("zone_id", "area_id"),
    )


def downgrade():
    pass
