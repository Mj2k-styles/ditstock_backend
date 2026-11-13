"""Produits complets, contact fournisseur, fournisseur des entrées et journal d'audit

Revision ID: c4e8a1f2d6b7
Revises: b7c2d41e9a55
Create Date: 2026-11-13 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e8a1f2d6b7'
down_revision = 'b7c2d41e9a55'
branch_labels = None
depends_on = None


def upgrade():
    # Produits : fournisseur, unité, prix de vente et image (cahier des charges, F2.1)
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('supplier_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('unit', sa.String(length=20), nullable=False, server_default='pièce'))
        batch_op.add_column(sa.Column('sale_price', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True))
        batch_op.create_index(batch_op.f('ix_products_supplier_id'), ['supplier_id'], unique=False)
        batch_op.create_foreign_key('fk_products_supplier_id', 'suppliers', ['supplier_id'], ['id'])

    # Fournisseurs : personne à contacter (F4.1)
    with op.batch_alter_table('suppliers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact', sa.String(length=150), nullable=True))

    # Mouvements : fournisseur d'une entrée (historique des approvisionnements, F4.2)
    with op.batch_alter_table('stock_movements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('supplier_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_stock_movements_supplier_id'), ['supplier_id'], unique=False)
        batch_op.create_foreign_key('fk_stock_movements_supplier_id', 'suppliers', ['supplier_id'], ['id'])

    # Journal d'audit (F9.1)
    op.create_table('audit_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('entity', sa.String(length=50), nullable=False),
    sa.Column('entity_id', sa.Integer(), nullable=True),
    sa.Column('details', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_entity'), ['entity'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_logs_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_logs_user_id'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_entity'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_created_at'))
        batch_op.drop_index(batch_op.f('ix_audit_logs_action'))
    op.drop_table('audit_logs')

    with op.batch_alter_table('stock_movements', schema=None) as batch_op:
        batch_op.drop_constraint('fk_stock_movements_supplier_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_stock_movements_supplier_id'))
        batch_op.drop_column('supplier_id')

    with op.batch_alter_table('suppliers', schema=None) as batch_op:
        batch_op.drop_column('contact')

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_constraint('fk_products_supplier_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_products_supplier_id'))
        batch_op.drop_column('image_url')
        batch_op.drop_column('sale_price')
        batch_op.drop_column('unit')
        batch_op.drop_column('supplier_id')
