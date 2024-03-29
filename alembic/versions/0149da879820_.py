"""empty message

Revision ID: 0149da879820
Revises: 0823ce261fca
Create Date: 2023-02-09 11:07:55.101468

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import FetchedValue


# revision identifiers, used by Alembic.
revision = '0149da879820'
down_revision = '0823ce261fca'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('submissions', sa.Column('scores_last_updated_utc', sa.Integer(), nullable=True))
    op.create_index('submissions_aux_body_trgm_idx', 'submissions_aux', ['body'], unique=False, postgresql_using='gin', postgresql_ops={'body': 'gin_trgm_ops'})
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('submissions_aux_body_trgm_idx', table_name='submissions_aux', postgresql_using='gin', postgresql_ops={'body': 'gin_trgm_ops'})
    op.drop_column('submissions', 'scores_last_updated_utc')
    # ### end Alembic commands ###
