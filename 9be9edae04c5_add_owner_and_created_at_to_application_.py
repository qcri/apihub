"""add owner and created_at to application table

Revision ID: 9be9edae04c5
Revises: 
Create Date: 2023-01-12 15:01:46.535112

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9be9edae04c5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('application', sa.Column("created_at", sa.DateTime, nullable=False))
    op.add_column('application', sa.Column("owner", sa.ForeignKey('user.username'), nullable=False))


def downgrade() -> None:
    op.drop_column('application', "owner")
    op.drop_column('application', "created_at")