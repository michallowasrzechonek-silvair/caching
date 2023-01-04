"""
Collaborator model

Revision ID: d6f6c427aab4
Revises: 69494c419c3a
Create Date: 2023-01-04 15:45:08.083482

"""
import sqlalchemy as sa
from alembic import op

revision = "d6f6c427aab4"
down_revision = "69494c419c3a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "collaborators",
        sa.Column("project_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.project_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "email"),
    )


def downgrade():
    op.drop_table("collaborators")
