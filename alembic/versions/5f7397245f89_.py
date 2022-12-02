"""empty message

Revision ID: 5f7397245f89
Revises: 0bb67dcceca2
Create Date: 2022-12-01 10:04:44.114274

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import FetchedValue


# revision identifiers, used by Alembic.
revision = '5f7397245f89'
down_revision = '0bb67dcceca2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_boards_name', table_name='boards')
    op.create_index('boards_name_trgm_idx', 'boards', ['name'], unique=False, postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.drop_index('ix_users_original_username', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('ix_users_username', 'users', ['username'], unique=False)
    op.create_index('ix_users_original_username', 'users', ['original_username'], unique=False)
    op.drop_index('boards_name_trgm_idx', table_name='boards', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('ix_boards_name', 'boards', ['name'], unique=False)
    # ### end Alembic commands ###