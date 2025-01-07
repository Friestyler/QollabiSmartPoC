from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial_migration'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create the degoudse_settings table
    op.create_table(
        'degoudse_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('section_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200)),
        sa.Column('link', sa.String(length=500)),
        sa.Column('content', sa.Text()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )

    # Create the baloise_settings table
    op.create_table(
        'baloise_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('section_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200)),
        sa.Column('link', sa.String(length=500)),
        sa.Column('content', sa.Text()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now())
    )

def downgrade():
    # Drop the tables if they exist
    op.drop_table('degoudse_settings')
    op.drop_table('baloise_settings')
