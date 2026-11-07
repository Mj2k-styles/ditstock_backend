"""fusion des branches de migration

Revision ID: 544584cabd2e
Revises: a3f1c9b27e10, f3ca38ea98a0
Create Date: 2026-11-07 16:55:12.204354

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '544584cabd2e'
down_revision = ('a3f1c9b27e10', 'f3ca38ea98a0')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
