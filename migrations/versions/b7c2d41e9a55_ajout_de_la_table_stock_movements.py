"""Ajout de la table stock_movements

Revision ID: b7c2d41e9a55
Revises: 30e29bfa4984
Create Date: 2026-11-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c2d41e9a55'
down_revision = '30e29bfa4984'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('stock_movements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('warehouse_id', sa.Integer(), nullable=False),
    sa.Column('warehouse_dest_id', sa.Integer(), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.Column('reference', sa.String(length=100), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint("type IN ('ENTREE', 'SORTIE', 'TRANSFERT', 'AJUSTEMENT')", name='ck_movement_type'),
    sa.CheckConstraint('quantity <> 0', name='ck_movement_quantity'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['warehouse_dest_id'], ['warehouses.id'], ),
    sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('stock_movements', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_stock_movements_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_stock_movements_product_id'), ['product_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_stock_movements_type'), ['type'], unique=False)
        batch_op.create_index(batch_op.f('ix_stock_movements_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_stock_movements_warehouse_id'), ['warehouse_id'], unique=False)


def downgrade():
    with op.batch_alter_table('stock_movements', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_stock_movements_warehouse_id'))
        batch_op.drop_index(batch_op.f('ix_stock_movements_user_id'))
        batch_op.drop_index(batch_op.f('ix_stock_movements_type'))
        batch_op.drop_index(batch_op.f('ix_stock_movements_product_id'))
        batch_op.drop_index(batch_op.f('ix_stock_movements_created_at'))

    op.drop_table('stock_movements')
