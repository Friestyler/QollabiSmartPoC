"""initial migration

Revision ID: 028fd8ec0bdc
Revises: 
Create Date: 2025-01-13 18:17:54.951522

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '028fd8ec0bdc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('baloise_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('section_number', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=True),
    sa.Column('link', sa.String(length=500), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('degoudse_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('section_number', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=True),
    sa.Column('link', sa.String(length=500), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('demo_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('section_number', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=True),
    sa.Column('link', sa.String(length=500), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('demo_settings')
    op.drop_table('degoudse_settings')
    op.drop_table('baloise_settings')
    # ### end Alembic commands ###
