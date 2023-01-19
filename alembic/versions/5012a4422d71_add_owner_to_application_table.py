"""Add owner to application table

Revision ID: 5012a4422d71
Revises: 
Create Date: 2023-01-15 10:55:32.594417

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5012a4422d71'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('application', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('application', sa.Column('owner', sa.String(), nullable=True))
    op.create_foreign_key(None, 'application', 'users', ['owner'], ['username'])

def downgrade() -> None:
    op.drop_constraint(None, 'application', type_='foreignkey')
    op.drop_column('application', 'owner')
    op.drop_column('application', 'created_at')
