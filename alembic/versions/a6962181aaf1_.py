"""empty message

Revision ID: a6962181aaf1
Revises: 0149da879820
Create Date: 2023-02-09 11:36:09.590224

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import FetchedValue


# revision identifiers, used by Alembic.
revision = 'a6962181aaf1'
down_revision = '0149da879820'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_submissions_aux_id', table_name='submissions_aux')
    op.create_index(op.f('ix_submissions_aux_id'), 'submissions_aux', ['id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_submissions_aux_id'), table_name='submissions_aux')
    op.create_index('ix_submissions_aux_id', 'submissions_aux', ['id'], unique=False)
    # ### end Alembic commands ###
